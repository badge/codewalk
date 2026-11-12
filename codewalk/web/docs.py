"""An excerpt's docs, as prose.

An excerpt's code is shown line by line, but its docs are shown as what they say. A run of
Rust doc comments (`///` or `//!`) is Markdown, as rustdoc reads it: its code blocks are
highlighted, as Rust unless they say otherwise, without the lines rustdoc hides, and an
intra-doc link (`[`Name`]`) links to the symbol it names, if codewalk can find it. A
Python docstring is NumPy style: its text is Markdown, and each entry in its Parameters,
Returns, Raises and like sections is a name and a type, with its description as Markdown
below.
"""

from __future__ import annotations

import html
import re
import textwrap
from collections.abc import Callable

from markdown_it import MarkdownIt

from codewalk.code.highlight import highlight_text

RUST_DOC = re.compile(r"^\s*//[/!](?![/!])")
PY_DOC_OPEN = re.compile(r"""^\s*[rRuU]?("{3}|'{3})""")
# An intra-doc link with no target of its own: `[`Name`]` or `[Name]`, `[`f()`]`
INTRA = re.compile(r"\[(`?)([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)(?:\(\))?\1\](?![\[(:])")
# A link target that's a Rust path, which rustdoc resolves, not a URL
PATH = re.compile(r"[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*(?:\(\))?")
# What rustdoc reads in a code block's info string, all of which still means Rust
RUSTDOC_ATTRS = re.compile(r"rust|no_run|ignore|should_panic|compile_fail|test_harness|edition\d+|E\d{4}|")
# A NumPy section's heading: a line, then a line of dashes under it
SECTION = re.compile(r"^(\S[^\n]*)\n-{3,}[ \t]*$", re.MULTILINE)
# The sections whose entries are a name, a type, or both (`name : type`), each with its
# description indented below; in the ones that list types, an entry alone is a type
ENTRIES = {"parameters", "other parameters", "attributes", "returns", "yields", "receives", "raises", "warns"}
TYPED = {"returns", "yields", "raises", "warns"}

# Something that links a name in the docs to its symbol: the opening tag, or None if it
# names nothing codewalk knows
Linker = Callable[[str], str | None]


def doc_runs(lines: list[str], highlighted: list[str], suffix: str) -> list[tuple[int, int]]:
    """Where the docs are in a run of lines.

    Parameters
    ----------
    lines : list of str
        The lines, as written.
    highlighted : list of str
        The same lines, highlighted: a Python docstring is told from any other string by
        the class Pygments gives it.
    suffix : str
        The file's suffix, `.rs` or `.py`.

    Returns
    -------
    list of tuple of (int, int)
        Each run of docs, as the indices of its first and last lines.
    """
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if suffix == ".rs" and RUST_DOC.match(lines[i]):
            j = i
            while j + 1 < len(lines) and RUST_DOC.match(lines[j + 1]):
                j += 1
            runs.append((i, j))
            i = j + 1
        elif suffix == ".py" and (m := PY_DOC_OPEN.match(lines[i])) and 'class="sd"' in highlighted[i]:
            quote, j = m.group(1), i
            if lines[i].count(quote) < 2:
                j += 1
                while j < len(lines) and quote not in lines[j]:
                    j += 1
            runs.append((i, min(j, len(lines) - 1)))
            i = j + 1
        else:
            i += 1
    return runs


def _fence(self, tokens, idx, options, env) -> str:
    tok = tokens[idx]
    attrs = [a.strip() for a in tok.info.replace(" ", ",").split(",") if a.strip()]
    rust = all(RUSTDOC_ATTRS.fullmatch(a) for a in attrs)
    python = env.get("lang") == "python"
    lang = (attrs[0] if attrs else "python") if python else ("rust" if rust else attrs[0])
    rust = rust and not python
    code = tok.content.rstrip("\n")
    if rust:
        # The lines rustdoc runs but doesn't show
        code = "\n".join(line for line in code.split("\n") if line.strip() != "#" and not line.lstrip().startswith("# "))
    label = ", ".join(a for a in attrs if a not in ("rust", "python", "pycon"))
    head = f'<span class="doc-lang">{html.escape(label)}</span>' if label else ""
    body = "\n".join(highlight_text(code, lang))
    return f'<div class="doc-code">{head}<pre><code>{body}</code></pre></div>\n'


def _link_open(self, tokens, idx, options, env) -> str:
    href = str(tokens[idx].attrGet("href") or "")
    if PATH.fullmatch(href):
        opened = env["link"](href)
        env["closing"].append("</a>" if opened else "")
        return opened or ""
    env["closing"].append("</a>")
    return self.renderToken(tokens, idx, options, env)


def _link_close(self, tokens, idx, options, env) -> str:
    return env["closing"].pop() if env["closing"] else "</a>"


_md = MarkdownIt("commonmark").enable(["table", "strikethrough"])
_md.add_render_rule("fence", _fence)
_md.add_render_rule("link_open", _link_open)
_md.add_render_rule("link_close", _link_close)


def rust_doc_html(lines: list[str], link: Linker) -> str:
    """A run of Rust doc comments, as HTML.

    Parameters
    ----------
    lines : list of str
        The comment lines, as written.
    link : Linker
        Links a name in an intra-doc link to its symbol.

    Returns
    -------
    str
        The docs, rendered as Markdown.
    """
    text = "\n".join(RUST_DOC.sub("", line).removeprefix(" ") for line in lines)
    text = INTRA.sub(lambda m: f"[{m.group(0)[1:-1]}]({m.group(2)})", text)
    return _md.render(text, {"link": link, "closing": []})


def _markdown(text: str) -> str:
    """Markdown from a docstring: its code blocks are Python unless they say otherwise."""
    return _md.render(text, {"link": lambda name: None, "closing": [], "lang": "python"})


def _head(line: str, typed: bool) -> str:
    """An entry's first line, `name : type`, as its name and its type, both as code. In a
    section that lists types, a line with no ` : ` is a type; elsewhere, a name."""
    name, sep, kind = (part.strip() for part in line.partition(" : "))
    if not sep and typed:
        name, kind = "", name
    head = [f'<code class="doc-name">{html.escape(name)}</code>'] if name else []
    head += [f"<code>{html.escape(kind)}</code>"] if kind else []
    return f"<dt>{' : '.join(head)}</dt>"


def _entries(body: str, typed: bool) -> str:
    """A section's entries: each an unindented line, then its description, indented."""
    out: list[str] = []
    desc: list[str] = []
    for line in body.split("\n") + ["\0"]:
        if line[:1].strip():
            if out:
                out.append(f"<dd>{_markdown(textwrap.dedent(chr(10).join(desc)))}</dd>")
            if line != "\0":
                out.append(_head(line, typed))
            desc = []
        else:
            desc.append(line)
    return f'<dl class="doc-entries">{"".join(out)}</dl>'


def python_doc_html(lines: list[str]) -> str:
    """A NumPy-style Python docstring, as HTML.

    Its text is Markdown. Each entry in a section that lists names or types (Parameters,
    Returns, Raises, …) is its name and its type, both as code, with its description below, as
    Markdown. An Examples section that's a Python session is highlighted as one.

    Parameters
    ----------
    lines : list of str
        The docstring's lines, quotes and all.

    Returns
    -------
    str
        The HTML.
    """
    raw = "\n".join(lines).strip()
    raw = re.sub(r"""^[rRuU]?("{3}|'{3})|("{3}|'{3})$""", "", raw)
    first, _, rest = raw.partition("\n")
    text = (first.strip() + "\n" + textwrap.dedent(rest)).strip("\n")
    parts = SECTION.split(text)
    out = [_markdown(parts[0])]
    for title, body in zip(parts[1::2], parts[2::2], strict=True):
        key = title.strip().lower()
        body = body.strip("\n")
        out.append(f'<div class="doc-h">{html.escape(title.strip())}</div>')
        if key in ENTRIES:
            out.append(_entries(body, key in TYPED))
        elif key == "examples" and ">>>" in body:
            out.append(_markdown(f"```pycon\n{body}\n```"))
        else:
            out.append(_markdown(body))
    return "".join(out)
