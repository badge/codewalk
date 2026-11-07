"""codewalk against a small repository of its own, so the tests don't move with the code
this project is used on."""

import json
import textwrap
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


# r[verify index.languages]
def test_an_impl_block_is_named_by_impl_and_its_type(repo):
    index = ctx(repo).index
    sym, candidates = index.resolve("impl Battery")
    assert sym is None and len(candidates) == 2
    sym, _ = index.resolve("impl other::Battery")
    assert sym and sym.kind == "impl"
    assert index.shortest_unique(sym) == "impl other::Battery"


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


# ---- Walkthroughs -----------------------------------------------------------------------


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


# r[verify ref.focus]
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


# r[verify ref.focus]
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
# r[verify index.languages]
def test_python_symbols_are_named_from_their_package(pyrepo):
    index = pyctx(pyrepo).index
    names = {s.qualified: s.kind for s in index.symbols if s.file.endswith(".py")}
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


# ---- Front matter, and how walkthroughs relate ---------------------------------------------


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


def test_walkthroughs_relate_by_linking_to_each_other(repo):
    from codewalk.walk.library import Library

    (repo / "docs/a.md").write_text("---\ntags: [x, y]\n---\n# A\n\n[[MARGIN]], then [B](b.md#start).\n")
    (repo / "docs/b.md").write_text("---\ntags: [y]\nrelated: [sub/c.md]\n---\n# B\n\n[[MARGIN]]\n")
    (repo / "docs/sub").mkdir()
    (repo / "docs/sub/c.md").write_text("# C\n\n[[MARGIN]]\n")
    (repo / "docs/plain.md").write_text("# Not a walkthrough\n\n[A](a.md)\n")
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


# r[verify serve.local]
def test_only_walkthroughs_can_be_edited_or_saved(client, repo):
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


# r[verify proposal.draft]
# r[verify proposal.pending]
def test_a_proposal_for_a_name_not_written_yet_is_in_hand_not_broken(repo):
    w = walk(repo, PROPOSAL)
    kinds = sorted((p.severity, p.message) for p in w.problems())
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


# r[verify proposal.settle]
# r[verify proposal.progress]
def test_once_written_a_proposal_shows_the_code_against_the_draft_and_can_be_settled(repo):
    from codewalk.walk.doc import settle

    (repo / "src/lib.rs").write_text(
        LIB.replace("impl Battery {", "impl Battery {\n    pub fn rest(&mut self) {\n        self.power = 0;\n    }\n", 1)
    )
    w = walk(repo, PROPOSAL)
    assert [p.severity for p in w.problems()] == ["pending", "pending"]
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

t[deadband]
How far above its target import can rise before we act.

t[settlement-period]
A 15-minute period.

f[market.periods] observed
Markets settle every 15 minutes.

f[market.guess]
Something we suppose.
"""


# r[verify term.define]
def test_terms_and_facts_are_defined_like_requirements(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY)
    g = ctx(repo).glossary
    assert set(g.terms) == {"deadband", "settlement-period"}
    assert g.facts["market.periods"].status == "observed" and g.facts["market.guess"].status == "assumed"
    assert g.term_for("Settlement Periods").id == "settlement-period"
    assert g.terms["deadband"].text == "How far above its target import can rise before we act."


# r[verify term.cite]
# r[verify term.errors+2]
def test_terms_are_cited_and_mentioned_and_unknown_ones_are_errors(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY)
    w = walk(repo, "# W\n\nThe deadband, the deadband, and [[t:deadband]] and [[f:market.periods]] and [[t:nope]].\n")
    assert [p.message for p in w.problems()] == ["no term `nope`"]
    body, data = render(w)
    assert body.count('class="mention"') == 1
    assert 'class="term fact"' in body and set(data["terms"]) == {"t:deadband", "f:market.periods"}


# r[verify term.cite]
# r[verify note.syntax]
def test_a_note_whose_kind_is_a_term_is_still_a_note(repo):
    (repo / "docs/glossary.md").write_text("# G\n\nt[note]\nA paragraph in a blockquote.\n\nt[request]\nA standing ask.\n")
    w = walk(repo, "# W\n\n> [!note] A thought.\n\nThen:\n\n> [!request] @m: Keep it short.\n")
    assert [t.notes[0].kind for t in w.threads] == ["note", "request"]
    body, _ = render(w)
    assert "A thought." in body and "Keep it short." in body and "[!" not in body


# r[verify term.errors+2]
def test_a_term_defined_twice_is_an_error_where_its_defined(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY + "\nt[deadband]\nAgain.\n")
    w = Walk(ctx(repo), "docs/glossary.md")
    assert any("defined again" in p.message for p in w.problems())


# r[verify term.glossary]
def test_the_glossary_groups_terms_by_the_spec_defining_them(repo):
    from starlette.testclient import TestClient

    from codewalk.web.server import make_app

    (repo / "docs/spec/spec.md").write_text(SPEC + "\n## Terms\n\nt[deadband]\nHow far import can rise.\n")
    (repo / "docs/spec/top.md").write_text(
        "---\nweight: 0\n---\n# Top\n\nt[site]\nA place with a meter.\n\nf[meter.rate] observed\nMeters read every 15 minutes.\n"
    )
    (repo / "docs/walk.md").write_text("# Walk\n\nThe deadband at a site, by [[MARGIN]].\n")
    client = TestClient(make_app(ctx(repo), watch=False))
    page = client.get("/glossary").text
    top, spec = page.index('href="/spec/docs/spec/top.md">Top'), page.index('href="/spec/docs/spec/spec.md">')
    assert top < page.index('id="t-site"') < page.index('id="f-meter-rate"') < spec < page.index('id="t-deadband"')
    assert 'href="/spec/docs/spec/spec.md#t-deadband"' in page and 'href="/walk/docs/walk.md">docs/walk.md' in page
    # A term's mention links to its definition, in the spec that defines it
    assert 'href="/spec/docs/spec/spec.md#t-deadband"' in client.get("/walk/docs/walk.md").text


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


# r[verify ref.sig]
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
def test_a_walkthrough_is_markdown_in_the_docs_that_makes_a_reference_and_isnt_spec(repo):
    (repo / "docs/plain.md").write_text("# Nothing here\n\nJust words.\n")
    (repo / "docs/walk.md").write_text("# Walk\n\nSee [[MARGIN]].\n")
    assert ctx(repo).walkthroughs() == ["docs/walk.md"]


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
def test_a_change_to_a_walkthrough_or_the_code_reaches_the_pages(repo):
    from codewalk.web.server import App

    (repo / "docs/walk.md").write_text("# Walk\n\nSee [[MARGIN]].\n")
    app = App(ctx(repo))
    assert app.changed({str(repo / "docs/walk.md")}).docs == ["docs/walk.md"]
    (repo / "src/lib.rs").write_text(LIB + "\npub fn more() {}\n")
    assert app.changed({str(repo / "src/lib.rs")}).code


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
def test_walkthroughs_and_specs_are_listed_in_order_of_weight(repo):
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

t[deadband]
How far import can rise before we act.

t[site]
A place with a meter.
"""

GLOSSARY_DEADBAND = "# G\n\nt[deadband]\nHow far import can rise.\n"


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


# r[verify term.errors+2]
def test_a_term_a_prd_redefines_or_defines_and_cites_is_not_an_error(repo):
    (repo / "docs/glossary.md").write_text(GLOSSARY_DEADBAND)
    w = prd(repo, PRD.format(stage="spec") + "\nA [[t:site]] has a [[t:deadband]].\n")
    assert not [p.message for p in w.problems() if p.severity == "error"]
    # Elsewhere, a term only a PRD defines isn't defined
    other = walk(repo, "# W\n\nA [[t:site]].\n")
    assert [p.message for p in other.problems()] == ["no term `site`"]


# r[verify prd.check]
def test_check_fails_on_a_prd_that_changes_a_requirement_without_a_new_version(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    monkeypatch.chdir(repo)
    prd(repo, PRD.format(stage="spec"))
    assert CliRunner().invoke(main, ["check"]).exit_code == 0
    prd(repo, PRD.format(stage="spec") + "\nr[battery.command]\nSomething else.\n")
    out = CliRunner().invoke(main, ["check"])
    assert out.exit_code == 1 and "without a new version" in out.output and "docs/prd/x.md" in out.output


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


# r[verify proposal.change]
def test_a_proposed_change_shows_its_draft_against_the_code_until_settled(repo):
    from codewalk.walk.doc import settle

    draft = "pub fn command(&mut self, power: i32) -> bool {\n    self.power = power;\n    power == 0\n}"
    text = f"# W\n\n```walk proposed change rust\ncrate::Battery::command\n{draft}\n```\n"
    w = walk(repo, text)
    (ref,) = [r for r in w.refs if r.kind == "proposal"]
    assert ref.change and ref.symbol and ref.lang == "rust"
    assert (w.progress().proposed, w.progress().written) == (1, 0)
    assert [p.message for p in w.problems()] == ["a change to `crate::Battery::command` is proposed, not settled yet"]
    body, _ = render(w)
    # From the code as it is to the draft: what the change adds is added
    assert 'class="walk proposal change"' in body
    assert '<span class="drow add"><span class="dt">+</span>    power == 0</span>' in body
    assert '<span class="drow del"><span class="dt">-</span>    match power {</span>' in body
    assert "```walk settled rust\ncrate::Battery::command\n" in settle(w.text, ref.line, "crate::Battery::command")
    broken = walk(repo, text.replace("crate::Battery::command", "crate::Battery::halt"))
    assert [p.severity for p in broken.problems()] == ["error"]


# r[verify prd.start]
def test_starting_a_prd_from_the_index_writes_it_with_what_was_asked(client, repo):
    r = client.post("/api/prd", json={"title": "Stop a battery!", "ask": "Batteries need stopping."})
    assert r.json() == {"started": "docs/prd/stop-a-battery.md", "href": "/walk/docs/prd/stop-a-battery.md"}
    w = Walk(ctx(repo), "docs/prd/stop-a-battery.md")
    assert (w.meta.kind, w.meta.stage, w.title) == ("prd", "problem", "Stop a battery!")
    (t,) = w.threads
    assert t.notes[0].kind == "request" and t.request_open and t.notes[0].text.strip() == "Batteries need stopping."
    assert client.post("/api/prd", json={"title": "Stop a battery", "ask": "Again."}).status_code == 409
    assert 'data-action="new-prd"' in client.get("/").text


# r[verify prd.template]
def test_a_comment_in_a_walkthrough_isnt_shown(repo):
    body, _ = render(walk(repo, "# W\n\n<!-- For whoever edits it.\nOn two lines. -->\n\nShown.\n"))
    assert "whoever" not in body and "Shown." in body
