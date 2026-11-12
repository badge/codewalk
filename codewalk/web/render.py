"""A codewalk as HTML, for the web view.

markdown-it renders the prose; codewalk takes over its fences (a `walk` block becomes the
code it names), its links (`walk:` links become symbols) and the `[[…]]` token. The
markup for an embedded symbol, a broken reference and a diff is in `templates/`.

Every block carries `data-md`, its first line in the Markdown, so the editor and the
preview can be scrolled together and a click in one finds its place in the other.
"""

from __future__ import annotations

import difflib
import html
import json
import os
import re
import textwrap
from contextvars import ContextVar
from functools import cached_property

from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup

from codewalk.code.highlight import highlight_text
from codewalk.code.index import Symbol
from codewalk.spec import terms, tracey
from codewalk.spec.requirements import Requirement
from codewalk.spec.terms import DEF_LINE, Definition
from codewalk.walk.doc import Ref, Walk, embed_line
from codewalk.walk.notes import KINDS, blocks, parse_notes, threads
from codewalk.walk.prd import SpecChange, spec_changes
from codewalk.walk.review import diff
from codewalk.web.docs import doc_runs, python_doc_html, rust_doc_html

templates = Environment(loader=PackageLoader("codewalk.web"), autoescape=select_autoescape(), trim_blocks=True, lstrip_blocks=True)

# The path the project's pages are under: nothing for a server of one project, and
# `/p/<name>` for one of a workspace's. Set for the work done for a request.
BASE: ContextVar[str] = ContextVar("base", default="")


# r[impl serve.workspace-pages]
def base() -> str:
    """The path the current project's pages are under; empty for a server of one."""
    return BASE.get()


templates.globals["base"] = base


def inline_md(text: str) -> Markup:
    """A title's inline Markdown (emphasis, code) as HTML."""
    return Markup(MarkdownIt("commonmark").renderInline(text or ""))


def plain_md(text: str) -> str:
    """A title's text, without its Markdown."""
    return re.sub(r"<[^>]+>", "", MarkdownIt("commonmark").renderInline(text or "")).replace("&amp;", "&")


templates.filters["inline"] = inline_md
templates.filters["plain"] = plain_md
REQ_IN_CODE = tracey.MARKER
NOTE_HEAD = re.compile(rf"^(<p[^>]*>)\[!({'|'.join(KINDS)})\][ \t]*(?:@([\w.\-]+):?)?[ \t]*", re.IGNORECASE)
# A paragraph that's only an HTML comment, which Markdown elsewhere doesn't show either
COMMENT = re.compile(r"\A\s*<!--.*?-->\s*\Z", re.DOTALL)
# A note's kind and author, at the start of its text: never linked to a term, so a note
# whose kind is also a term (`note`, `request`) is still read as one
NOTE_MARK = re.compile(rf"^\[!(?:{'|'.join(KINDS)})\][ \t]*(?:@[\w.\-]+:?)?", re.IGNORECASE)
_plain = MarkdownIt("commonmark")


def definitions_table(rows: list[str]) -> str:
    """A run of terms and facts in a `walk` block, as one table."""
    return '<table class="definitions"><tbody>' + "".join(rows) + "</tbody></table>"


def requirement_html(text: str) -> Markup:
    """A requirement's text, which is Markdown, as HTML.

    Parameters
    ----------
    text : str
        The Markdown.

    Returns
    -------
    Markup
        The HTML, marked safe for the templates.
    """
    return Markup(_plain.render(text))


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def symbol_data(walk: Walk, s: Symbol) -> dict:
    """What the page knows about a symbol, for hover cards and the context panel.

    Parameters
    ----------
    walk : Walk
        The codewalk the page shows.
    s : Symbol
        The symbol.

    Returns
    -------
    dict
        Its names, place, signature, docs and markers, and a link to open it in Zed.
    """
    return {
        "qualified": s.qualified,
        "short": walk.ctx.index.shortest_unique(s),
        "kind": s.kind,
        "file": s.file,
        "start": s.start,
        "line": s.line,
        "end": s.end,
        "signature": s.signature,
        "doc": s.doc,
        "details": s.details,
        "markers": s.markers,
        "zed": walk.ctx.index.zed(s.file, s.line),
    }


def path_parts(qualified: str) -> list[tuple[str, str]]:
    """A qualified name in parts to show.

    Parameters
    ----------
    qualified : str
        The name, with `::` between parts.

    Returns
    -------
    list of tuple of (str, str)
        Each part with its class: `qual` for the module path (muted), `owner` for the type
        it's in, and `name` for the name itself.
    """
    parts = qualified.split("::")
    split = next((i for i, part in enumerate(parts[:-1]) if part[:1].isupper()), len(parts) - 1)
    return [(p, "qual") for p in parts[:split]] + [(p, "owner") for p in parts[split:-1]] + [(parts[-1], "name")]


# r[impl proposal.indent]
def _draft(ref: Ref) -> str:
    """A proposal's draft without the indentation its lines share, as its code is shown.

    Parameters
    ----------
    ref : Ref
        The proposal.

    Returns
    -------
    str
        The draft, dedented; empty if it has none.
    """
    return textwrap.dedent(ref.draft or "")


def _dedent_html(line: str, n: int) -> str:
    """Take `n` leading spaces off a highlighted line, which may sit inside a span."""
    if n == 0:
        return line
    m = re.match(rf"^((?:<span[^>]*>)?)( {{0,{n}}})", line)
    return m.group(1) + line[m.end() :] if m else line


def word_diff(before: str, after: str) -> Markup:
    """`after` against `before`, word by word: what's gone struck out, what's new marked."""
    a, b = before.split(), after.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            out.append(f"<del>{html.escape(' '.join(a[i1:i2]))}</del>")
        if op in ("insert", "replace"):
            out.append(f"<ins>{html.escape(' '.join(b[j1:j2]))}</ins>")
        if op == "equal":
            out.append(html.escape(" ".join(a[i1:i2])))
    return Markup(" ".join(out))


def diff_rows(before: str, after: str, context: int = 2) -> list[dict]:
    """What changed, as the changed lines with a little context either side.

    Runs of unchanged lines between them collapse to a gap saying how many.

    Parameters
    ----------
    before, after : str
        The text before and after.
    context : int
        How many unchanged lines to keep either side of a change.

    Returns
    -------
    list of dict
        Rows for the diff template: `del`, `add` or `same` with the line, or `gap` with a count.
    """
    lines = diff(before, after)
    near = {j for i, (tag, _) in enumerate(lines) if tag != " " for j in range(i - context, i + context + 1)}
    rows, skipped = [], 0
    for i, (tag, text) in enumerate(lines):
        if i not in near:
            skipped += 1
            continue
        if skipped:
            rows.append({"kind": "gap", "count": skipped})
            skipped = 0
        rows.append({"kind": {"-": "del", "+": "add", " ": "same"}[tag], "tag": tag, "text": text})
    if skipped:
        rows.append({"kind": "gap", "count": skipped})
    return rows


class Renderer:
    """Renders one codewalk, collecting what its page needs as it goes.

    Parameters
    ----------
    walk : Walk
        The codewalk, parsed.
    spec_mode : bool
        Whether it's a spec, whose requirements are rendered as anchors with their code.
    """

    def __init__(self, walk: Walk, spec_mode: bool = False):
        self.walk = walk
        # A spec file: `r[id]` paragraphs are requirements, shown as such
        self.spec_mode = spec_mode
        self.ctx = walk.ctx
        # A PRD: what it proposes for the spec, by the line each is written on
        self.prd: dict[int, SpecChange] = {c.line: c for c in spec_changes(walk)} if walk.meta.kind == "prd" else {}
        self.symbols: dict[str, dict] = {}
        self.requirements: dict[str, dict] = {}
        # Terms and facts it mentions or cites, by `t:id` or `f:id`
        self.definitions: dict[str, dict] = {}
        self.by_line = {(r.line, r.key if r.kind == "embed" else r.target): r for r in walk.refs}

    @cached_property
    def codewalks(self) -> set[str]:
        return set(self.ctx.codewalks())

    @cached_property
    def specs(self) -> set[str]:
        return set(self.ctx.spec_paths())

    def note_requirements(self, ids) -> None:
        for rid in ids:
            if rid not in self.requirements and (r := self.ctx.spec.requirements.get(rid)):
                self.requirements[rid] = {**r.model_dump(), "traces": self.traces(rid)}

    def traces(self, rid: str) -> list[dict]:
        """The code that names a requirement, for its hover card and figure.

        Parameters
        ----------
        rid : str
            The requirement's ID.

        Returns
        -------
        list of dict
            Each marker's kind and place, and the symbol it's in or on.
        """
        index = self.ctx.index
        return [
            {
                "kind": t.kind,
                "file": t.file,
                "line": t.line,
                "name": index.shortest_unique(t.symbol) if t.symbol else f"{t.file}:{t.line}",
                "start": t.symbol.start if t.symbol else t.line,
                "end": t.symbol.end if t.symbol else t.line,
            }
            for t in index.traces().get(rid, [])
        ]

    # ---- Requirements and proposals in `walk` blocks ------------------------------------------

    def requirement(self, ref: Ref, req: Requirement) -> str:
        self.note_requirements([req.id])
        traces = self.requirements[req.id]["traces"]
        return templates.get_template("requirement.html").render(
            ref=ref, req=req, text=requirement_html(req.text), traces=traces, slug=_slug(req.id)
        )

    # r[impl proposal.change+2]
    def proposal(self, ref: Ref, end: int) -> str:
        """A `walk proposed` block: the draft, or once the name exists, what was written.

        Once it's written, the draft is shown against it.

        Parameters
        ----------
        ref : Ref
            The proposal.
        end : int
            The block's last line in the Markdown.

        Returns
        -------
        str
            The HTML.
        """
        files = self.ctx.index.files
        draft = _draft(ref)
        draft_rows = [Markup(h or " ") for h in highlight_text(draft, ref.lang)]
        rows, diff = None, None
        if s := ref.symbol:
            self.symbols[ref.target] = symbol_data(self.walk, s)
            highlighted = self.ctx.index.highlighted(s.file)
            raw = files.lines(s.file)[s.start - 1 : s.end]
            indent = min((len(l) - len(l.lstrip()) for l in raw if l.strip()), default=0)
            rows = [(n, Markup(_dedent_html(highlighted[n - 1], indent) or " ")) for n in range(s.start, s.end + 1)]
            current = "\n".join(l[indent:] for l in raw)
            # A change shows what there is, then what there will be; a written proposal what
            # was planned, then what was written
            diff = diff_rows(current, draft, context=3) if ref.change else diff_rows(draft, current, context=3)
        return templates.get_template("proposal.html").render(
            ref=ref,
            s=ref.symbol,
            parts=path_parts(ref.symbol.qualified if ref.symbol else ref.target),
            draft=draft_rows,
            rows=rows,
            diff=diff,
            end=end,
            ambiguous=ref.ambiguous,
            made=self.walk.made(ref),
            agreed=None if self.walk.made(ref) else self.walk.agreement(ref),
            candidates=[self.ctx.index.shortest_unique(c) for c in ref.candidates] if ref.ambiguous else [],
            zed=self.symbols[ref.target]["zed"] if ref.symbol else None,
            slug=_slug(ref.target),
        )

    def requirement_def(self, rid: str, para, inline, env) -> str:
        """Where a spec defines a requirement: its ID as an anchor, its text, and the code that names it.

        Parameters
        ----------
        rid : str
            The requirement's ID.
        para : Token
            Its paragraph_open token.
        inline : Token
            Its inline token, with the marker and the text.
        env : dict
            markdown-it's render environment.

        Returns
        -------
        str
            The HTML.
        """
        env["line"] = para.map[0] + 1 if para.map else env["line"]
        md = self.walk.md
        body = md.renderer.renderInline(inline.children or [], md.options, env)
        body = re.sub(r"^[a-z][a-z0-9]*\[[^\]]+\]\s*", "", body)
        self.note_requirements([rid])
        traces = self.requirements.get(rid, {}).get("traces", [])
        return templates.get_template("requirement_def.html").render(
            id=rid, slug=_slug(rid), line=env["line"], body=Markup(body), traces=traces
        )

    def note_definition(self, d: Definition) -> str:
        key = f"{d.kind[0]}:{d.id}"
        self.definitions[key] = {**d.model_dump(), "key": key, "slug": _slug(d.id), "href": self.definition_href(d)}
        return key

    def definition_href(self, d: Definition) -> str:
        view = "spec" if d.file in self.specs else "walk" if d.file in self.codewalks else "glossary"
        anchor = f"{d.kind[0]}-{_slug(d.id)}"
        return f"{base()}/glossary#{anchor}" if view == "glossary" else f"{base()}/{view}/{d.file}#{anchor}"

    def definition_def(self, kind: str, did: str, para, inline, env) -> str:
        """Where a term or fact is defined.

        Parameters
        ----------
        kind : str
            `t` or `f`.
        did : str
            Its ID.
        para : Token
            Its paragraph_open token.
        inline : Token
            Its inline token, with the marker and the text.
        env : dict
            markdown-it's render environment.

        Returns
        -------
        str
            The HTML.
        """
        env["line"] = para.map[0] + 1 if para.map else env["line"]
        d = self.ctx.glossary.get(f"{kind}:{did}")
        md = self.walk.md
        env["defining"] = did
        body = md.renderer.renderInline(inline.children or [], md.options, env)
        env["defining"] = None
        body = re.sub(r"^[a-z][a-z0-9]*\[(?:term|fact)\.[^\]]+\][^\n<]*\s*", "", body)
        if d:
            self.note_definition(d)
        change = self.prd.get(env["line"])
        return templates.get_template("definition_def.html").render(
            kind="term" if kind == "t" else "fact", id=did, d=d, slug=_slug(did), line=env["line"], body=Markup(body), change=change
        )

    # r[impl prd.compare]
    # r[impl prd.terms]
    def proposed_requirement(self, c: SpecChange, para, inline, env) -> str:
        """A requirement a PRD proposes, against the spec: new, changed, removed, quoted, or in error.

        Parameters
        ----------
        c : SpecChange
            How it stands against the spec.
        para : Token
            Its paragraph_open token.
        inline : Token
            Its inline token, with the marker and the text.
        env : dict
            markdown-it's render environment.

        Returns
        -------
        str
            The HTML.
        """
        env["line"] = para.map[0] + 1 if para.map else env["line"]
        md = self.walk.md
        body = md.renderer.renderInline(inline.children or [], md.options, env)
        body = re.sub(r"^[a-z][a-z0-9]*\[[^\]]+\][^\n<]*\s*", "", body)
        # r[impl ui.prd-requirement]
        # Open the PRD at it, and ask about it, as for an excerpt
        path = (self.ctx.root / self.walk.rel).resolve()
        return templates.get_template("prd_requirement.html").render(
            c=c,
            slug=_slug(c.id),
            line=env["line"],
            end=para.map[1] if para.map else env["line"],
            zed=f"zed://file/{path}:{env['line']}",
            body=Markup(body),
            words=word_diff(c.was or "", c.text),
        )

    # r[impl glossary.cite]
    def text(self, tokens, idx, options, env) -> str:
        """Plain text, with the first mention of each term in a paragraph linked to it."""
        content = html.escape(tokens[idx].content)
        pattern = self.ctx.glossary.mentions()
        if not pattern or env.get("in_heading") or env.get("in_link"):
            return content
        mark = NOTE_MARK.match(content)
        head, content = (content[: mark.end()], content[mark.end() :]) if mark else ("", content)
        seen = env.setdefault("seen_terms", set())

        def link(m):
            d = self.ctx.glossary.term_for(m.group(1))
            if d is None or d.id in seen or d.id == env.get("defining"):
                return m.group(0)
            seen.add(d.id)
            key = self.note_definition(d)
            return f'<a class="mention" href="{self.definition_href(d)}" data-term="{key}">{m.group(0)}</a>'

        return head + pattern.sub(link, content)

    # ---- Threads --------------------------------------------------------------------------

    def notes_html(self, open_idx: int, close_idx: int, env) -> list[dict]:
        """The notes in a blockquote as HTML, each with its replies, as `parse_notes` reads them."""
        tokens = self.walk.tokens
        out: list[dict] = []
        for a, b in blocks(tokens, open_idx, close_idx):
            if tokens[a].type == "blockquote_open" and out and parse_notes(tokens, a, b, 1):
                out[-1]["replies"] += self.notes_html(a, b, env)
                continue
            html_part = "".join(self.render_tokens(tokens[a : b + 1], env))
            m = NOTE_HEAD.match(html_part)
            if m and tokens[a].type == "paragraph_open":
                out.append(
                    {
                        "kind": m.group(2).lower(),
                        "author": m.group(3),
                        "html": m.group(1) + html_part[m.end() :],
                        "line": tokens[a].map[0] + 1 if tokens[a].map else 0,
                        "replies": [],
                    }
                )
            elif out:
                out[-1]["html"] += html_part

        def mark(ns):
            for n in ns:
                n["html"] = Markup(n["html"])
                mark(n["replies"])

        mark(out)
        return out

    # r[impl note.add-settled]
    def thread(self, open_idx: int, close_idx: int, thread, env) -> str:
        """A thread of notes, each note's Markdown rendered as the page renders it.

        Parameters
        ----------
        open_idx, close_idx : int
            The indices of its blockquote_open and blockquote_close tokens.
        thread : Thread
            The thread, parsed.
        env : dict
            markdown-it's render environment.

        Returns
        -------
        str
            The HTML.
        """
        notes = self.notes_html(open_idx, close_idx, env)
        return templates.get_template("thread.html").render(t=thread, notes=notes, prd=self.walk.meta.kind == "prd")

    # ---- Embedded symbols ----------------------------------------------------------------

    # r[impl embed.current]
    # r[impl ref.sig+2]
    # r[impl review.changed]
    def embed(self, ref: Ref) -> str:
        if ref.requirement:
            return self.requirement(ref, ref.requirement)
        if not ref.symbol:
            index = self.ctx.index
            if (gone := self.gone(ref)) is not None:
                return gone
            return templates.get_template("broken.html").render(
                ref=ref,
                ambiguous=ref.ambiguous,
                candidates=[(index.shortest_unique(c), f"{c.file}:{c.line}") for c in ref.candidates],
            )
        s = ref.symbol
        files = self.ctx.index.files
        self.symbols[ref.key] = symbol_data(self.walk, s)
        self.note_requirements(m[1] for m in s.markers)
        highlighted = self.ctx.index.highlighted(s.file)
        # `sig`: the runs of lines its outline gives, or its doc comments and first line
        runs = (s.outline or [(s.start, s.line)]) if ref.sig else [(s.start, s.end)]
        shown = [n for a, b in runs for n in range(a, b + 1)]
        raw = [files.lines(s.file)[n - 1] for n in shown]
        last = shown[-1]
        for line in raw:
            self.note_requirements([tracey.key(p, rid) for p, _, rid, _ in REQ_IN_CODE.findall(line)])
        # Shown without the indent it has inside its impl, class or module
        indent = min((len(l) - len(l.lstrip()) for l in raw if l.strip()), default=0)
        rows = self.code_rows(s, shown, indent, highlighted)
        more = last < s.end
        digest = s.digest(files)
        reviewed = self.ctx.review.get(self.walk.rel, ref.key)
        state = "new" if reviewed is None else ("changed" if reviewed.digest != digest else "ok")
        branch = self.branch_change(ref, s)
        return templates.get_template("figure.html").render(
            ref=ref,
            s=s,
            rows=rows,
            has_docs=any(r[2] == "doc" for r in rows),
            digest=digest,
            state=state,
            diff=diff_rows(reviewed.text, s.text(files)) if state == "changed" else None,
            plan=diff_rows(_draft(ref), "\n".join(l[indent:] for l in raw), context=3) if ref.settled else None,
            more=more,
            parts=path_parts(s.qualified),
            zed=self.symbols[ref.key]["zed"],
            slug=_slug(ref.key),
            branch=branch,
        )

    # r[impl review.branch-gone]
    def gone(self, ref: Ref) -> str | None:
        """A reference to a symbol the branch being read removed or renamed: what it was,
        shown removed, in place of a reference that names nothing.

        Parameters
        ----------
        ref : Ref
            A reference that names nothing on the branch.

        Returns
        -------
        str or None
            The HTML; None if no branch is being read, or the name isn't a symbol that was
            there where the branch started.
        """
        if not self.ctx.worktrees or ref.error or ref.ambiguous:
            return None
        was, _ = self.ctx.checked_out.resolve(ref.target)
        found = self.ctx.index.at_base(was) if was else None
        if not found or found[1] is None:
            return None
        base_ref, before = found
        return templates.get_template("gone.html").render(
            ref=ref,
            s=was,
            parts=path_parts(was.qualified),
            branch=self.ctx.worktrees.branch,
            base=base_ref,
            rows=[{"kind": "del", "tag": "-", "text": line} for line in textwrap.dedent(before).split("\n")],
        )

    # r[impl review.branch-diff]
    def branch_change(self, ref: Ref, s: Symbol) -> dict | None:
        """What the branch being read changed in an embedded symbol, if one is being read.

        Compared whole: an excerpt (`sig`, or a focus) is only labelled; the whole symbol,
        changed, is shown as a diff in place of its code.

        Parameters
        ----------
        ref : Ref
            The reference.
        s : Symbol
            The symbol, or the part of it the focus shows.

        Returns
        -------
        dict or None
            `state` (`new`, `changed` or `same`), `base` (the ref the branch started from)
            and, for a whole symbol that changed, `rows` for the diff template; None if no
            branch is being read or the symbol's file isn't in one of its worktrees.
        """
        index = self.ctx.index
        whole = s
        if ref.focus:
            whole = next((w for w in index.symbols if w.qualified == s.qualified and w.kind == s.kind), s)
        found = index.at_base(whole)
        if found is None:
            return None
        base_ref, before = found
        now = whole.text(index.files)
        state = "new" if before is None else ("same" if before == now else "changed")
        rows = None
        if state == "changed" and not (ref.sig or ref.focus):
            rows = diff_rows(textwrap.dedent(before), textwrap.dedent(now), context=10**6)
        return {"state": state, "base": base_ref, "branch": self.ctx.worktrees.branch, "rows": rows}

    # r[impl embed.docs]
    def code_rows(self, s: Symbol, shown: list[int], indent: int, highlighted: list[str]) -> list[tuple[int | None, Markup, str]]:
        """An excerpt's rows: its code a line at a time, and each run of its docs as one.

        Parameters
        ----------
        s : Symbol
            The symbol shown.
        shown : list of int
            The lines shown, in order, with gaps where its outline skips some.
        indent : int
            The spaces taken off every line.
        highlighted : list of str
            The file's lines, highlighted.

        Returns
        -------
        list of tuple of (int or None, Markup, str)
            Each row's line number (None for a gap), its HTML and its kind: `code`, `doc`
            for a run of docs as prose, `raw` for its lines as written (shown instead, on
            request), or `gap`.
        """
        lines = self.ctx.index.files.lines(s.file)
        suffix = os.path.splitext(s.file)[1]
        # Contiguous stretches of what's shown, so a run of docs never spans a gap
        stretches: list[list[int]] = []
        for n in shown:
            if stretches and n == stretches[-1][-1] + 1:
                stretches[-1].append(n)
            else:
                stretches.append([n])
        rows: list[tuple[int | None, Markup, str]] = []
        for k, stretch in enumerate(stretches):
            if k:
                rows.append((None, Markup("…"), "gap"))
            raw = [lines[n - 1] for n in stretch]
            runs = dict(doc_runs(raw, [highlighted[n - 1] for n in stretch], suffix))
            i = 0
            while i < len(stretch):
                j = runs.get(i)
                if j is None:
                    rows.append((stretch[i], Markup(_dedent_html(highlighted[stretch[i] - 1], indent) or " "), "code"))
                    i += 1
                    continue
                text = raw[i : j + 1]
                body = rust_doc_html(text, self.doc_linker(s)) if suffix == ".rs" else python_doc_html(text)
                pad = len(text[0]) - len(text[0].lstrip()) - indent
                kind = "rust" if suffix == ".rs" else "python"
                title = f"Lines {stretch[i]}–{stretch[j]}"
                prose = f'<div class="doc {kind}" style="--pad: {pad}ch" title="{title}">{body}</div>'
                rows.append((stretch[i], Markup(prose), "doc"))
                for n in stretch[i : j + 1]:
                    rows.append((n, Markup(_dedent_html(highlighted[n - 1], indent) or " "), "raw"))
                i = j + 1
        return rows

    def doc_linker(self, s: Symbol):
        """What links a name in `s`'s docs to its symbol, as rustdoc would: `Self` is the
        type the docs are on or in."""

        def link(name: str) -> str | None:
            target = name.removesuffix("()")
            if target == "Self" or target.startswith("Self::"):
                types = ("struct", "enum", "trait", "union", "type")
                owner = s.name if s.kind in types else (s.segments[-2] if len(s.segments) > 1 else "")
                target = owner + target[4:]
            sym, _ = self.ctx.index.resolve(target)
            if sym is None:
                return None
            self.symbols[target] = symbol_data(self.walk, sym)
            return f'<a class="sym" href="#" data-ref="{html.escape(target)}">'

        return link

    # ---- markdown-it rules -----------------------------------------------------------------

    def fence(self, tokens, idx, options, env) -> str:
        tok = tokens[idx]
        line = tok.map[0] + 1 if tok.map else 0
        end = tok.map[1] if tok.map else line
        if tok.info.split()[:2] == ["walk", "settled"]:
            ref = next((r for r in self.walk.refs if r.settled and line < r.line <= end), None)
            body = self.embed(ref) if ref else ""
            return f'<div class="walk-group" data-md="{line}" data-md-end="{end}">{body}</div>\n'
        if tok.info.split()[:2] == ["walk", "proposed"]:
            ref = next((r for r in self.walk.refs if r.kind == "proposal" and line < r.line <= end), None)
            body = self.proposal(ref, end) if ref else ""
            return f'<div class="walk-group" data-md="{line}" data-md-end="{end}">{body}</div>\n'
        if tok.info.strip() != "walk":
            lang = html.escape(tok.info.strip())
            return f'<pre class="plain" data-md="{line}"><code class="lang-{lang}">{html.escape(tok.content)}</code></pre>\n'
        parts = []
        rows: list[str] = []
        for i, text in enumerate(tok.content.split("\n")):
            if parsed := embed_line(text):
                target, focus, _ = parsed
                if ref := self.by_line.get((line + 1 + i, f"{target} > {focus}" if focus else target)):
                    # r[impl embed.definitions]
                    if ref.block:
                        rows.append(self.definition_row(ref))
                        continue
                    if rows:
                        parts.append(definitions_table(rows))
                        rows = []
                    parts.append(self.embed(ref))
        if rows:
            parts.append(definitions_table(rows))
        return f'<div class="walk-group" data-md="{line}" data-md-end="{end}">' + "\n".join(parts) + "</div>\n"

    # r[impl embed.definitions]
    def definition_row(self, ref: Ref) -> str:
        """A term or fact on a line of a `walk` block: a row of its words, or its ID and how
        it's known, linked to its definition, and its whole text."""
        d = ref.definition
        if not d:
            what = "term" if ref.target.startswith("t:") else "fact"
            name = f'<span class="broken" title="No such {what}">{html.escape(ref.target[2:])}</span>'
            return f'<tr data-md="{ref.line}"><th>{name}</th><td></td></tr>'
        key = self.note_definition(d)
        words = html.escape(d.words) if d.kind == "term" else f"<code>{html.escape(d.id)}</code>"
        name = f'<a class="term {d.kind}" href="{self.definition_href(d)}" data-term="{key}">{words}</a>'
        if d.status:
            name += f' <span class="status">{html.escape(d.status)}</span>'
        return f'<tr data-md="{ref.line}"><th>{name}</th><td>{requirement_html(d.text)}</td></tr>'

    # r[impl embed.inline]
    def inline_ref(self, target: str, label: str | None, line: int) -> str:
        proposed = target.startswith("?")
        target = target.lstrip("?")
        ref = self.by_line.get((line, target))
        if ref is None:
            return html.escape(label or target)
        if ref.kind == "term":
            d = ref.definition
            if not d:
                return f'<span class="broken" title="No such term or fact">{html.escape(label or target)}</span>'
            key = self.note_definition(d)
            text = label or (d.words if d.kind == "term" else d.id)
            return f'<a class="term {d.kind}" href="{self.definition_href(d)}" data-term="{key}">{html.escape(text)}</a>'
        if proposed and not ref.symbol:
            text = html.escape(label or target.split("::")[-1])
            return f'<span class="proposed-ref" title="Proposed: not written yet"><code>{text}</code></span>'
        if ref.kind == "req":
            if not ref.requirement:
                return f'<span class="broken" title="No such requirement">{html.escape(target)}</span>'
            self.note_requirements([ref.requirement.id])
            return f'<a class="req" href="#" data-req="{html.escape(ref.requirement.id)}">{html.escape(label or ref.requirement.id)}</a>'
        if not ref.symbol:
            cands = ", ".join(self.ctx.index.shortest_unique(c) for c in ref.candidates)
            title = "Names nothing" + (f": did you mean {cands}" if cands else "")
            return f'<span class="broken" title="{html.escape(title)}">{html.escape(label or target)}</span>'
        self.symbols[target] = symbol_data(self.walk, ref.symbol)
        return f'<a class="sym" href="#" data-ref="{html.escape(target)}"><code>{html.escape(label or ref.symbol.name)}</code></a>'

    def link_open(self, tokens, idx, options, env) -> str:
        tok = tokens[idx]
        href = str(tok.attrGet("href") or "")
        if not href.startswith(("walk:", "req:", "term:", "fact:")):
            env["in_link"] = True
        if href.startswith(("walk:", "req:", "term:", "fact:")):
            # Render the label ourselves, and swallow the link's own tokens
            label, j = "", idx + 1
            while tokens[j].type != "link_close":
                label += tokens[j].content
                tokens[j].hidden, tokens[j].type, tokens[j].content = True, "text", ""
                j += 1
            tokens[j].meta = {"walk": True}
            scheme, _, rest = href.partition(":")
            target = {"walk": rest, "req": "r:" + rest, "term": "t:" + rest, "fact": "f:" + rest}[scheme]
            return self.inline_ref(target, label, env["line"])
        if not re.match(r"^[a-z]+:", href) and (src := self.source_link(href)):
            # r[impl ui.context-link]
            # A link to a source file opens it beside the page, at its lines
            file, start, end = src
            tok.attrSet("class", "srclink")
            tok.attrSet("data-file", file)
            if start:
                tok.attrSet("data-start", str(start))
                tok.attrSet("data-end", str(end))
        elif href.split("#")[0].endswith(".md") and not re.match(r"^[a-z]+:", href):
            # A link to another codewalk opens it here
            target = os.path.normpath(os.path.join(os.path.dirname(self.walk.rel), href.split("#")[0]))
            if target in self.codewalks:
                tok.attrSet("href", f"{base()}/walk/{target}")
                tok.attrSet("class", "walklink")
            elif target in self.specs:
                tok.attrSet("href", f"{base()}/spec/{target}" + (f"#{href.split('#', 1)[1]}" if "#" in href else ""))
                tok.attrSet("class", "walklink")
        return self.walk.md.renderer.renderToken(tokens, idx, options, env)

    def source_link(self, href: str) -> tuple[str, int | None, int | None] | None:
        """The source file a relative link names, and the lines its `#L` anchor names.

        Parameters
        ----------
        href : str
            The link, as written, from the codewalk's folder.

        Returns
        -------
        tuple of (str, int or None, int or None) or None
            The file, from the root, with the first and last line, or None for each if
            there's no anchor; None if the index doesn't read the file.
        """
        path, _, anchor = href.partition("#")
        if not path:
            return None
        file = os.path.normpath(os.path.join(os.path.dirname(self.walk.rel), path))
        if not self.ctx.index.has_file(file):
            return None
        m = re.fullmatch(r"L(\d+)(?:-L?(\d+))?", anchor)
        if not m:
            return file, None, None
        start = int(m.group(1))
        return file, start, int(m.group(2) or start)

    def link_close(self, tokens, idx, options, env) -> str:
        env["in_link"] = False
        if tokens[idx].meta and tokens[idx].meta.get("walk"):
            return ""
        return self.walk.md.renderer.renderToken(tokens, idx, options, env)

    def code_inline(self, tokens, idx, options, env) -> str:
        """A requirement's ID in backticks is a citation of it: the convention in prose."""
        content = tokens[idx].content
        if "." in content and (r := self.ctx.spec.find(content, self.walk.rel)):
            self.note_requirements([r.id])
            return f'<a class="req cite" href="#" data-req="{html.escape(r.id)}"><code>{html.escape(content)}</code></a>'
        return f"<code>{html.escape(content)}</code>"

    # ---- The whole page ----------------------------------------------------------------------

    def render_tokens(self, tokens, env: dict, split_paragraphs: bool = False) -> list[str]:
        """Block tokens as HTML, each tagged with its line.

        Parameters
        ----------
        tokens : list of Token
            The block tokens.
        env : dict
            markdown-it's render environment.
        split_paragraphs : bool
            Split the HTML at each top-level paragraph.

        Returns
        -------
        list of str
            With `split_paragraphs`, one item from each top-level paragraph on; else one item.
        """
        md = self.walk.md
        parts: list[str] = [""]
        depth = 0
        skip_close = False
        for k, tok in enumerate(tokens):
            if skip_close and tok.type == "paragraph_close":
                skip_close = False
                continue
            if (
                self.spec_mode
                and tok.type == "paragraph_open"
                and k + 1 < len(tokens)
                and (m := re.match(rf"^([a-z][a-z0-9]*)\[({tracey.ID}){tracey.VERSION}\]", tokens[k + 1].content))
                and m.group(1) in self.ctx.spec.prefixes
                # A term or a fact is written as a requirement, and rendered as a definition below
                and not m.group(2).startswith(terms.KINDS)
            ):
                # A requirement: rendered by `requirement_def` from its inline token
                parts[-1] += self.requirement_def(tracey.key(m.group(1), m.group(2)), tok, tokens[k + 1], env)
                tokens[k + 1].type = "_done"
                skip_close = True
                continue
            if tok.type == "paragraph_open" and k + 1 < len(tokens) and COMMENT.match(tokens[k + 1].content):
                # A comment, as the PRD template's guidance is: for whoever edits it, not shown
                tokens[k + 1].type = "_done"
                skip_close = True
                continue
            if (
                self.prd
                and tok.type == "paragraph_open"
                and tok.map
                and (c := self.prd.get(tok.map[0] + 1))
                and c.kind == "requirement"
                and k + 1 < len(tokens)
            ):
                # A requirement a PRD proposes: shown against the spec
                parts[-1] += self.proposed_requirement(c, tok, tokens[k + 1], env)
                tokens[k + 1].type = "_done"
                skip_close = True
                continue
            if tok.type == "_done":
                continue
            if tok.type == "paragraph_open" and k + 1 < len(tokens) and (m := DEF_LINE.match(tokens[k + 1].content.split("\n")[0])):
                # A term or a fact: rendered by `definition_def`
                parts[-1] += self.definition_def(m["kind"][0], m["id"], tok, tokens[k + 1], env)
                tokens[k + 1].type = "_done"
                skip_close = True
                continue
            if tok.type == "paragraph_open" or tok.type == "heading_open":
                env["seen_terms"] = set()
            env["in_heading"] = tok.type == "heading_open" or (env.get("in_heading") and tok.type != "heading_close")
            if tok.map:
                env["line"] = tok.map[0] + 1
                if tok.nesting == 1 or tok.type in ("hr", "code_block"):
                    tok.attrSet("data-md", str(tok.map[0] + 1))
            if split_paragraphs and tok.type == "paragraph_open" and depth == 0:
                parts.append("")
            if tok.nesting == 1:
                depth += 1
            elif tok.nesting == -1:
                depth -= 1
            if tok.type == "inline":
                parts[-1] += md.renderer.renderInline(tok.children or [], md.options, env)
            elif tok.type == "fence":
                parts[-1] += self.fence([tok], 0, md.options, env)
            else:
                # With the whole list, so markdown-it knows what follows (and where newlines go)
                rule = md.renderer.rules.get(tok.type)
                parts[-1] += rule(tokens, k, md.options, env) if rule else md.renderer.renderToken(tokens, k, md.options, env)
        return [p for p in parts if p] if split_paragraphs else ["".join(parts)]

    def render(self) -> tuple[str, dict]:
        md = self.walk.md
        rules = md.renderer.rules
        rules["fence"] = self.fence
        rules["walk_ref"] = lambda tokens, idx, options, env: self.inline_ref(
            tokens[idx].meta["target"], tokens[idx].meta["label"], env["line"]
        )
        rules["link_open"] = self.link_open
        rules["link_close"] = self.link_close
        rules["front_matter"] = lambda *a: ""
        rules["code_inline"] = self.code_inline
        rules["text"] = self.text

        tokens = self.walk.tokens
        found = {start: (close, t) for start, close, t in threads(tokens)}
        out = []
        env: dict = {"line": 0}
        i = 0
        while i < len(tokens):
            if i in found:
                close, thread = found[i]
                out.append(self.thread(i, close, thread, env))
                i = close + 1
                continue
            j = i
            while j < len(tokens) and j not in found:
                j += 1
            out.extend(self.render_tokens(tokens[i:j], env))
            i = j
        return "".join(out), {"symbols": self.symbols, "requirements": self.requirements, "terms": self.definitions}


def render(walk: Walk, spec_mode: bool = False) -> tuple[str, dict]:
    """The codewalk as HTML, and the data its page needs.

    The data is each symbol and requirement it refers to, for hover cards and the context
    panel.

    Parameters
    ----------
    walk : Walk
        The codewalk, parsed.
    spec_mode : bool
        It's a spec file: `r[id]` paragraphs are requirements, shown as such.

    Returns
    -------
    html : str
        The document.
    data : dict
        `symbols`, `requirements` and `terms`, by the key the page looks them up by.
    """
    return Renderer(walk, spec_mode).render()


def page_data_json(data: dict) -> str:
    return json.dumps(data).replace("</", "<\\/")
