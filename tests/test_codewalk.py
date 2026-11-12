"""codewalk against a small repository of its own, so the tests don't move with the code
this project is used on."""

import json
import os
import textwrap
from datetime import date
from pathlib import Path

import pytest

from codewalk.config import Config
from codewalk.walk.doc import Context, Walk, embed_line
from codewalk.walk.review import ReviewState
from codewalk.web.render import render

LIB = """\
//! A tiny crate.

/// How much to hold back.
// r[impl hold.margin]
pub const MARGIN: u32 = 5;

/// A battery.
pub struct Battery {
    /// What it's told to do, in kW.
    pub power: i32,
}

impl Battery {
    /// Tell it what to do.
    // r[impl battery.command]
    pub fn command(&mut self, power: i32) -> bool {
        match power {
            0 => {
                self.power = 0;
                true
            }
            p => {
                self.power = p;
                false
            }
        }
    }
}

pub mod other {
    pub struct Battery;

    impl Battery {
        pub fn command(&self) {}
    }
}
"""

SPEC = """\
# Spec

r[hold.margin]
Hold a margin back.

r[battery.command]
A battery is told what to do.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/lib.rs").write_text(LIB)
    (tmp_path / "docs/spec").mkdir(parents=True)
    (tmp_path / "docs/spec/spec.md").write_text(SPEC)
    return tmp_path


def ctx(repo: Path) -> Context:
    return Context(repo, Config())


def walk(repo: Path, text: str) -> Walk:
    path = repo / "docs/walk.md"
    path.write_text(textwrap.dedent(text))
    return Walk(ctx(repo), "docs/walk.md")


# ---- The index ------------------------------------------------------------------------


# r[verify ref.tail]
def test_a_tail_of_the_qualified_name_resolves_when_it_names_one_symbol(repo):
    index = ctx(repo).index
    sym, _ = index.resolve("MARGIN")
    assert sym and sym.kind == "const" and sym.line == 5
    sym, _ = index.resolve("other::Battery::command")
    assert sym and sym.qualified.endswith("other::Battery::command")


# r[verify ref.ambiguous]
def test_a_name_shared_by_several_symbols_is_ambiguous_with_each_as_a_candidate(repo):
    sym, candidates = ctx(repo).index.resolve("Battery::command")
    assert sym is None
    assert len(candidates) == 2


# r[verify ref.ambiguous]
# r[verify ref.nearest]
def test_a_name_whose_last_part_others_share_but_whose_path_none_has_names_nothing(repo):
    w = walk(repo, "# W\n\nSee [[fresh::Battery::command]].\n")
    (problem,) = [p for p in w.problems() if p.severity == "error"]
    assert problem.message == "`fresh::Battery::command` names nothing"


# r[verify ref.ambiguous]
# r[verify proposal.pending]
def test_a_proposal_whose_last_part_others_share_but_whose_path_none_has_is_pending(repo):
    w = walk(repo, "# W\n\n```walk proposed rust\nfresh::Battery::command\npub fn command() {}\n```\n")
    kinds = sorted((p.severity, p.message) for p in w.problems() if p.severity != "warning")
    assert kinds == [("pending", "`fresh::Battery::command` is proposed, not written yet")]
    w = walk(repo, "# W\n\n```walk proposed rust\nBattery::command\npub fn command() {}\n```\n")
    assert [p.message for p in w.problems() if p.severity == "error"] == ["`Battery::command` names 2 symbols: qualify it"]


# r[verify ref.nearest]
def test_a_name_that_matches_nothing_suggests_the_nearest(repo):
    sym, candidates = ctx(repo).index.resolve("comand")
    assert sym is None
    assert any(c.name == "command" for c in candidates)


# r[verify index.start]
def test_a_symbol_starts_at_its_doc_comments_and_markers(repo):
    sym, _ = ctx(repo).index.resolve("MARGIN")
    assert (sym.start, sym.line, sym.end) == (3, 5, 5)
    assert sym.doc == "How much to hold back."
    assert sym.markers == [("impl", "hold.margin", 1)]


# r[verify index.languages+2]
def test_an_impl_block_is_named_by_impl_and_its_type(repo):
    index = ctx(repo).index
    sym, candidates = index.resolve("impl Battery")
    assert sym is None and len(candidates) == 2
    sym, _ = index.resolve("impl other::Battery")
    assert sym and sym.kind == "impl"
    assert index.shortest_unique(sym) == "impl other::Battery"


STORING = """\
//! What's stored.
//!
//! More about it.

pub fn store() {}
"""


@pytest.fixture
def filed(repo: Path) -> Path:
    (repo / "src/lib.rs").write_text(LIB + "\npub mod core;\n")
    (repo / "src/core").mkdir()
    (repo / "src/core/mod.rs").write_text("pub mod storing;\n")
    (repo / "src/core/storing.rs").write_text(STORING)
    (repo / "src/main.rs").write_text("fn main() {}\n")
    return repo


# r[verify index.files]
# r[verify index.languages+2]
def test_a_file_is_a_symbol_named_by_its_module_with_its_module_docs(filed, pyrepo):
    index = ctx(filed).index
    sym, _ = index.resolve("core::storing")
    assert sym and sym.kind == "file" and sym.file == "src/core/storing.rs"
    assert (sym.start, sym.end) == (1, 6)
    assert sym.doc == "What's stored." and sym.details == "More about it."
    # The `mod storing;` line isn't a symbol of its own
    assert not [s for s in index.symbols if s.kind == "mod" and s.name == "storing"]
    # A crate's root is named by its path only
    assert index.resolve("lib.rs")[0].kind == "file"
    assert not [s for s in index.symbols if s.qualified == "crate"]
    # A Python module, with its docstring
    py, _ = pyctx(pyrepo).index.resolve("pkg::store")
    assert py and py.kind == "file" and py.doc == "A module."


# r[verify ref.file]
def test_a_file_is_named_by_its_path_or_any_tail_of_it(filed):
    index = ctx(filed).index
    for ref in ("src/core/storing.rs", "core/storing.rs", "storing.rs"):
        sym, _ = index.resolve(ref)
        assert sym and sym.file == "src/core/storing.rs", ref
    # A tail on `/` boundaries only
    assert index.resolve("ore/storing.rs")[0] is None
    sym, candidates = index.resolve("lib.rs")
    assert sym and sym.file == "src/lib.rs"
    (filed / "src/other").mkdir()
    (filed / "src/other/storing.rs").write_text("")
    sym, candidates = ctx(filed).index.resolve("storing.rs")
    assert sym is None and {c.file for c in candidates} == {"src/core/storing.rs", "src/other/storing.rs"}


# r[verify ref.file]
def test_an_item_is_meant_over_the_file_of_the_same_name(filed):
    (filed / "src/core/storing.rs").write_text(STORING + "pub fn storing() {}\n")
    sym, _ = ctx(filed).index.resolve("storing")
    assert sym and sym.kind == "fn"


# r[verify ref.sig+2]
def test_a_files_outline_is_its_module_docs(filed):
    sym, _ = ctx(filed).index.resolve("core::storing")
    assert sym.outline == [(1, 3)]
    path = filed / "docs/walk.md"
    path.write_text("```walk\ncore::storing sig\n```\n")
    html, _ = render(Walk(ctx(filed), "docs/walk.md"))
    assert "More about it" in html and "pub fn store" not in html


# r[verify check.whole-file]
def test_a_whole_file_in_a_walk_block_is_a_warning(filed):
    w = walk(
        filed,
        """\
        ```walk
        core::storing
        core::storing sig
        core::storing > pub fn store
        ```
        """,
    )
    warnings = [p for p in w.problems() if p.severity == "warning"]
    assert [p.line for p in warnings] == [2]


DOCUMENTED = """\
/// Holds a battery back by [`MARGIN`], kept by [`Self::check`].
///
/// ```compile_fail,E0616
/// # use crate::Battery;
/// let x = 1;
/// ```
pub struct Held;

impl Held {
    pub fn check(&self) {}
}
"""


# r[verify embed.docs]
def test_rust_doc_comments_are_shown_as_markdown_with_their_lines_as_written_too(repo):
    (repo / "src/held.rs").write_text(DOCUMENTED)
    (repo / "docs/walk.md").write_text("```walk\nHeld\n```\n")
    html, _ = render(Walk(ctx(repo), "docs/walk.md"))
    prose = html.split('class="doc rust"')[1].split('class="row raw"')[0]
    # Markdown, with intra-doc links to the symbols they name, `Self` its own type
    assert 'data-ref="MARGIN"' in prose and 'data-ref="Held::check"' in prose
    # A code block highlighted as Rust, with its rustdoc attributes, and without the
    # lines rustdoc hides
    assert "compile_fail, E0616" in prose and "use crate" not in prose
    assert '<span class="kd">let</span>' in prose or '<span class="k">let</span>' in prose
    # Its lines as written are there too, to be shown instead
    assert html.count('class="row raw"') == 6 and 'data-action="as-written"' in html


# r[verify embed.docs]
def test_a_numpy_docstrings_entries_are_shown_with_their_types_as_code(pyrepo):
    (pyrepo / "pkg/outlined.py").write_text(OUTLINED)
    (pyrepo / "docs/walk.md").write_text("```walk\noutlined::Store\n```\n")
    html, _ = render(Walk(pyctx(pyrepo), "docs/walk.md"))
    prose = html.split('class="doc python"')[1].split('class="row raw"')[0]
    assert "<p>Keeps things.</p>" in prose and '<div class="doc-h">Parameters</div>' in prose
    assert '<dt><code class="doc-name">root</code> : <code>str</code></dt><dd><p>Where.</p>' in prose


# r[verify embed.docs]
def test_a_type_alone_in_returns_or_raises_is_a_type(repo):
    from codewalk.web.docs import python_doc_html

    doc = python_doc_html(['"""Do it.', "", "Returns", "-------", "list of str", "    Each `x`.", '"""'])
    assert "<dt><code>list of str</code></dt><dd><p>Each <code>x</code>.</p>" in doc


def test_a_member_keeps_its_owner_in_its_shortest_name(repo):
    index = ctx(repo).index
    sym, _ = index.resolve("Battery::power")
    assert index.shortest_unique(sym) == "Battery::power"


# r[verify ref.crate]
def test_crate_anchors_a_reference_at_the_root(repo):
    index = ctx(repo).index
    sym, _ = index.resolve("crate::Battery::command")
    assert sym and sym.qualified == "Battery::command"
    sym, _ = index.resolve("impl crate::Battery")
    assert sym and sym.kind == "impl" and sym.segments[0] == "Battery"


def test_a_reference_can_name_its_file_by_any_tail_of_its_path(repo):
    index = ctx(repo).index
    assert index.resolve("lib.rs#MARGIN")[0]
    assert index.resolve("src/lib.rs#MARGIN")[0]
    assert index.resolve("main.rs#MARGIN")[0] is None


def test_search_matches_words_in_any_order(repo):
    names = [s.qualified for s in ctx(repo).index.search("command other")]
    assert names and names[0].endswith("other::Battery::command")


# ---- Codewalks -----------------------------------------------------------------------


# r[verify ref.forms]
def test_a_walk_block_line_is_a_reference_with_an_optional_focus_and_sig():
    assert embed_line("  Battery::command > 0 => sig") == ("Battery::command", "0 =>", True)
    assert embed_line("impl Battery") == ("impl Battery", None, False)
    assert embed_line("// a comment") is None
    assert embed_line("   ") is None


# r[verify ref.forms]
def test_every_kind_of_reference_is_found_and_resolved(repo):
    w = walk(
        repo,
        """\
        # Walk

        The [[MARGIN]], [the power](walk:Battery::power), and [[r:battery.command]].

        ```walk
        MARGIN
        ```
        """,
    )
    assert [(r.kind, r.target, r.resolved) for r in w.refs] == [
        ("inline", "MARGIN", True),
        ("inline", "Battery::power", True),
        ("req", "r:battery.command", True),
        ("embed", "MARGIN", True),
    ]
    assert w.problems() == []


# r[verify check.broken]
def test_broken_references_are_errors_on_their_lines(repo):
    w = walk(
        repo,
        """\
        # Walk

        [[Battery::command]] and [[r:no.such]].

        ```walk
        nothing_here
        ```
        """,
    )
    problems = {(p.line, p.severity): p for p in w.problems()}
    assert "qualify it" in problems[(3, "error")].message or "no requirement" in problems[(3, "error")].message
    assert sorted(p.line for p in w.problems()) == [3, 3, 6]
    assert all(p.severity == "error" for p in w.problems())


# r[verify ref.focus+2]
def test_a_focus_shows_only_the_block_its_line_opens(repo):
    w = walk(
        repo,
        """\
        ```walk
        crate::Battery::command > 0 =>
        ```
        """,
    )
    (ref,) = w.refs
    assert ref.symbol, ref.error
    lines = ref.symbol.text(w.ctx.index.files).split("\n")
    assert lines[0].strip() == "0 => {"
    assert lines[-1].strip() == "}"
    assert len(lines) == 4


# r[verify ref.focus+2]
def test_a_focus_runs_to_the_end_of_the_statement_its_line_starts(repo):
    (repo / "src/wrap.rs").write_text(
        textwrap.dedent(
            """\
            pub fn post(id: Option<u32>, started: bool) -> bool {
                let first = 1;
                let continues =
                    id.is_some() && !started;
                continues
            }
            """
        )
    )
    w = walk(
        repo,
        """\
        ```walk
        wrap::post > let continues =
        ```
        """,
    )
    (ref,) = w.refs
    assert ref.symbol, ref.error
    lines = ref.symbol.text(w.ctx.index.files).split("\n")
    assert [line.strip() for line in lines] == ["let continues =", "id.is_some() && !started;"]


# r[verify ref.focus+2]
def test_a_focus_that_matches_no_line_is_an_error(repo):
    w = walk(
        repo,
        """\
        ```walk
        MARGIN > nowhere
        ```
        """,
    )
    (problem,) = w.problems()
    assert problem.severity == "error" and "nowhere" in problem.message


# r[verify embed.current]
# r[verify embed.inline]
def test_the_rendered_page_links_symbols_and_requirements(repo):
    w = walk(
        repo,
        """\
        # Walk

        [[MARGIN]] holds [[r:hold.margin]].

        ```walk
        MARGIN
        ```
        """,
    )
    body, data = render(w)
    assert 'class="sym"' in body and 'data-req="hold.margin"' in body
    assert '<figure class="walk" data-ref="MARGIN"' in body
    assert "not reviewed" in body
    assert set(data["symbols"]) == {"MARGIN"}
    assert "hold.margin" in data["requirements"]


# ---- Review -----------------------------------------------------------------------------


# r[verify review.changed]
# r[verify check.strict]
def test_code_changed_since_review_is_a_warning_with_a_diff(repo):
    text = """\
    ```walk
    MARGIN
    ```
    """
    w = walk(repo, text)
    (ref,) = w.refs
    w.ctx.review.mark("docs/walk.md", ref.key, ref.symbol.digest(w.ctx.index.files), ref.symbol.text(w.ctx.index.files))
    assert walk(repo, text).problems() == []

    (repo / "src/lib.rs").write_text(LIB.replace("= 5;", "= 6;"))
    w = walk(repo, text)
    (problem,) = w.problems()
    assert problem.severity == "warning"
    body, _ = render(w)
    assert "changed since review" in body
    assert '<span class="drow del">' in body and '<span class="drow add">' in body


# r[verify review.record]
def test_review_state_is_kept_in_one_file_at_the_root(repo):
    state = ReviewState(repo)
    state.mark("docs/walk.md", "MARGIN", "abc", "text")
    saved = json.loads((repo / "codewalk.review.json").read_text())
    assert saved == {"docs/walk.md": {"MARGIN": {"digest": "abc", "text": "text"}}}
    state.forget_missing("docs/walk.md", set())
    assert json.loads((repo / "codewalk.review.json").read_text()) == {"docs/walk.md": {}}


# ---- Export -----------------------------------------------------------------------------


# r[verify export.plain]
def test_export_writes_plain_markdown_with_the_code_and_links(repo):
    w = walk(
        repo,
        """\
        # Walk

        See [[MARGIN]] and [[r:hold.margin]].

        ```walk
        MARGIN
        ```
        """,
    )
    out = w.export("docs/out.md")
    assert "[`MARGIN`](../src/lib.rs#L5)" in out
    assert "[`hold.margin`](spec/spec.md#L3)" in out
    assert "```rust\n/// How much to hold back.\n// r[impl hold.margin]\npub const MARGIN: u32 = 5;\n```" in out
    assert "```walk" not in out


# ---- Python -----------------------------------------------------------------------------

PY = '''\
"""A module."""

LIMIT = 3


# r[impl hold.margin]
class Store:
    """Keeps things.

    More than one paragraph."""

    size = 0

    @property
    def full(self) -> bool:
        return self.size >= LIMIT

    def add(self, item):
        def check(x):
            return x is not None

        if check(item):
            self.size += 1
        else:
            raise ValueError(
                "nothing"
            )
'''


@pytest.fixture
def pyrepo(repo: Path) -> Path:
    (repo / "pkg").mkdir()
    (repo / "pkg/__init__.py").write_text("")
    (repo / "pkg/store.py").write_text(PY)
    return repo


def pyctx(repo: Path) -> Context:
    return Context(repo, Config(sources=["src/**/*.rs", "pkg/**/*.py"]))


# r[verify index.python-path]
# r[verify index.languages+2]
def test_python_symbols_are_named_from_their_package(pyrepo):
    index = pyctx(pyrepo).index
    names = {s.qualified: s.kind for s in index.symbols if s.file.endswith(".py") and s.kind != "file"}
    assert names == {
        "pkg::store::LIMIT": "const",
        "pkg::store::Store": "class",
        "pkg::store::Store::size": "field",
        "pkg::store::Store::full": "method",
        "pkg::store::Store::add": "method",
        "pkg::store::Store::add::check": "def",
    }


# r[verify index.start]
def test_a_python_symbol_takes_in_its_decorators_comments_and_markers(pyrepo):
    index = pyctx(pyrepo).index
    full, _ = index.resolve("Store::full")
    assert (full.start, full.line) == (14, 15)
    store, _ = index.resolve("Store")
    assert store.start == 6 and store.markers == [("impl", "hold.margin", 1)]
    assert store.doc == "Keeps things."


def test_a_python_focus_follows_indentation(pyrepo):
    w = Walk(pyctx(pyrepo), "docs/walk.md", "```walk\nStore::add > else:\n```\n")
    (ref,) = w.refs
    text = ref.symbol.text(w.ctx.index.files).split("\n")
    assert [line.strip() for line in text] == ["else:", "raise ValueError(", '"nothing"', ")"]


def test_python_exports_as_a_python_block(pyrepo):
    w = Walk(pyctx(pyrepo), "docs/walk.md", "```walk\nLIMIT\n```\n")
    assert "```python\nLIMIT = 3\n```" in w.export("docs/out.md")


# ---- Front matter, and how codewalks relate ---------------------------------------------


def test_front_matter_gives_the_title_summary_and_tags(repo):
    w = walk(
        repo,
        """\
        ---
        title: The margin
        summary: Why we hold some back.
        tags: margin
        weights: {keep: 1}
        ---

        # Something else

        [[MARGIN]]
        """,
    )
    assert w.title == "The margin"
    assert w.summary == "Why we hold some back."
    assert w.meta.tags == ["margin"]
    assert w.problems() == []
    assert [r.line for r in w.refs] == [10]


def test_without_front_matter_the_summary_is_the_first_paragraph(repo):
    w = walk(repo, "# Walk\n\nSee [[MARGIN|the margin]] and [why](other.md).\n")
    assert w.summary == "See the margin and why."


def test_front_matter_that_isnt_valid_is_an_error(repo):
    w = walk(repo, "---\ntags: [unclosed\n---\n\n[[MARGIN]]\n")
    (problem,) = w.problems()
    assert problem.severity == "error" and "front matter" in problem.message


def test_codewalks_relate_by_linking_to_each_other(repo):
    from codewalk.walk.library import Library

    (repo / "docs/a.md").write_text("---\ntags: [x, y]\n---\n# A\n\n[[MARGIN]], then [B](b.md#start).\n")
    (repo / "docs/b.md").write_text("---\ntags: [y]\nrelated: [sub/c.md]\n---\n# B\n\n[[MARGIN]]\n")
    (repo / "docs/sub").mkdir()
    (repo / "docs/sub/c.md").write_text("# C\n\n[[MARGIN]]\n")
    (repo / "docs/plain.md").write_text("# Not a codewalk\n\n[A](a.md)\n")
    library = Library.of(ctx(repo))
    a, b, c = (library.get(f"docs/{n}") for n in ("a.md", "b.md", "sub/c.md"))
    assert a.links_to == ["docs/b.md"] and a.linked_from == []
    assert b.links_to == ["docs/sub/c.md"] and b.linked_from == ["docs/a.md"]
    assert c.linked_from == ["docs/b.md"]
    assert library.get("docs/plain.md") is None
    assert library.tags() == [("y", 2), ("x", 1)]
    assert [f for f, _ in library.folders()] == ["docs", "docs/sub"]


# r[verify check.links]
def test_a_link_to_a_markdown_file_that_doesnt_exist_is_an_error(repo):
    w = walk(repo, "# Walk\n\n[[MARGIN]] and [gone](gone.md).\n")
    (problem,) = w.problems()
    assert "gone.md" in problem.message


def test_every_rendered_block_says_which_line_of_the_markdown_it_starts_on(repo):
    w = walk(repo, "# Walk\n\nOne.\n\n- a\n- b\n\n```walk\nMARGIN\n```\n")
    body, _ = render(w)
    assert '<h1 data-md="1"' in body or 'data-md="1"' in body.split("</h1>")[0]
    assert '<p data-md="3">' in body
    assert '<li data-md="6">' in body
    assert '<div class="walk-group" data-md="8" data-md-end="10">' in body
    assert 'data-md="9"' in body.split('<div class="walk-group"')[1]


def test_the_config_rejects_keys_it_doesnt_know(tmp_path):
    from pydantic import ValidationError

    (tmp_path / "codewalk.toml").write_text('sources = ["x/**/*.rs"]\n')
    assert Config.load(tmp_path).sources == ["x/**/*.rs"]
    (tmp_path / "codewalk.toml").write_text('source = ["x/**/*.rs"]\n')
    with pytest.raises(ValidationError):
        Config.load(tmp_path)


# ---- The server ---------------------------------------------------------------------------


@pytest.fixture
def client(repo):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    (repo / "docs/walk.md").write_text("---\ntags: [t]\n---\n# Walk\n\n```walk\nMARGIN\n```\n")
    with TestClient(make_app(ctx(repo), watch=False)) as c:
        yield c


def test_the_pages_render(client):
    index = client.get("/")
    assert index.status_code == 200 and "docs/walk.md" in index.text and 'data-tag="t"' in index.text
    page = client.get("/walk/docs/walk.md")
    assert page.status_code == 200 and 'data-ref="MARGIN"' in page.text
    assert client.get("/edit/docs/walk.md").status_code == 200


# r[verify serve.local+2]
def test_only_codewalks_can_be_edited_or_saved(client, repo):
    assert client.get("/edit/src/lib.rs").status_code == 403
    assert client.post("/api/save", json={"path": "src/lib.rs", "text": "oops"}).status_code == 403
    assert (repo / "src/lib.rs").read_text() == LIB
    assert client.post("/api/save", json={"path": "docs/walk.md", "text": "# New\n"}).json() == {"saved": True}
    assert (repo / "docs/walk.md").read_text() == "# New\n"


# r[verify review.record]
def test_reviewing_through_the_api_records_the_code(client, repo):
    assert client.post("/api/review", json={"path": "docs/walk.md"}).json() == {"reviewed": ["MARGIN"]}
    assert "MARGIN" in json.loads((repo / "codewalk.review.json").read_text())["docs/walk.md"]
    assert "reviewed</span>" in client.get("/walk/docs/walk.md").text


def test_symbols_and_files_are_served_for_the_palette_and_the_context_panel(client):
    (hit,) = [s for s in client.get("/api/symbols", params={"q": "MARGIN"}).json() if s["ref"] == "MARGIN"]
    assert hit["file"] == "src/lib.rs" and hit["line"] == 5
    view = client.get("/api/file", params={"path": "src/lib.rs"}).json()
    assert view["file"] == "src/lib.rs" and len(view["lines"]) == len(LIB.split("\n"))
    assert client.get("/api/file", params={"path": "../etc/passwd"}).status_code == 404


# r[verify serve.files]
def test_a_source_outside_the_root_is_shown_beside_the_page(tmp_path):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    root = tmp_path / "here"
    (root / "docs").mkdir(parents=True)
    (tmp_path / "there/src").mkdir(parents=True)
    (tmp_path / "there/src/lib.rs").write_text(LIB)
    (tmp_path / "secret.rs").write_text("pub fn secret() {}\n")
    (root / "docs/walk.md").write_text("# Walk\n\n```walk\nMARGIN\n```\n")
    with TestClient(make_app(Context(root, Config(sources=["../there/src/**/*.rs"])), watch=False)) as client:
        view = client.get("/api/file", params={"path": "../there/src/lib.rs"}).json()
        assert view["file"] == "../there/src/lib.rs" and len(view["lines"]) == len(LIB.split("\n"))
        assert view["zed"] == f"zed://file/{(tmp_path / 'there/src/lib.rs').resolve()}"
        assert client.get("/api/file", params={"path": "../secret.rs"}).status_code == 404


# ---- Proposals ----------------------------------------------------------------------------


PROPOSAL = """\
# Walk

We'll add [[?Battery::rest]].

```walk proposed rust
Battery::rest
pub fn rest(&mut self) {
    self.power = 0;
}
```
"""


# r[verify proposal.draft+2]
# r[verify proposal.pending]
def test_a_proposal_for_a_name_not_written_yet_is_in_hand_not_broken(repo):
    w = walk(repo, PROPOSAL)
    kinds = sorted((p.severity, p.message) for p in w.problems() if p.severity != "warning")
    assert kinds == [("pending", "`Battery::rest` is proposed, not written yet")]
    (proposal,) = [r for r in w.refs if r.kind == "proposal"]
    assert proposal.draft.startswith("pub fn rest") and proposal.lang == "rust" and proposal.line == 6
    body, _ = render(w)
    assert 'class="walk proposal pending"' in body and "proposed-ref" in body


# r[verify proposal.agree]
def test_agreeing_a_proposal_writes_a_decision_under_it_and_context_says_so(client, repo):
    from codewalk.walk.brief import as_markdown, brief

    (repo / "docs/walk.md").write_text(PROPOSAL + "\nAfter.\n")
    w = Walk(ctx(repo), "docs/walk.md")
    assert w.agreement(w.refs[-1]) is None and "not agreed yet" in as_markdown([brief(ctx(repo), "docs/walk.md")])
    r = client.post("/api/agree", json={"path": "docs/walk.md", "line": 6, "end": 10, "text": "Agreed."})
    assert r.json()["agreed"] == "Battery::rest"
    assert "}\n```\n\n> [!decision]" in (repo / "docs/walk.md").read_text()
    w = Walk(ctx(repo), "docs/walk.md")
    b = brief(ctx(repo), "docs/walk.md")
    assert b.proposed[0].agreed.endswith("Agreed.") and ", agreed (" in as_markdown([b])
    body, _ = render(w)
    assert 'class="badge agreed"' in body and "Agree again" in body
    # Agreeing again, or changing it, goes into the same thread
    client.post("/api/agree", json={"path": "docs/walk.md", "line": 6, "end": 10, "text": "Agreed, but call it `pause`."})
    w = Walk(ctx(repo), "docs/walk.md")
    assert len(w.threads) == 1 and [n.kind for n in w.threads[0].notes] == ["decision", "decision"]
    assert w.agreement(w.refs[-1]).text.startswith("Agreed, but")


# r[verify note.add-settled]
def test_a_settled_thread_can_still_be_answered_or_decided_on(repo):
    w = walk(repo, "# W\n\n```walk\nMARGIN\n```\n\n> [!question] @m: Why?\n>\n> [!answer] @c: Because.\n")
    assert w.threads[0].settled
    body, _ = render(w)
    assert all(f'data-kind="{k}"' in body for k in ("answer", "question", "decision")) and 'data-mode="changelog"' in body


# r[verify proposal.settle+2]
# r[verify proposal.progress+2]
def test_once_written_a_proposal_shows_the_code_against_the_draft_and_can_be_settled(repo):
    from codewalk.walk.doc import settle

    (repo / "src/lib.rs").write_text(
        LIB.replace("impl Battery {", "impl Battery {\n    pub fn rest(&mut self) {\n        self.power = 0;\n    }\n", 1)
    )
    w = walk(repo, PROPOSAL)
    assert [p.severity for p in w.problems() if p.severity != "warning"] == ["pending", "pending"]
    body, _ = render(w)
    assert 'class="walk proposal written"' in body and 'data-action="settle"' in body
    settled = settle(w.text, 6, "Battery::rest")
    assert "```walk settled rust\nBattery::rest\npub fn rest(&mut self) {" in settled and "walk proposed" not in settled

    # Settled, it's an ordinary excerpt of the code as written, with the plan kept
    w = walk(repo, settled)
    assert [p.message for p in w.problems()] == ["`Battery::rest` is written now: settle the `?`"]
    assert w.progress().model_dump() == {"proposed": 0, "written": 0, "settled": 1} and w.progress().status == "done"
    body, _ = render(w)
    assert 'class="badge settled" data-action="plan"' in body and '<pre class="diff plan" hidden>' in body
    assert "```rust\npub fn rest(&mut self) {" in w.export("docs/out.md")


# r[verify note.open]
def test_a_standing_request_is_in_hand_until_its_done(repo):
    from codewalk.walk.brief import brief

    text = "# W\n\n> [!request] @matthew: Use NumPy-style docstrings.\n\n[[MARGIN]]\n"
    w = walk(repo, text)
    (t,) = w.threads
    assert t.request_open and not t.open
    assert [p.message for p in w.problems()] == ["standing request: @matthew: Use NumPy-style docstrings."]
    assert [r.text for r in brief(ctx(repo), "docs/walk.md").requests] == ["@matthew: Use NumPy-style docstrings."]
    done = walk(repo, text.replace("docstrings.\n", "docstrings.\n>\n> [!done] @claude: Converted them.\n"))
    assert not done.threads[0].request_open and done.problems() == []


def test_a_numpy_style_docstring_gives_a_summary_and_its_sections(repo):
    (repo / "pkg").mkdir()
    (repo / "pkg/__init__.py").write_text("")
    (repo / "pkg/m.py").write_text(
        'def f(x):\n    """Do a thing.\n\n    Parameters\n    ----------\n    x : int\n        The thing.\n    """\n'
    )
    index = Context(repo, Config(sources=["pkg/**/*.py"])).index
    sym, _ = index.resolve("pkg::m::f")
    assert sym.doc == "Do a thing."
    assert sym.details == "Parameters\n----------\nx : int\n    The thing."


# ---- Notes --------------------------------------------------------------------------------


THREAD = """\
# Walk

```walk
MARGIN
```

> [!question] @matthew: Why five?
>
> More about why.

Then more prose.
"""


# r[verify note.syntax]
# r[verify note.open]
def test_a_thread_is_parsed_from_a_blockquote_and_is_open_until_answered(repo):
    from codewalk.walk import notes

    w = walk(repo, THREAD)
    (t,) = w.threads
    assert t.open and t.question.author == "matthew" and "More about why." in t.question.text
    assert t.about_line == 3
    assert [p.severity for p in w.problems()] == ["pending"]
    answered = notes.reply(w.text, t, "answer", "claude", "Because it's\\nsafe.")
    w2 = walk(repo, answered)
    (t2,) = w2.threads
    assert [n.kind for n in t2.notes] == ["question", "answer"] and not t2.open
    assert w2.problems() == []
    body, _ = render(w2)
    assert 'class="thread settled"' in body and "@claude" in body


def test_asking_a_question_writes_a_new_thread_after_a_block(repo):
    from codewalk.walk import notes

    text = notes.ask(THREAD, 5, "matthew", "Is this used?")
    assert "```\n\n> [!question] @matthew: Is this used?\n\n> [!question]" in text
    assert len(walk(repo, text).threads) == 2


# r[verify note.syntax]
def test_an_ordinary_blockquote_isnt_a_thread(repo):
    assert walk(repo, "# W\n\n> Just a quote.\n\n[[MARGIN]]\n").threads == []


# r[verify context.brief]
def test_context_briefs_an_agent_on_whats_in_hand(repo):
    from codewalk.walk.brief import as_markdown, brief

    walk(repo, THREAD + "\n```walk proposed\nBattery::rest\nfn rest() {}\n```\n")
    b = brief(ctx(repo), "docs/walk.md")
    assert [q.text for q in b.questions] == ["@matthew: Why five?\n\nMore about why."]
    assert b.questions[0].about == ["MARGIN"]
    assert [p.about for p in b.proposed] == [["Battery::rest"]]
    md = as_markdown([b])
    assert "### Open questions (1)" in md and "### Proposed, not written yet (1)" in md


# ---- Requirements and their code ------------------------------------------------------------


# r[verify spec.traces+2]
def test_a_requirements_markers_in_the_code_are_found_with_the_symbol_theyre_on(repo):
    traces = ctx(repo).index.traces()
    (t,) = traces["battery.command"]
    assert t.kind == "impl" and t.symbol.qualified == "Battery::command"


def test_a_requirement_in_a_walk_block_shows_its_text_and_code(repo):
    w = walk(repo, "# W\n\n```walk\nr:battery.command\nr:nope\n```\n")
    assert [p.message for p in w.problems()] == ["no requirement `nope`"]
    body, data = render(w)
    assert 'class="walk reqfig"' in body and "A battery is told what to do." in body
    assert data["requirements"]["battery.command"]["traces"][0]["name"] == "Battery::command"


# ---- Specs: the prose beside its requirements ----------------------------------------------


SPEC_PROSE = """\
# Spec

We hold some back (`hold.margin`), and we [tell batteries](req:battery.command) what to do.
Soon we'll [[r:battery.rest]].

r[hold.margin]
Hold a margin back.

r[battery.command]
A battery is told what to do.
"""


# r[verify spec.view]
# r[verify spec.cite]
def test_the_spec_view_finds_what_the_prose_cites_and_what_it_doesnt(repo):
    from codewalk.spec import prose

    (repo / "docs/spec/spec.md").write_text(SPEC_PROSE + "\nr[battery.idle]\nAn idle battery rests.\n")
    c = ctx(repo)
    v = prose.view(c, "docs/spec/spec.md")
    assert {x.id: x.state for x in v.citations} == {"hold.margin": "never", "battery.command": "never", "battery.rest": "missing"}
    assert [r.id for r in v.uncited] == ["battery.idle"]
    assert all(x.lines == [3] for x in v.citations if x.id != "battery.rest")


# r[verify spec.drift]
def test_reconciling_records_both_sides_and_a_change_to_either_shows(repo):
    from codewalk.spec import prose

    path = repo / "docs/spec/spec.md"
    path.write_text(SPEC_PROSE)
    c = ctx(repo)
    assert prose.reconcile(c, "docs/spec/spec.md") == ["hold.margin", "battery.command"]
    assert {x.id: x.state for x in prose.view(c, "docs/spec/spec.md").citations}["hold.margin"] == "ok"

    path.write_text(SPEC_PROSE.replace("We hold some back", "We always hold some back"))
    c = ctx(repo)
    assert prose.view(c, "docs/spec/spec.md").citations[0].state == "prose"

    path.write_text(SPEC_PROSE.replace("Hold a margin back.", "Hold a margin of 5 kW back."))
    c = ctx(repo)
    states = {x.id: x.state for x in prose.view(c, "docs/spec/spec.md").citations}
    assert states["hold.margin"] == "spec" and states["battery.command"] == "ok"


def test_a_spec_renders_its_requirements_as_anchors_with_their_code(repo):
    (repo / "docs/spec/spec.md").write_text(SPEC_PROSE)
    w = Walk(ctx(repo), "docs/spec/spec.md")
    body, _ = render(w, spec_mode=True)
    assert 'id="r-hold-margin"' in body and 'class="trace t-impl"' in body
    assert 'class="req cite" href="#" data-req="hold.margin"' in body


# ---- Terms and facts -----------------------------------------------------------------------


GLOSSARY = """\
# Glossary

r[term.deadband]
How far above its target import can rise before we act.

r[term.settlement-period]
A 15-minute period.

r[fact.market.periods] observed
Markets settle every 15 minutes.

r[fact.market.guess]
Something we suppose.
"""


# r[verify glossary.define]
def test_terms_and_facts_are_defined_like_requirements(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY)
    g = ctx(repo).glossary
    assert set(g.terms) == {"deadband", "settlement-period"}
    assert g.facts["market.periods"].status == "observed" and g.facts["market.guess"].status == "assumed"
    assert g.term_for("Settlement Periods").id == "settlement-period"
    assert g.terms["deadband"].text == "How far above its target import can rise before we act."


# r[verify glossary.define]
def test_terms_and_facts_are_not_requirements_and_take_a_specs_prefix(repo):
    defs = "\nr[term.deadband]\nHow far import can rise.\n\nr[fact.meter.rate] observed\nMeters read every 15 minutes.\n"
    (repo / "docs/spec/spec.md").write_text(SPEC + defs)
    c = ctx(repo)
    assert not {k for k in c.spec.requirements if "term." in k or "fact." in k}
    assert c.glossary.terms["deadband"].text == "How far import can rise."
    assert c.glossary.facts["meter.rate"].status == "observed"


# r[verify glossary.cite]
# r[verify glossary.errors]
def test_terms_are_cited_and_mentioned_and_unknown_ones_are_errors(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY)
    w = walk(repo, "# W\n\nThe deadband, the deadband, and [[t:deadband]] and [[f:market.periods]] and [[t:nope]].\n")
    assert [p.message for p in w.problems()] == ["no term `nope`"]
    body, data = render(w)
    assert body.count('class="mention"') == 1
    assert 'class="term fact"' in body and set(data["terms"]) == {"t:deadband", "f:market.periods"}


# r[verify embed.definitions]
def test_terms_and_facts_in_a_walk_block_are_one_table_of_their_definitions(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY)
    w = walk(
        repo,
        "# W\n\n```walk\nt:deadband\nf:market.periods\nt:nope\nMARGIN\nt:settlement-period\n```\n",
    )
    assert [p.message for p in w.problems()] == ["no term `nope`"]
    body, data = render(w)
    # A run of them is one table, in order; a symbol between breaks it
    assert body.count('<table class="definitions">') == 2
    first = body.index("How far above its target import can rise before we act.")
    assert first < body.index("Markets settle every 15 minutes.") < body.index('data-ref="MARGIN"')
    assert body.index('data-ref="MARGIN"') < body.index("A 15-minute period.")
    assert ">deadband<" in body and "market.periods" in body and "observed" in body
    assert {"t:deadband", "f:market.periods", "t:settlement-period"} <= set(data["terms"])
    out = w.export("docs/out.md")
    assert "| Term | Meaning |" in out
    assert "| [deadband](glossary.md#L3) | How far above its target import can rise before we act. |" in out
    assert "| [`market.periods`](glossary.md#L9) (observed) | Markets settle every 15 minutes. |" in out
    assert "**Unresolved:** `t:nope`" in out


# r[verify glossary.cite]
# r[verify note.syntax]
def test_a_note_whose_kind_is_a_term_is_still_a_note(repo):
    (repo / "docs/glossary.md").write_text("# G\n\nr[term.note]\nA paragraph in a blockquote.\n\nr[term.request]\nA standing ask.\n")
    w = walk(repo, "# W\n\n> [!note] A thought.\n\nThen:\n\n> [!request] @m: Keep it short.\n")
    assert [t.notes[0].kind for t in w.threads] == ["note", "request"]
    body, _ = render(w)
    assert "A thought." in body and "Keep it short." in body and "[!" not in body


# r[verify glossary.errors]
def test_a_term_defined_twice_is_an_error_where_its_defined(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY + "\nr[term.deadband]\nAgain.\n")
    w = Walk(ctx(repo), "docs/glossary.md")
    assert any("defined again" in p.message for p in w.problems())


# r[verify glossary.page]
def test_the_glossary_groups_terms_by_the_spec_defining_them(repo):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    (repo / "docs/spec/spec.md").write_text(SPEC + "\n## Terms\n\nr[term.deadband]\nHow far import can rise.\n")
    (repo / "docs/spec/top.md").write_text(
        "---\nweight: 0\n---\n# Top\n\nr[term.site]\nA place with a meter.\n\nr[fact.meter.rate] observed\nMeters read every 15 minutes.\n"
    )
    (repo / "docs/walk.md").write_text("# Walk\n\nThe deadband at a site, by [[MARGIN]].\n")
    client = TestClient(make_app(ctx(repo), watch=False))
    page = client.get("/glossary").text
    top, spec = page.index('href="/spec/docs/spec/top.md">Top'), page.index('href="/spec/docs/spec/spec.md">')
    assert top < page.index('id="t-site"') < page.index('id="f-meter-rate"') < spec < page.index('id="t-deadband"')
    assert 'href="/spec/docs/spec/spec.md#t-deadband"' in page and 'href="/walk/docs/walk.md">docs/walk.md' in page
    # A term's mention links to its definition, in the spec that defines it
    assert 'href="/spec/docs/spec/spec.md#t-deadband"' in client.get("/walk/docs/walk.md").text
    # In the spec itself it's a definition, not a requirement
    spec_page = client.get("/spec/docs/spec/spec.md").text
    assert 'id="t-deadband"' in spec_page and 'id="r-term-deadband"' not in spec_page


# ---- The language server -------------------------------------------------------------------


def test_the_language_server_finds_the_reference_under_the_cursor():
    from codewalk.lsp import completion_query, reference_at

    lines = ["See [[Battery::command|it]] and `hold.margin`.", "", "```walk", "MARGIN > five", "```"]
    assert reference_at(lines, 0, 8) == ("Battery::command", 4, 27)
    assert reference_at(lines, 0, 34)[0] == "r:hold.margin"
    assert reference_at(lines, 3, 2) == ("MARGIN", 0, 6)
    assert reference_at(lines, 0, 1) is None
    assert completion_query(["Then [[Disp"], 0, 11) == ("Disp", 7)
    assert completion_query(["```walk", "Batt"], 1, 4) == ("Batt", 0)
    assert completion_query(["plain text"], 0, 5) is None


# ---- Setting a project up ------------------------------------------------------------------


def test_init_sets_a_project_up_and_running_it_again_changes_nothing(repo):
    from codewalk.setup import init

    (repo / "AGENTS.md").write_text("# Contributing\n\nOur rules.\n")
    done = init(repo, command="codewalk")
    assert done == [
        "wrote: codewalk.toml",
        "added a codewalk section to: AGENTS.md",
        "wrote the skill: .claude/skills/codewalk-propose/SKILL.md",
        "wrote the skill: .claude/skills/codewalk-work/SKILL.md",
    ]
    agents = (repo / "AGENTS.md").read_text()
    assert agents.startswith("# Contributing\n\nOur rules.\n\n<!-- codewalk:start") and "codewalk context" in agents
    assert "name: codewalk-propose" in (repo / ".claude/skills/codewalk-propose/SKILL.md").read_text()
    assert init(repo, command="codewalk") == []
    assert init(repo, command="cw", dry_run=True) == [
        "would update the codewalk section of: AGENTS.md",
        "would write the skill: .claude/skills/codewalk-propose/SKILL.md",
        "would write the skill: .claude/skills/codewalk-work/SKILL.md",
    ]


# ---- Threading, and resolving settled threads ----------------------------------------------


NESTED = """\
# W

[[MARGIN]]

> [!request] @matthew: Use NumPy-style docstrings.
>
> [!done] @claude: Converted every module's. The CLI's are left as they were.
>
> > [!question] @matthew: Why not the CLI's?

The end.
"""


# r[verify note.replies]
def test_a_reply_nests_under_the_note_it_refines_and_keeps_the_thread_open(repo):
    from codewalk.walk import notes

    w = walk(repo, NESTED)
    (t,) = w.threads
    assert [n.kind for n in t.notes] == ["request", "done"]
    (q,) = t.notes[1].replies
    assert q.kind == "question" and q.depth == 1 and q.line == 9
    assert not t.request_open and t.open and not t.settled
    assert [p.message for p in w.problems()] == ["open question: @matthew: Why not the CLI's?"]

    answered = notes.reply_to(w.text, q, "answer", "claude", "Click shows them as help.")
    assert "> > [!question] @matthew: Why not the CLI's?\n> >\n> > > [!answer] @claude: Click shows them as help." in answered
    (t2,) = walk(repo, answered).threads
    assert t2.settled and [n.kind for n in t2.all()] == ["request", "done", "question", "answer"]

    body, _ = render(walk(repo, answered))
    assert body.count('class="replies"') == 2 and 'data-action="resolve" data-mode="changelog"' in body


# r[verify note.resolve]
def test_a_settled_thread_compacts_into_the_changelog_newest_first(repo):
    from codewalk.walk import notes

    w = walk(repo, NESTED)
    settled = notes.reply_to(w.text, w.threads[0].notes[1].replies[0], "answer", "claude", "Click shows them as help.")
    t = walk(repo, settled).threads[0]
    out = notes.resolve(settled, t, "changelog", "2026-11-06", ["MARGIN"])
    assert "[!request]" not in out and "The end." in out and "[[MARGIN]]\n\nThe end." in out
    entry = (
        "- 2026-11-06 (`MARGIN`): **request** @matthew: Use NumPy-style docstrings. → "
        "**answer** @claude: Click shows them as help. (2 more notes)"
    )
    assert out.endswith("## Changelog\n\nWhat was asked here and how it was settled, newest first.\n\n" + entry + "\n")

    second = out.replace("The end.", "> [!question] @a: One?\n>\n> [!answer] @b: Yes.\n\nThe end.")
    out2 = notes.resolve(second, walk(repo, second).threads[0], "changelog", "2026-11-07")
    log = out2[out2.index("## Changelog") :]
    assert log.index("2026-11-07") < log.index("2026-11-06")
    assert "- 2026-11-07: **question** @a: One? → **answer** @b: Yes.\n" in log


# r[verify note.resolve]
# r[verify note.resolve-open]
def test_an_open_thread_cant_be_resolved_and_a_settled_one_can_be_removed(repo):
    from codewalk.walk import notes

    w = walk(repo, NESTED)
    with pytest.raises(ValueError):
        notes.resolve(w.text, w.threads[0], "remove", "2026-11-06")
    done = "# W\n\n> [!request] @m: Do it.\n>\n> [!done] @c: Did it.\n\nAfter.\n"
    assert notes.resolve(done, walk(repo, done).threads[0], "remove", "2026-11-06") == "# W\n\nAfter.\n"


# r[verify note.write]
def test_replying_to_a_note_and_resolving_work_through_the_api(client, repo):
    (repo / "docs/walk.md").write_text(NESTED)
    r = client.post("/api/note", json={"path": "docs/walk.md", "kind": "answer", "text": "Because.", "to": 9})
    assert r.status_code == 200
    assert client.post("/api/resolve", json={"path": "docs/walk.md", "thread": 5, "mode": "changelog"}).json() == {"resolved": "changelog"}
    text = (repo / "docs/walk.md").read_text()
    assert "## Changelog" in text and "[!request]" not in text
    (repo / "docs/walk.md").write_text(NESTED)
    assert client.post("/api/resolve", json={"path": "docs/walk.md", "thread": 5, "mode": "remove"}).status_code == 409


TRACEY = """\
specs (
    {
        name v1
        include (docs/old/**/*.md)
        impls ({ name rust include (src/**/*.rs) })
    }
)
"""


# r[verify spec.files]
# r[verify spec.prefix+2]
def test_a_spec_named_in_traceys_config_is_read_with_its_own_prefix(repo):
    (repo / ".config/tracey").mkdir(parents=True)
    (repo / ".config/tracey/config.styx").write_text(TRACEY)
    (repo / "docs/old").mkdir()
    (repo / "docs/old/old.md").write_text("# Old\n\nIt's told `battery.command`.\n\nv1[battery.command]\nAn old battery is told too.\n")
    c = ctx(repo)
    # The same ID in two specs is two requirements
    assert {"battery.command", "v1:battery.command"} <= set(c.spec.requirements)
    assert c.spec.find("battery.command", "docs/old/old.md").id == "v1:battery.command"
    assert c.spec.find("battery.command").id == "battery.command"
    from codewalk.spec import prose

    assert [x.id for x in prose.view(c, "docs/old/old.md").citations] == ["v1:battery.command"]


# r[verify note.ask-here]
def test_asking_about_one_reference_of_several_splits_its_block_under_it(repo):
    from codewalk.walk import notes

    text = "```walk\nMARGIN\nBattery::command\n```\n"
    out = notes.ask_about(text, 2, "me", "Why five?")
    assert out.startswith("```walk\nMARGIN\n```\n\n> [!question] @me: Why five?\n\n```walk\nBattery::command\n```")
    # About the last one, it goes after the block, which stays whole
    assert notes.ask_about(text, 3, "me", "Why?").startswith(text.rstrip("\n") + "\n\n> [!question]")


# r[verify ui.context]
def test_a_name_in_the_code_means_the_symbol_of_that_name_nearest_it(repo):
    c = ctx(repo)
    s = c.index.named_at("MARGIN", "src/lib.rs", 20)
    assert s and s.name == "MARGIN"
    # Two `command`s in the file: not the one it's written in
    assert c.index.named_at("command", "src/lib.rs", 18).qualified.endswith("other::Battery::command")
    assert c.index.named_at("nothing", "src/lib.rs", 1) is None


# r[verify ui.index]
def test_the_index_lists_specs_as_a_tree_of_folders(repo):
    from codewalk.walk.library import Library

    (repo / "docs/spec/v2").mkdir()
    (repo / "docs/spec/v2/more.md").write_text("# _More_\n\nr[more.thing]\nA thing.\n")
    rows = [(d, f or s.rel) for d, f, s in Library.of(ctx(repo)).spec_tree()]
    assert rows == [(0, "docs/spec/spec.md"), (0, "v2"), (1, "docs/spec/v2/more.md")]


OUTLINED = '''\
class Store:
    """Keeps things.

    Parameters
    ----------
    root : str
        Where.
    """

    # How many it holds
    size: int = 3

    def __init__(self, root: str):
        """Open it."""
        self.root = root

    def get(self, key: str) -> str:
        """One thing."""
        return key
'''


# r[verify ref.sig+2]
def test_sig_shows_a_python_classs_docstring_fields_and_init_header(pyrepo):
    (pyrepo / "pkg/outlined.py").write_text(OUTLINED)
    c = pyctx(pyrepo)
    s, _ = c.index.resolve("outlined::Store")
    # The header and docstring, the field with its comment, then `__init__` to its docstring
    assert s.outline == [(1, 8), (10, 11), (13, 14)]
    get, _ = c.index.resolve("Store::get")
    assert get.outline == [(get.line, get.line + 1)]
    path = pyrepo / "docs/walk.md"
    path.write_text("```walk\noutlined::Store sig\n```\n")
    html, _ = render(Walk(c, "docs/walk.md"))
    assert "Keeps things" in html and "size" in html and "__init__" in html
    assert "One thing" not in html


# r[verify spec.cite]
def test_a_citation_written_in_backticks_is_an_example_not_a_citation(repo):
    from codewalk.spec.prose import cited_ids

    known = ctx(repo).spec
    assert cited_ids("cite with `[[r:some.id]]`, like [[r:hold.margin]], or `hold.margin`", known) == ["hold.margin"]


# r[verify walk.what]
def test_a_codewalk_is_markdown_in_the_docs_that_makes_a_reference_and_isnt_spec(repo):
    (repo / "docs/plain.md").write_text("# Nothing here\n\nJust words.\n")
    (repo / "docs/walk.md").write_text("# Walk\n\nSee [[MARGIN]].\n")
    assert ctx(repo).codewalks() == ["docs/walk.md"]


# r[verify spec.trail]
def test_a_blocks_requirements_are_in_the_margin_linked_to_their_prose(repo):
    from codewalk.spec import trail
    from codewalk.web.server import App

    (repo / "docs/spec/spec.md").write_text("# Spec\n\nWe hold some back (`hold.margin`).\n\n" + SPEC.split("\n", 2)[2])
    w = walk(repo, "# W\n\n```walk\nMARGIN\n```\n")
    assert [(link.id, link.role) for link in trail.links(w)] == [("hold.margin", "implements")]
    html, data, _ = App(ctx(repo)).walk_body("docs/walk.md")
    assert data["margin"] and 'data-go="/spec/docs/spec/spec.md?line=3&amp;req=hold.margin"' in html


# r[verify serve.live]
def test_a_change_to_a_codewalk_or_the_code_reaches_the_pages(repo):
    from codewalk.web.server import App

    (repo / "docs/walk.md").write_text("# Walk\n\nSee [[MARGIN]].\n")
    app = App(ctx(repo))
    assert app.changed({str(repo / "docs/walk.md")}).docs == ["docs/walk.md"]
    (repo / "src/lib.rs").write_text(LIB + "\npub fn more() {}\n")
    assert app.changed({str(repo / "src/lib.rs")}).code


# r[verify serve.live.settle]
def test_a_moved_source_is_indexed_at_its_new_path(repo):
    from codewalk.web.server import App

    (repo / "src/v2").mkdir()
    (repo / "src/v2/service.rs").write_text("pub fn run() {}\n")
    app = App(ctx(repo))
    assert app.ctx.index.resolve("run")[0].file == "src/v2/service.rs"
    (repo / "src/v2/service.rs").rename(repo / "src/service.rs")
    (repo / "src/v2").rmdir()
    assert app.changed({str(repo / "src/v2/service.rs"), str(repo / "src/service.rs")}).code
    assert app.ctx.index.resolve("run")[0].file == "src/service.rs"


# r[verify serve.live.settle]
def test_a_source_gone_while_the_index_is_read_is_left_out(repo, monkeypatch):
    index = ctx(repo).index
    found = index.paths()
    monkeypatch.setattr(index, "paths", lambda: [*found, "src/gone.rs"])
    index.refresh()
    assert {s.file for s in index.symbols} == {"src/lib.rs"}


# r[verify serve.live.settle]
def test_a_change_caught_half_made_is_read_again_and_never_stops_the_watching(repo, monkeypatch):
    import asyncio

    from codewalk.web.server import App

    app = App(ctx(repo))
    real, calls = app.changed, []

    def flaky(paths):
        calls.append(paths)
        if len(calls) == 1:
            raise FileNotFoundError("src/lib.rs went mid-read")
        return real(paths)

    monkeypatch.setattr(app, "changed", flaky)
    (repo / "src/lib.rs").write_text(LIB + "\npub fn more() {}\n")
    assert asyncio.run(app.catch_up({str(repo / "src/lib.rs")}, wait=0)).code
    assert len(calls) == 2

    def broken(paths):
        raise ValueError("the review file is half-written")

    monkeypatch.setattr(app, "changed", broken)
    assert asyncio.run(app.catch_up({str(repo / "codewalk.review.json")}, tries=3, wait=0)) is None


# r[verify review.people]
def test_reading_checking_and_exporting_never_mark_anything_reviewed(repo):
    w = walk(repo, "# W\n\n```walk\nMARGIN\n```\n")
    render(w)
    w.problems()
    w.export("out.md")
    assert not (repo / "codewalk.review.json").exists()


# r[verify context.brief]
def test_context_takes_in_questions_asked_in_a_spec(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    (repo / "docs/spec/spec.md").write_text(SPEC + "\n> [!question] @matthew: Is this what we mean?\n")
    monkeypatch.chdir(repo)
    out = CliRunner().invoke(main, ["context"]).output
    assert "docs/spec/spec.md" in out and "Is this what we mean?" in out


# r[verify serve.stop]
def test_the_server_stops_on_ctrl_c_with_a_page_open(repo):
    import signal
    import socket
    import subprocess
    import sys
    import time

    import httpx

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    (repo / "docs/walk.md").write_text("# Walk\n\nSee [[MARGIN]].\n")
    proc = subprocess.Popen(
        [sys.executable, "-c", "from codewalk.cli import main; main()", "serve", "--port", str(port)],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                httpx.get(url, timeout=1)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        # A page open: its event stream held open, as a browser would
        with httpx.stream("GET", f"{url}/events", timeout=10) as events:
            next(events.iter_lines())
            began = time.monotonic()
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=8)
        assert time.monotonic() - began < 4
    finally:
        proc.kill()


# r[verify ui.weight]
def test_codewalks_and_specs_are_listed_in_order_of_weight(repo):
    from codewalk.walk.library import Library

    for name, front in [("b", "weight: 20"), ("a", ""), ("c", "weight: 10"), ("d", "")]:
        (repo / f"docs/{name}.md").write_text(f"---\n{front}\n---\n# {name.upper()}\n\nSee [[MARGIN]].\n")
    (repo / "docs/spec/first.md").write_text("---\nweight: 1\n---\n# Z first\n\nr[first.thing]\nA thing.\n")
    lib = Library.of(ctx(repo))
    [(_, walks)] = lib.folders()
    assert [s.title for s in walks] == ["C", "B", "A", "D"]
    assert [s.rel for _, _, s in lib.spec_tree() if s] == ["docs/spec/first.md", "docs/spec/spec.md"]


# ---- PRDs ----------------------------------------------------------------------------------

PRD = """\
---
title: "Stop a battery"
kind: prd
stage: {stage}
---

# Stop a battery

r[battery.command+2]
A battery is told what to do, and for how long.

r[battery.stop]
A battery can be stopped.

r[hold.margin+2] removed

r[hold.margin]
Hold a margin back.

r[term.deadband]
How far import can rise before we act.

r[term.site]
A place with a meter.
"""

GLOSSARY_DEADBAND = "# G\n\nr[term.deadband]\nHow far import can rise.\n"


def prd(repo: Path, text: str, rel: str = "docs/prd/x.md") -> Walk:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text)
    return Walk(ctx(repo), rel)


# r[verify spec.prefix+2]
# r[verify spec.traces+2]
def test_a_versioned_requirement_and_its_traces_are_read_with_their_versions(repo):
    (repo / "docs/spec/spec.md").write_text(SPEC.replace("r[battery.command]", "r[battery.command+2]"))
    (repo / "src/lib.rs").write_text(LIB.replace("// r[impl battery.command]", "// r[impl battery.command+2]"))
    c = ctx(repo)
    assert c.spec.requirements["battery.command"].version == 2 and c.spec.requirements["hold.margin"].version == 1
    (trace,) = c.index.traces()["battery.command"]
    assert trace.version == 2 and trace.symbol.qualified.endswith("Battery::command")
    sym, _ = c.index.resolve("crate::Battery::command")
    assert sym.markers == [("impl", "battery.command", 2)]


# r[verify prd.requirements]
# r[verify prd.terms]
def test_a_prds_requirements_and_terms_are_its_own_not_the_specs(repo):
    from codewalk.walk.prd import spec_changes

    (repo / "docs/glossary.md").write_text(GLOSSARY_DEADBAND)
    w = prd(repo, PRD.format(stage="spec"))
    c = w.ctx
    assert "battery.stop" not in c.spec.requirements and c.spec.requirements["battery.command"].version == 1
    assert c.glossary.terms["deadband"].file == "docs/glossary.md" and "site" not in c.glossary.terms
    assert not c.glossary.duplicates
    changes = {(ch.kind, ch.id): ch for ch in spec_changes(w)}
    assert changes[("term", "deadband")].how == "changed" and changes[("term", "deadband")].was == "How far import can rise."
    assert changes[("term", "site")].how == "new"


# r[verify prd.compare]
def test_a_prds_requirements_are_new_changed_removed_quoted_or_in_error_against_the_spec(repo):
    from codewalk.walk.prd import spec_changes

    extra = "\nr[battery.command]\nSomething else.\n\nr[nothing.here+2] removed\n"
    w = prd(repo, PRD.format(stage="spec") + extra)
    reqs = [(c.id, c.how) for c in spec_changes(w) if c.kind == "requirement"]
    assert reqs == [
        ("battery.command", "changed"),
        ("battery.stop", "new"),
        ("hold.margin", "removed"),
        ("hold.margin", "quoted"),
        ("battery.command", "error"),
        ("nothing.here", "error"),
    ]
    changed = spec_changes(w)[0]
    assert (changed.version, changed.was) == (2, "A battery is told what to do.")
    body, _ = render(w)
    assert body.count("prd-req how-") == 6 and "<del>" in body and "<ins>" in body
    assert "without a new version" in body and "which the spec doesn&#39;t have" in body


# r[verify glossary.errors]
def test_a_term_a_prd_redefines_or_defines_and_cites_is_not_an_error(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY_DEADBAND)
    w = prd(repo, PRD.format(stage="spec") + "\nA [[t:site]] has a [[t:deadband]].\n")
    assert not [p.message for p in w.problems() if p.severity == "error"]
    # Elsewhere, a term only a PRD defines isn't defined
    other = walk(repo, "# W\n\nA [[t:site]].\n")
    assert [p.message for p in other.problems()] == ["no term `site`"]


# r[verify prd.check+2]
def test_check_fails_on_a_prd_that_changes_a_requirement_without_a_new_version(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    monkeypatch.chdir(repo)
    prd(repo, PRD.format(stage="spec"))
    assert CliRunner().invoke(main, ["check"]).exit_code == 0
    prd(repo, PRD.format(stage="spec") + "\nr[battery.command]\nSomething else.\n")
    out = CliRunner().invoke(main, ["check"])
    assert out.exit_code == 1 and "without a new version" in out.output and "docs/prd/x.md" in out.output


# r[verify prd.check+2]
def test_a_done_prd_isnt_checked_against_the_spec_as_it_has_moved_on(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    monkeypatch.chdir(repo)
    stale = PRD.format(stage="work") + "\nr[battery.command]\nSomething else.\n"
    w = prd(repo, stale)
    assert w.done and CliRunner().invoke(main, ["check"]).exit_code == 0
    # At the work stage with a proposal still to settle, it's checked as any other
    waiting = stale + "\n```walk proposed rust\n?crate::Battery::stop\npub fn stop(&mut self) {}\n```\n"
    w = prd(repo, waiting)
    assert not w.done
    out = CliRunner().invoke(main, ["check"])
    assert out.exit_code == 1 and "without a new version" in out.output


# r[verify prd.stage]
def test_a_prds_stage_is_read_from_its_front_matter_and_shown(client, repo):
    from codewalk.walk.brief import as_markdown, brief
    from codewalk.walk.library import Library

    w = prd(repo, PRD.format(stage="prose"))
    prd(repo, "---\nkind: prd\n---\n# Y\n\nNothing yet.\n", "docs/prd/y.md")
    assert w.meta.stage == "prose"
    lib = Library.of(ctx(repo))
    assert lib.get("docs/prd/x.md").stage == "prose" and lib.get("docs/prd/y.md").stage == "problem"
    assert "PRD · prose" in client.get("/").text
    assert "<option selected>prose</option>" in client.get("/walk/docs/prd/x.md").text
    assert "at the **prose** stage" in as_markdown([brief(ctx(repo), "docs/prd/x.md")])


# r[verify prd.stage-set]
def test_setting_a_prds_stage_from_its_page_writes_its_front_matter(client, repo):
    prd(repo, PRD.format(stage="prose"))
    assert client.post("/api/stage", json={"path": "docs/prd/x.md", "stage": "spec"}).json() == {"stage": "spec"}
    text = (repo / "docs/prd/x.md").read_text()
    assert "stage: spec" in text and "stage: prose" not in text and Walk(ctx(repo), "docs/prd/x.md").meta.stage == "spec"
    assert client.post("/api/stage", json={"path": "docs/prd/x.md", "stage": "done"}).status_code == 409
    assert client.post("/api/stage", json={"path": "docs/walk.md", "stage": "spec"}).status_code == 409


# r[verify prd.stage-gate]
def test_work_written_ahead_of_a_prds_stage_is_a_warning(repo):
    proposal = "\n```walk proposed rust\nBattery::stop\npub fn stop(&mut self) {}\n```\n"
    w = prd(repo, PRD.format(stage="prose") + proposal)
    warnings = [p.message for p in w.problems() if p.severity == "warning"]
    assert warnings.count("a requirement at the prose stage") == 4 and "a proposal at the prose stage" in warnings
    w = prd(repo, PRD.format(stage="spec") + proposal)
    assert [p.message for p in w.problems() if p.severity == "warning"] == ["a proposal at the spec stage"]
    w = prd(repo, PRD.format(stage="code") + proposal)
    assert not [p for p in w.problems() if p.severity == "warning"]


# r[verify prd.template]
def test_a_new_prd_has_a_section_for_each_stage_and_nothing_in_hand(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    monkeypatch.chdir(repo)
    assert CliRunner().invoke(main, ["new", "docs/prd/x.md", "--title", "X", "--prd"]).exit_code == 0
    w = Walk(ctx(repo), "docs/prd/x.md")
    assert (w.meta.kind, w.meta.stage, w.title) == ("prd", "problem", "X")
    assert all(f"## {s}\n" in w.text for s in ("The problem", "What we want", "The spec", "The code"))
    assert not w.problems() and not w.threads and w.progress().proposed == 0


# r[verify proposal.draft+2]
def test_a_proposal_named_with_a_question_mark_is_the_name_without_it(repo):
    w = walk(repo, "# W\n\n```walk proposed rust\n?crate::Battery::command\npub fn command() {}\n```\n")
    (proposal,) = [r for r in w.refs if r.kind == "proposal"]
    assert proposal.target == "crate::Battery::command" and proposal.symbol is not None


# r[verify proposal.indent]
def test_a_draft_indented_as_its_code_sits_in_the_file_differs_only_where_it_changes(repo):
    lines = LIB.split("\n")
    start = lines.index("    /// Tell it what to do.")
    end = start + lines[start:].index("    }")
    draft = "\n".join(lines[start : end + 1]).replace("self.power = 0;", "self.power = 1;")
    w = walk(repo, f"# W\n\n```walk proposed change rust\ncrate::Battery::command\n{draft}\n```\n")
    body, _ = render(w)
    assert body.count('class="drow add"') == 1 and body.count('class="drow del"') == 1
    assert '<span class="drow add"><span class="dt">+</span>            self.power = 1;</span>' in body


# r[verify proposal.change+2]
def test_a_proposed_change_shows_its_draft_against_the_code_until_settled(repo):
    from codewalk.walk.doc import settle

    draft = "pub fn command(&mut self, power: i32) -> bool {\n    self.power = power;\n    power == 0\n}"
    text = f"# W\n\n```walk proposed change rust\ncrate::Battery::command\n{draft}\n```\n"
    w = walk(repo, text)
    (ref,) = [r for r in w.refs if r.kind == "proposal"]
    assert ref.change and ref.symbol and ref.lang == "rust"
    assert (w.progress().proposed, w.progress().written) == (1, 0)
    assert [p.message for p in w.problems() if p.severity != "warning"] == [
        "a change to `crate::Battery::command` is proposed, not made yet"
    ]
    body, _ = render(w)
    # Not made yet, so it's agreed, not settled
    assert 'data-action="settle"' not in body and 'data-action="agree"' in body
    # From the code as it is to the draft: what the change adds is added
    assert 'class="walk proposal change"' in body
    assert '<span class="drow add"><span class="dt">+</span>    power == 0</span>' in body
    assert '<span class="drow del"><span class="dt">-</span>    match power {</span>' in body
    assert "```walk settled change rust\ncrate::Battery::command\n" in settle(w.text, ref.line, "crate::Battery::command")
    broken = walk(repo, text.replace("crate::Battery::command", "crate::Battery::halt"))
    assert [p.severity for p in broken.problems() if p.severity != "warning"] == ["error"]


# r[verify prd.start+2]
def test_starting_a_prd_from_the_index_writes_it_with_what_was_asked(client, repo):
    r = client.post("/api/prd", json={"title": "Stop a battery!", "ask": "Batteries need stopping."})
    today = date.today().isoformat()
    rel = f"docs/prds/{today}-1-stop-a-battery.md"
    assert r.json() == {"started": rel, "href": f"/walk/{rel}"}
    w = Walk(ctx(repo), rel)
    assert (w.meta.kind, w.meta.stage, w.title) == ("prd", "problem", "Stop a battery!")
    (t,) = w.threads
    assert t.notes[0].kind == "request" and t.request_open and t.notes[0].text.strip() == "Batteries need stopping."
    assert client.post("/api/prd", json={"title": "Stop a battery", "ask": "Again."}).status_code == 409
    # The next that day is the next number
    r = client.post("/api/prd", json={"title": "Start a battery", "ask": "And starting."})
    assert r.json()["started"] == f"docs/prds/{today}-2-start-a-battery.md"
    assert 'data-action="new-prd"' in client.get("/").text


# r[verify prd.template]
def test_a_comment_in_a_codewalk_isnt_shown(repo):
    body, _ = render(walk(repo, "# W\n\n<!-- For whoever edits it.\nOn two lines. -->\n\nShown.\n"))
    assert "whoever" not in body and "Shown." in body


# r[verify serve.live]
def test_pages_link_the_script_and_styles_by_what_is_in_them(client):
    import re

    page = client.get("/").text
    js, css = re.search(r'src="(/static/app\.js\?v=[0-9a-f]{10})"', page), re.search(r'href="(/static/app\.css\?v=[0-9a-f]{10})"', page)
    assert js and css
    assert client.get(js.group(1)).status_code == 200 and client.get(css.group(1)).status_code == 200


# ---- Better codewalks ----------------------------------------------------------------------


# r[verify proposal.draft+2]
def test_a_proposal_in_a_codewalk_that_isnt_a_prd_is_a_warning(repo):
    warning = "`Battery::rest` is proposed in a codewalk that isn't a PRD: propose it in one"
    assert [p.message for p in walk(repo, PROPOSAL).problems() if p.severity == "warning"] == [warning]
    w = prd(repo, "---\nkind: prd\nstage: code\n---\n" + PROPOSAL)
    assert not [p for p in w.problems() if p.severity == "warning"]


# r[verify proposal.progress+2]
def test_only_a_prd_shows_its_progress(client, repo):
    (repo / "docs/walk.md").write_text(PROPOSAL)
    prd(repo, "---\nkind: prd\nstage: code\n---\n" + PROPOSAL)
    assert "0/1 settled" not in client.get("/walk/docs/walk.md").text
    assert "PRD proposed: 0/1 settled" in client.get("/walk/docs/prd/x.md").text
    assert client.get("/").text.count('<div class="progress"') == 1


# r[verify prd.from-thread]
def test_a_prd_started_from_a_thread_and_the_thread_link_to_each_other(client, repo):
    (repo / "docs/walk.md").write_text("# Walk\n\n```walk\nMARGIN\n```\n\n> [!question] @m: Why hold back so much?\n")
    (thread,) = Walk(ctx(repo), "docs/walk.md").threads
    assert 'data-action="prd-from-thread"' in client.get("/walk/docs/walk.md").text
    r = client.post("/api/prd", json={"title": "Hold less", "ask": "Hold back less.", "source": "docs/walk.md", "thread": thread.line})
    rel = f"docs/prds/{date.today().isoformat()}-1-hold-less.md"
    assert r.json() == {"started": rel, "href": f"/walk/{rel}"}
    request = Walk(ctx(repo), rel).threads[0].notes[0]
    assert request.kind == "request" and request.text.strip().endswith("From [Walk](../walk.md).")
    (thread,) = Walk(ctx(repo), "docs/walk.md").threads
    assert [(n.kind, n.text.strip()) for n in thread.all()][-1] == (
        "note",
        f"Taken up in a PRD: [Hold less](prds/{date.today().isoformat()}-1-hold-less.md).",
    )
    # A PRD's own threads don't offer it
    assert 'data-action="prd-from-thread"' not in client.get(f"/walk/{rel}").text
    bad = client.post("/api/prd", json={"title": "Other", "ask": "x", "source": "docs/walk.md", "thread": 1})
    assert bad.status_code == 409 and not list((repo / "docs/prds").glob("*-other.md"))


# r[verify glossary.define]
# r[verify glossary.cite]
def test_a_cited_only_term_is_linked_only_where_its_cited(repo):
    (repo / "docs/glossary.md").write_text(
        "# G\n\nr[term.target] cited-only\nWhat a site aims for.\n\nr[fact.odd] cited-only\nNot a fact.\n"
    )
    g = ctx(repo).glossary
    assert g.terms["target"].cited_only and "odd" not in g.facts
    w = walk(repo, "# W\n\nThe target moves, and a [[t:target]] is set.\n")
    body, data = render(w)
    assert 'class="mention"' not in body and "t:target" in data["terms"] and not w.problems()


# r[verify ui.edit-margin]
def test_the_editor_can_put_the_margin_away(client, repo):
    page = client.get("/edit/docs/spec/spec.md").text
    assert 'id="margin-toggle"' in page and '"margin": true' in page
    css = client.get("/static/app.css").text
    assert ".editor.with-context .preview .prose.spec .margin { display: none; }" in css


# ---- Workspaces ----------------------------------------------------------------------------


def _project(folder: Path, walk: str = "# Walk\n\nSee [[MARGIN]].\n") -> Path:
    """A project in `folder`: the tiny crate, its spec, a codewalk, and a `codewalk.toml`."""
    (folder / "src").mkdir(parents=True)
    (folder / "src/lib.rs").write_text(LIB)
    (folder / "docs/spec").mkdir(parents=True)
    (folder / "docs/spec/spec.md").write_text(SPEC)
    (folder / "docs/walk.md").write_text(walk)
    (folder / "codewalk.toml").write_text('sources = ["src/**/*.rs"]\n')
    return folder


@pytest.fixture
def workspace(tmp_path):
    _project(tmp_path / "alpha")
    _project(tmp_path / "beta", "# Beta\n\nSee [[MARGIN]] and [the walk](walk.md).\n")
    # A folder that could be a project, and a project too deep to be one of this workspace's
    (tmp_path / "gamma/notes/spec").mkdir(parents=True)
    (tmp_path / "gamma/Cargo.toml").write_text("[package]\n")
    _project(tmp_path / "gamma/deeper")
    return tmp_path


@pytest.fixture
def served(workspace):
    from starlette.testclient import TestClient

    from codewalk.web.workspace import Workspace

    with TestClient(Workspace(workspace, watch=False).starlette) as c:
        yield c


# r[verify serve.workspace]
def test_a_workspace_is_the_folders_one_level_down_with_a_codewalk_toml(workspace):
    from codewalk.web.workspace import find_projects

    assert [p.name for p in find_projects(workspace)] == ["alpha", "beta"]


# r[verify serve.workspace-pages]
def test_each_project_is_served_under_its_own_path_and_its_links_stay_there(served):
    home = served.get("/", follow_redirects=False)
    assert home.status_code in (302, 307) and home.headers["location"] == "/p/alpha/"
    index = served.get("/p/alpha/").text
    assert 'href="/p/alpha/walk/docs/walk.md"' in index and 'href="/p/alpha/glossary"' in index
    assert '"base": "/p/alpha"' in index
    page = served.get("/p/beta/walk/docs/walk.md").text
    assert 'href="/p/beta/walk/docs/walk.md"' in page and 'class="walklink"' in page
    assert served.get("/p/beta/api/file", params={"path": "src/lib.rs"}).json()["file"] == "src/lib.rs"
    assert served.get("/static/app.js").status_code == 200


# r[verify ui.project]
def test_every_page_offers_the_projects_with_its_own_chosen(served):
    page = served.get("/p/beta/walk/docs/walk.md").text
    assert '<option value="alpha">alpha</option>' in page
    assert '<option value="beta" selected>beta</option>' in page
    assert "Add project…" in page
    js = served.get("/static/app.js").text
    assert "location.href = `/p/${encodeURIComponent(pick.value)}/`" in js


# r[verify ui.project-add]
# r[verify serve.local+2]
def test_a_folder_is_added_as_a_project_with_its_chosen_folders(served, workspace):
    info = served.get("/api/workspace").json()
    assert info["projects"] == ["alpha", "beta"]
    (gamma,) = info["candidates"]
    assert gamma["name"] == "gamma" and gamma["sources"] == ["src/**/*.rs"]
    assert {"notes", "notes/spec", "deeper"} <= set(gamma["folders"])

    out = served.post("/api/workspace/projects", json={"folder": "gamma", "docs": "notes", "specs": "notes/spec"})
    assert out.json() == {"project": "gamma", "href": "/p/gamma/"}
    toml = (workspace / "gamma/codewalk.toml").read_text()
    assert 'sources = ["src/**/*.rs"]' in toml and 'specs = ["notes/spec/**/*.md"]' in toml
    assert 'docs = ["notes/**/*.md"]' in toml
    assert served.get("/p/gamma/").status_code == 200
    assert served.get("/api/workspace").json()["projects"] == ["alpha", "beta", "gamma"]

    assert served.post("/api/workspace/projects", json={"folder": "gamma", "docs": "notes"}).status_code == 409
    assert served.post("/api/workspace/projects", json={"folder": "../elsewhere", "docs": "x"}).status_code == 409
    assert not (workspace.parent / "elsewhere").exists()


# ---- Reading a branch's worktrees ----------------------------------------------------------


def _git(cwd: Path, *args: str) -> None:
    import subprocess

    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


WALK_ON_BRANCH = """\
# Walk

```walk
MARGIN
src::Battery::command
other::Battery
src::fresh
```
"""


@pytest.fixture
def branched(tmp_path):
    """A project and a crate beside it, each a repository with a worktree on `feat`: there,
    the crate changes `MARGIN`, drops `other`, and adds `fresh`."""
    crate, project = tmp_path / "crate", tmp_path / "project"
    (crate / "src").mkdir(parents=True)
    (crate / "src/lib.rs").write_text(LIB)
    (project / "src").mkdir(parents=True)
    (project / "src/lib.rs").write_text("/// The project's own.\npub fn own() {}\n")
    (project / "docs").mkdir()
    (project / "docs/walk.md").write_text(WALK_ON_BRANCH)
    (project / "codewalk.toml").write_text('sources = ["src/**/*.rs", "../crate/src/**/*.rs"]\n')
    for repo in (crate, project):
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "start")
        _git(repo, "worktree", "add", "-q", "-b", "feat", f"../{repo.name}-feat", "main")
    changed = LIB.replace("MARGIN: u32 = 5", "MARGIN: u32 = 7")
    changed = changed[: changed.index("pub mod other")] + "/// New on the branch.\npub fn fresh() {}\n"
    (tmp_path / "crate-feat/src/lib.rs").write_text(changed)
    return project


def _branch_ctx(project: Path):
    from codewalk.code.worktrees import branches

    config = Config.load(project)
    return Context(project, config, branches(project, config.sources)["feat"])


# r[verify review.branches]
# r[verify review.branch-base]
def test_a_branch_with_worktrees_in_the_projects_repositories_is_found_with_its_base(branched):
    from codewalk.code.worktrees import branches

    found = branches(branched, Config.load(branched).sources)
    assert list(found) == ["feat"]
    checkouts = {c.prefix: c for c in found["feat"].checkouts}
    assert set(checkouts) == {"", "../crate/"}
    assert checkouts["../crate/"].worktree.name == "crate-feat" and checkouts["../crate/"].base_ref == "main"


# r[verify review.branch-code]
def test_on_a_branch_the_code_is_read_from_its_worktrees_under_the_same_names(branched):
    ctx = _branch_ctx(branched)
    sym, _ = ctx.index.resolve("MARGIN")
    assert sym.file == "../crate/src/lib.rs" and "= 7" in sym.text(ctx.index.files)
    assert ctx.index.where(sym.file).parent.parent.name == "crate-feat"
    assert ctx.index.resolve("other::Battery")[0] is None
    assert Context(branched, Config.load(branched)).index.resolve("other::Battery")[0] is not None


# r[verify review.branch-diff]
# r[verify review.branch-gone]
def test_on_a_branch_each_symbol_is_shown_against_where_the_branch_started(branched):
    body, _ = render(Walk(_branch_ctx(branched), "docs/walk.md"))
    figures = body.split("<figure")[1:]
    margin, command, other, fresh = figures
    assert "changed on feat" in margin and '<pre class="diff branch">' in margin
    assert '<span class="drow del"><span class="dt">-</span>pub const MARGIN: u32 = 5;</span>' in margin
    assert '<span class="drow add"><span class="dt">+</span>pub const MARGIN: u32 = 7;</span>' in margin
    assert "unchanged on feat" in command and '<pre class="code">' in command
    assert "gone on feat" in other and 'class="drow add"' not in other
    assert '<span class="drow del"><span class="dt">-</span>pub struct Battery;</span>' in other
    assert "new on feat" in fresh


# r[verify review.branch-pick]
# r[verify review.branch-code]
def test_a_branch_is_chosen_for_every_page_and_back_without_writing_anything(branched):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    before = {p: p.read_bytes() for p in branched.parent.rglob("*") if p.is_file() and ".git" not in p.parts}
    with TestClient(make_app(Context(branched, Config.load(branched)), watch=False)) as client:
        assert "Code: as checked out" in client.get("/walk/docs/walk.md").text
        listed = client.get("/api/branches").json()
        assert listed == {"current": None, "branches": [{"name": "feat", "repos": ["project", "crate"], "base": ["main"]}]}
        assert client.post("/api/branch", json={"branch": "feat"}).json() == {"branch": "feat"}
        page = client.get("/walk/docs/walk.md").text
        assert "Code: feat" in page and "changed on feat" in page
        assert client.post("/api/branch", json={"branch": "nope"}).status_code == 404
        client.post("/api/branch", json={"branch": None})
        assert "changed on feat" not in client.get("/walk/docs/walk.md").text
    after = {p: p.read_bytes() for p in branched.parent.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert after == before


# ---- Pinning a codewalk to a ref ----------------------------------------------------------

PINNED = """\
---
at: walks/v1
---

# Walk

See [[other::Battery]].

```walk
MARGIN
other::Battery
```
"""


@pytest.fixture
def pinned(repo):
    """The repository tagged `walks/v1`, then `MARGIN` changed and `other` dropped, with a
    codewalk pinned to the tag."""
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "start")
    _git(repo, "tag", "walks/v1")
    now = LIB.replace("MARGIN: u32 = 5", "MARGIN: u32 = 7")
    (repo / "src/lib.rs").write_text(now[: now.index("pub mod other")])
    (repo / "docs/walk.md").write_text(PINNED)
    return repo


# r[verify pin.at]
# r[verify pin.everywhere]
def test_a_pinned_codewalk_is_read_at_its_ref_from_git_without_writing_anything(pinned):
    before = {p: p.read_bytes() for p in pinned.rglob("*") if p.is_file() and ".git" not in p.parts}
    w = Walk(ctx(pinned), "docs/walk.md")
    assert w.problems() == []
    assert w.ctx.pin.ref == "walks/v1" and w.ctx.index.on_disk("src/lib.rs") is None
    import re

    body = re.sub(r"<[^>]+>", "", render(w)[0])
    assert "MARGIN: u32 = 5" in body and "pub struct Battery;" in body
    assert "= 7" not in body
    assert "MARGIN: u32 = 5" in w.export("docs/out.md")
    # The project itself is read as it is
    assert ctx(pinned).index.resolve("other::Battery")[0] is None
    after = {p: p.read_bytes() for p in pinned.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert after == before


# r[verify pin.broken]
def test_a_pin_that_names_no_commit_is_an_error(pinned):
    (pinned / "docs/walk.md").write_text(PINNED.replace("walks/v1", "walks/nope"))
    problems = Walk(ctx(pinned), "docs/walk.md").problems()
    assert any(p.line == 1 and p.severity == "error" and "walks/nope" in p.message for p in problems)


# r[verify pin.label]
# r[verify pin.everywhere]
def test_a_pinned_codewalks_page_and_files_beside_it_are_at_its_ref(pinned):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    with TestClient(make_app(ctx(pinned), watch=False)) as client:
        page = client.get("/walk/docs/walk.md").text
        assert "Pinned at walks/v1" in page and '"at": "walks/v1"' in page
        view = client.get("/api/file", params={"path": "src/lib.rs", "at": "walks/v1"}).json()
        assert view["zed"] is None and any(o["qualified"] == "other" for o in view["outline"])
        now = client.get("/api/file", params={"path": "src/lib.rs"}).json()
        assert now["zed"] and not any(o["qualified"] == "other" for o in now["outline"])
        named = client.get("/api/named", params={"name": "Battery", "file": "src/lib.rs", "line": 47, "at": "walks/v1"})
        assert named.json()["qualified"] == "other::Battery"
        assert client.get("/api/file", params={"path": "src/lib.rs", "at": "walks/nope"}).status_code == 404


# r[verify pin.own-repo]
# r[verify pin.everywhere]
def test_a_pinned_codewalk_reads_other_repositories_as_checked_out_whatever_branch_is_read(branched):
    _git(branched, "tag", "walks/v1")
    (branched / "src/lib.rs").write_text("pub fn later() {}\n")
    (branched / "docs/walk.md").write_text("---\nat: walks/v1\n---\n\n# Walk\n\n```walk\nown\nMARGIN\n```\n")
    (branched.parent / "crate/src/lib.rs").write_text(LIB.replace("MARGIN: u32 = 5", "MARGIN: u32 = 9"))
    for c in (Context(branched, Config.load(branched)), _branch_ctx(branched)):
        w = Walk(c, "docs/walk.md")
        assert w.problems() == []
        own = next(r for r in w.embeds if r.target == "own").symbol
        margin = next(r for r in w.embeds if r.target == "MARGIN").symbol
        assert own.file == "src/lib.rs"
        assert "= 9" in margin.text(w.ctx.index.files)


# r[verify ui.context-link]
def test_a_link_to_a_source_file_opens_it_beside_the_page_at_its_lines(repo):
    w = walk(
        repo,
        """\
        # Walk

        See [the crate](../src/lib.rs), [its margin](../src/lib.rs#L4-L5),
        [one line](../src/lib.rs#L5), [nothing](../src/nope.rs) and [the web](https://example.com).

        ```walk
        MARGIN
        ```
        """,
    )
    body, _ = render(w)
    assert '<a href="../src/lib.rs" class="srclink" data-file="src/lib.rs">the crate</a>' in body
    assert 'class="srclink" data-file="src/lib.rs" data-start="4" data-end="5">its margin</a>' in body
    assert 'data-start="5" data-end="5">one line</a>' in body
    assert '<a href="../src/nope.rs">nothing</a>' in body
    assert '<a href="https://example.com">the web</a>' in body


# r[verify review.reopen]
def test_a_reviewed_excerpt_can_be_reopened_so_it_reads_as_not_reviewed(client, repo):
    assert 'data-action="review"' in client.get("/walk/docs/walk.md").text
    client.post("/api/review", json={"path": "docs/walk.md", "ref": "MARGIN"})
    page = client.get("/walk/docs/walk.md").text
    assert 'data-action="reopen"' in page and 'data-action="review" ' not in page
    assert client.post("/api/reopen", json={"path": "docs/walk.md", "ref": "MARGIN"}).json() == {"reopened": "MARGIN"}
    page = client.get("/walk/docs/walk.md").text
    assert 'data-action="review"' in page and "not reviewed" in page
    assert "docs/walk.md" not in json.loads((repo / "codewalk.review.json").read_text())
    assert client.post("/api/reopen", json={"path": "docs/walk.md", "ref": "MARGIN"}).status_code == 404


# r[verify embed.names]
def test_types_variants_and_constants_are_coloured_by_how_theyre_named():
    from codewalk.code.highlight import highlight_text

    (arm, call) = highlight_text("Setpoint::Idle => x,\nlet band = TOLERANCE_KW.max(power_kw);", "rust")
    assert '<span class="nc">Setpoint</span>' in arm and '<span class="nc">Idle</span>' in arm
    assert '<span class="n">x</span>' in arm
    assert '<span class="no">TOLERANCE_KW</span>' in call and '<span class="n">power_kw</span>' in call
    (py,) = highlight_text("x = Battery(MARGIN, A)", "python")
    assert '<span class="nc">Battery</span>' in py and '<span class="no">MARGIN</span>' in py
    assert '<span class="n">A</span>' in py


# r[verify proposal.unsettle]
# r[verify proposal.settle+2]
def test_a_settled_block_can_be_unsettled_back_to_the_proposal_it_was(client, repo):
    # Made: the code is as the draft says, the body as now
    draft = "/// Tell it what to do.\n// r[impl battery.command]\npub fn command(&mut self, power: i32) -> bool {\n    // … as now …\n}"
    text = f"# W\n\n```walk proposed change rust\ncrate::Battery::command\n{draft}\n```\n"
    (repo / "docs/walk.md").write_text(text)
    assert client.post("/api/settle", json={"path": "docs/walk.md", "line": 4}).json() == {"settled": "crate::Battery::command"}
    settled = (repo / "docs/walk.md").read_text()
    assert "```walk settled change rust\n" in settled
    (ref,) = [r for r in Walk(ctx(repo), "docs/walk.md").refs if r.settled]
    assert ref.lang == "rust"
    assert 'data-action="unsettle"' in client.get("/walk/docs/walk.md").text
    assert client.post("/api/unsettle", json={"path": "docs/walk.md", "line": 4}).json() == {"unsettled": "crate::Battery::command"}
    assert (repo / "docs/walk.md").read_text() == text
    assert client.post("/api/unsettle", json={"path": "docs/walk.md", "line": 4}).status_code == 404
    # A new name's proposal goes back to `walk proposed`
    from codewalk.walk.doc import settle, unsettle

    assert unsettle(settle(PROPOSAL, 6, "Battery::rest"), 6) == PROPOSAL


# r[verify proposal.change+2]
def test_a_change_is_made_once_the_code_matches_its_draft_with_elisions_for_any_lines(repo):
    from codewalk.walk.doc import matches_draft

    code = "fn f() {\n    let a = 1;\n\n    a + 1\n}"
    assert matches_draft(code, "fn f() {\nlet a = 1;\na + 1\n}")
    assert not matches_draft(code, "fn f() {\n    let a = 2;\n    a + 1\n}")
    assert matches_draft(code, "fn f() {\n    // … as now …\n}")
    assert matches_draft(code, "fn f() {\n    let a = 1;\n    // … the rest …\n    a + 1\n}")
    assert not matches_draft(code, "fn f() {\n    // … as now …\n    a + 2\n}")
    # Made, it counts as written and can be settled
    draft = "/// Tell it what to do.\n// r[impl battery.command]\npub fn command(&mut self, power: i32) -> bool {\n    // … as now …\n}"
    w = walk(repo, f"# W\n\n```walk proposed change rust\ncrate::Battery::command\n{draft}\n```\n")
    assert (w.progress().proposed, w.progress().written) == (0, 1)
    assert [p.message for p in w.problems() if p.severity == "pending"] == [
        "the change to `crate::Battery::command` is made now: settle the proposal"
    ]
    body, _ = render(w)
    assert 'data-action="settle"' in body and "change made" in body


# r[verify ui.prd-requirement]
def test_a_prds_requirement_can_be_opened_in_zed_and_asked_about(repo):
    w = prd(repo, PRD.format(stage="spec"))
    body, _ = render(w)
    req = body[body.index('id="r-battery-command"') :]
    req = req[: req.index("</div>\n</div>")]
    assert 'data-md="9" data-md-end="10"' in body
    assert f'href="zed://file/{(repo / "docs/prd/x.md").resolve()}:9"' in req and 'data-action="ask"' in req
