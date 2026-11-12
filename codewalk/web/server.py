"""The web view: codewalks in the browser, with their code, an editor and live reload.

Each codewalk is rendered with its code, the code in its file beside it, a browser
editor with symbol completion, and live reload as the Markdown or the code changes.

Local only: it listens on 127.0.0.1, and writes only codewalks and the review file.

Pages and the API are plain functions on `App`, called from Starlette's routes, so they
can be tested without a server. The index and the codewalks are shared state, so every
call that reads them holds `App.lock`; Starlette runs each in a worker thread.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
import watchfiles
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from codewalk.code import worktrees
from codewalk.code.highlight import highlight_lines
from codewalk.code.index import CodeIndex
from codewalk.spec import prose, trail
from codewalk.walk import notes, prd
from codewalk.walk.doc import STAGES, Context, Walk, set_front_matter, settle, unsettle
from codewalk.walk.library import Library
from codewalk.web.render import BASE, _slug, base, diff_rows, page_data_json, render, requirement_html, templates

if TYPE_CHECKING:
    from codewalk.web.workspace import Workspace

log = logging.getLogger(__name__)

STATES = {
    "never": ("not reconciled", "No one has said this and its prose agree yet"),
    "ok": ("agrees", "Unchanged since it and its prose were reconciled"),
    "prose": ("prose changed", "The prose citing it changed since they were reconciled: does the requirement still follow?"),
    "spec": ("spec changed", "The requirement changed since they were reconciled: does the prose still say so?"),
    "both": ("both changed", "Both changed since they were reconciled"),
    "missing": ("not in the spec yet", "Cited in the prose, but no requirement has this ID yet"),
}

STATIC = Path(__file__).parent / "static"


def static_url(name: str) -> str:
    """A static file's address, with a digest of what's in it.

    A browser keeps a script or stylesheet it's fetched, and may use it again without
    asking whether it's changed; with the digest in the address, a changed file is a new
    address, so a page never runs with the script it had before codewalk was updated.

    Parameters
    ----------
    name : str
        The file, in the static folder.

    Returns
    -------
    str
        Its address, as `/static/name?v=digest`.
    """
    digest = hashlib.sha256((STATIC / name).read_bytes()).hexdigest()[:10]
    return f"/static/{name}?v={digest}"


class Change(BaseModel):
    """What changed, as told to each open page."""

    # The code or the spec changed
    code: bool = False
    # Codewalks whose Markdown changed, as paths from the root
    docs: list[str] = []
    review: bool = False


class App:
    """What the server serves: its pages, and the changes made from them.

    Parameters
    ----------
    ctx : Context
        The project.
    base : str
        The path its pages are under: empty for a server of one project, `/p/<name>` for
        one of a workspace's.
    workspace : Workspace or None
        The workspace it's one of, if any.
    """

    def __init__(self, ctx: Context, base: str = "", workspace: Workspace | None = None):
        self.ctx = ctx
        self.base = base
        self.workspace = workspace
        self.lock = threading.Lock()
        self.subscribers: set[asyncio.Queue[Change]] = set()
        # Set when the server's asked to stop, so the pages' event streams end: the server
        # waits for every connection to close before it stops, and they'd never close
        self.closing = False

    # ---- Pages ----------------------------------------------------------------------

    # r[impl ui.project]
    def page(self, template: str, title: str, view: str, data: dict, **context) -> str:
        projects = self.workspace.names() if self.workspace else []
        return templates.get_template(template).render(
            title=title,
            view=view,
            data_json=page_data_json({"view": view, "base": base(), **data}),
            static=static_url,
            projects=projects,
            project=self.base.removeprefix("/p/"),
            branch=self.ctx.worktrees.branch if self.ctx.worktrees else None,
            **context,
        )

    def index_page(self) -> str:
        library = Library.of(self.ctx)
        return self.page(
            "index.html",
            "Codewalks",
            "index",
            {},
            library=library,
            titles=library.titles(),
            symbols=len(self.ctx.index.symbols),
            requirements=len(self.ctx.spec.requirements),
        )

    ROLES = {
        "proposes": "proposed here",
        "proposes a test of": "test proposed here",
        "implements": "implemented here",
        "verifies": "verified here",
        "cites": "cited here",
    }

    # r[impl spec.trail]
    def walk_body(self, rel: str, text: str | None = None) -> tuple[str, dict, Walk]:
        """A codewalk, with the requirements each block has in its margin.

        Beside each block, the margin shows the requirements it proposes, implements,
        verifies or cites, each with the prose it came from.

        Parameters
        ----------
        rel : str
            The codewalk, from the root.
        text : str or None
            Its Markdown, if not as saved (while it's being edited).

        Returns
        -------
        html : str
            The document, with its margin if it has one.
        data : dict
            The page's data; `margin` is set if there's a margin.
        walk : Walk
            The codewalk, parsed.
        """
        w = Walk(self.ctx, rel, text)
        body, data = render(w)
        if w.ctx.pin:
            data["at"] = w.ctx.pin.ref
        views: dict[str, prose.SpecView] = {}
        groups: dict[int, list[dict]] = {}
        for link in trail.links(w):
            req = self.ctx.spec.requirements.get(link.id)
            card = {"id": link.id, "state": "role", "state_label": self.ROLES[link.role], "state_title": "", "diff": None}
            if req:
                # The whole card goes to the spec, at the prose it comes from if there is some
                o = trail.origin(self.ctx, link.id, views)
                at = o if o and o.prose else req
                card["href"] = card["go"] = f"{base()}/spec/{at.file}?line={at.line}&req={link.id}"
                card["text"] = requirement_html(req.text)
            else:
                card.update({"href": "#", "text": None, "state": "missing", "state_label": "not in the spec yet"})
            groups.setdefault(link.line, []).append(card)
        if not groups:
            return body, data, w
        html = templates.get_template("spec_body.html").render(body=body, groups=sorted(groups.items()))
        data["margin"] = True
        return html, data, w

    # r[impl pin.label]
    def walk_page(self, rel: str) -> str:
        body, data, w = self.walk_body(rel)
        problems = w.problems()
        library = Library.of(self.ctx)
        data.update({"doc": rel, "problems": [p.model_dump() for p in problems]})
        return self.page(
            "walk.html",
            w.title,
            "walk",
            data,
            rel=rel,
            body=body,
            margin=data.get("margin", False),
            headings=w.headings(),
            summary=library.get(rel),
            titles=library.titles(),
            stages=STAGES,
            pin=w.ctx.pin,
            errors=sum(1 for p in problems if p.severity == "error"),
            changed=sum(1 for p in problems if p.severity == "warning"),
        )

    def is_spec(self, rel: str) -> bool:
        return rel in self.ctx.spec_paths()

    # r[impl spec.view]
    def spec_body(self, rel: str, text: str | None = None) -> tuple[str, dict, prose.SpecView, Walk]:
        """A spec file's document and margin, as HTML, with its page data.

        Parameters
        ----------
        rel : str
            The spec file, from the root.
        text : str or None
            Its Markdown, if not as saved (while it's being edited).

        Returns
        -------
        html : str
            The document and its margin.
        data : dict
            The page's data.
        view : prose.SpecView
            Its requirements against its prose.
        walk : Walk
            The file, parsed.
        """
        w = Walk(self.ctx, rel, text)
        body, data = render(w, spec_mode=True)
        v = prose.view(self.ctx, rel, text)
        used = trail.uses(self.ctx)
        groups: dict[int, list[dict]] = {}
        for c in sorted(v.citations, key=lambda c: c.lines[0]):
            req = c.requirement
            label, title = STATES[c.state]
            card = {"id": c.id, "state": c.state, "state_label": label, "state_title": title, "diff": None}
            if req:
                card["href"] = f"#r-{_slug(c.id)}" if req.file == rel else f"/spec/{req.file}#r-{_slug(c.id)}"
                card["text"] = requirement_html(req.text)
                key = prose.review_key(rel)
                if c.state in ("prose", "both") and (was := self.ctx.review.get(key, f"{c.id}#prose")):
                    card["diff"], card["diff_label"] = diff_rows(was.text, c.prose), "What changed in the prose"
                elif c.state == "spec" and (was := self.ctx.review.get(key, f"{c.id}#spec")):
                    card["diff"], card["diff_label"] = diff_rows(was.text, req.text), "What changed in the requirement"
            else:
                card["href"], card["text"] = "#", None
            card["uses"] = [
                {"href": f"{base()}/walk/{u.codewalk}?line={u.line}", "title": u.title, "role": self.ROLES[u.role]}
                for u in used.get(c.id, [])
            ]
            groups.setdefault(c.lines[0], []).append(card)
        html = templates.get_template("spec_body.html").render(body=body, groups=sorted(groups.items()))
        return html, data, v, w

    def spec_page(self, rel: str) -> str:
        html, data, v, w = self.spec_body(rel)
        data.update({"doc": rel, "spec": True, "problems": []})
        return self.page(
            "spec.html", w.title, "spec", data, rel=rel, body=html, v=v, headings=w.headings(), slugs={r.id: _slug(r.id) for r in v.defined}
        )

    def reconcile(self, rel: str, rid: str | None) -> dict:
        self.writable(rel)
        return {"reconciled": prose.reconcile(self.ctx, rel, rid)}

    # r[impl ui.edit-margin]
    def edit_page(self, rel: str) -> str:
        self.writable(rel)
        if self.is_spec(rel):
            body, data, _, w = self.spec_body(rel)
            data.update({"doc": rel, "spec": True, "problems": [], "margin": True})
            return self.page("edit.html", f"Editing {w.title}", "edit", data, rel=rel, body=body, text=w.text, spec=True)
        body, data, w = self.walk_body(rel)
        data.update({"doc": rel, "problems": [p.model_dump() for p in w.problems()]})
        return self.page("edit.html", f"Editing {w.title}", "edit", data, rel=rel, body=body, text=w.text, spec=data.get("margin", False))

    # ---- API ------------------------------------------------------------------------

    # r[impl serve.files]
    def pinned(self, at: str | None) -> Context:
        """The project, or it read at a pinned codewalk's ref."""
        if not at:
            return self.ctx
        if (ctx := self.ctx.at(at)) is None:
            raise FileNotFoundError(f"`{at}` names no commit")
        return ctx

    # r[impl pin.everywhere]
    def file_view(self, rel: str, at: str | None = None) -> dict:
        # A source can be outside the root (`../other/src/**/*.rs`), or read from a branch's
        # worktree or from git at a pin, so one the index read is shown wherever it's read from
        index = self.pinned(at).index
        indexed = index.has_file(rel)
        if indexed and index.on_disk(rel) is None:
            return self._file_view(index, rel, index.highlighted(rel), None)
        path = (index.where(rel) if indexed else self.ctx.root / rel).resolve()
        if not path.is_file() or (self.ctx.root not in path.parents and not indexed):
            raise FileNotFoundError(rel)
        return self._file_view(index, rel, highlight_lines(path), f"zed://file/{path}")

    def _file_view(self, index: CodeIndex, rel: str, lines: list[str], zed: str | None) -> dict:
        outline = [
            {
                "ref": index.shortest_unique(s),
                "qualified": s.qualified,
                "kind": s.kind,
                "line": s.line,
                "start": s.start,
                "end": s.end,
                "depth": s.qualified.count("::"),
            }
            for s in sorted(index.in_file(rel), key=lambda s: s.line)
            if s.kind not in ("field", "impl")
        ]
        return {"file": rel, "lines": lines, "outline": outline, "zed": zed}

    # r[impl glossary.page]
    def glossary_page(self) -> str:
        g = self.ctx.glossary
        # Where each is cited or mentioned, across the codewalks and specs
        uses: dict[str, list[str]] = {}
        pattern = g.mentions()
        for rel in sorted(set(self.ctx.codewalks()) | set(self.ctx.spec_paths())):
            text = (self.ctx.root / rel).read_text()
            for key in {f"t:{m}" for m in re.findall(r"(?:\[\[t:|\(term:)([a-z0-9.\-]+)", text)} | {
                f"f:{m}" for m in re.findall(r"(?:\[\[f:|\(fact:)([a-z0-9.\-]+)", text)
            }:
                uses.setdefault(key, []).append(rel)
            if pattern:
                mentioned = {d.id for x in pattern.finditer(text) if (d := g.term_for(x.group(1)))}
                for tid in sorted(mentioned):
                    if rel not in uses.setdefault(f"t:{tid}", []):
                        uses[f"t:{tid}"].append(rel)

        specs = set(self.ctx.spec_paths())

        def view(rel: str) -> str:
            return "spec" if rel in specs else "walk"

        groups = []
        for rel in {d.file for d in [*g.terms.values(), *g.facts.values()]}:
            w = Walk(self.ctx, rel)
            terms = sorted((d for d in g.terms.values() if d.file == rel), key=lambda d: d.id)
            facts = sorted(
                (d for d in g.facts.values() if d.file == rel),
                key=lambda d: (("documented", "observed", "assumed").index(d.status or "assumed"), d.id),
            )
            # Specs first, as the index lists them: by folder, then lighter first; then the rest
            order = (rel not in specs, rel.split("/")[:-1], w.meta.weight is None, w.meta.weight or 0, w.title.lower())
            groups.append((order, {"rel": rel, "title": w.title, "view": view(rel), "terms": terms, "facts": facts}))
        return self.page(
            "glossary.html",
            "Glossary",
            "glossary",
            {},
            groups=[grp for _, grp in sorted(groups, key=lambda x: x[0])],
            counts=(len(g.terms), len(g.facts)),
            uses=uses,
            view_of=view,
            slug=_slug,
            text=requirement_html,
        )

    def symbols(self, q: str) -> list[dict]:
        if q.startswith(("t:", "f:", "r:")):
            return self.definitions(q)
        return [
            {
                "ref": self.ctx.index.shortest_unique(s),
                **s.model_dump(include={"qualified", "kind", "file", "line", "start", "end", "signature", "doc"}),
            }
            for s in self.ctx.index.search(q)
        ]

    def definitions(self, q: str) -> list[dict]:
        """Terms, facts or requirements whose ID starts with or contains what follows the prefix.

        For completing `[[t:`, `[[f:` and `[[r:`.

        Parameters
        ----------
        q : str
            `t:`, `f:` or `r:`, then what's been typed.

        Returns
        -------
        list of dict
            Up to 30, those starting with it first, shaped like `symbols`' results.
        """
        kind, _, want = q.partition(":")
        if kind == "r":
            pool = [(r.id, "req", r.file, r.line, r.text) for r in self.ctx.spec.requirements.values()]
        else:
            table = self.ctx.glossary.terms if kind == "t" else self.ctx.glossary.facts
            pool = [(d.id, d.kind, d.file, d.line, d.text) for d in table.values()]
        hits = sorted((p for p in pool if want.lower() in p[0]), key=lambda p: (not p[0].startswith(want.lower()), p[0]))
        return [
            {"ref": f"{kind}:{i}", "qualified": i, "kind": k, "file": f, "line": n, "start": n, "end": n, "signature": i, "doc": t}
            for i, k, f, n, t in hits[:30]
        ]

    def render(self, rel: str, text: str) -> dict:
        if self.is_spec(rel):
            body, data, _, w = self.spec_body(rel, text)
            return {"html": body, "data": data, "problems": [], "headings": w.headings(), "title": w.title}
        body, data, w = self.walk_body(rel, text)
        return {"html": body, "data": data, "problems": [p.model_dump() for p in w.problems()], "headings": w.headings(), "title": w.title}

    # r[impl serve.local+2]
    def writable(self, rel: str) -> Path:
        """`rel`, if it's a Markdown file under the docs folders: nothing else is written.

        Parameters
        ----------
        rel : str
            The file, from the root.

        Returns
        -------
        Path
            Its full path.

        Raises
        ------
        PermissionError
            If it isn't one that can be written.
        """
        path = (self.ctx.root / rel).resolve()
        if path.suffix != ".md" or rel not in self.ctx.editable():
            raise PermissionError(rel)
        return path

    def save(self, rel: str, text: str) -> dict:
        path = self.writable(rel)
        path.write_text(text)
        return {"saved": True}

    # r[impl note.write]
    def note(
        self,
        rel: str,
        kind: str,
        body: str,
        after: int | None = None,
        thread: int | None = None,
        to: int | None = None,
        about: int | None = None,
    ) -> dict:
        """Write a note into a codewalk.

        A new question after line `after`, or a note added to the thread that starts on line
        `thread`.

        Parameters
        ----------
        rel : str
            The codewalk, from the root.
        kind : str
            The note's kind; a new thread is always a question.
        body : str
            The note's Markdown.
        after : int or None
            For a new question, the line to put it after.
        thread : int or None
            For a reply, the line its thread starts on.
        to : int or None
            For a reply to one note, the line it starts on.
        about : int or None
            For a new question about one reference in a `walk` block, its line.

        Returns
        -------
        dict
            `written`, and the `author` it was written as.

        Raises
        ------
        PermissionError
            If `rel` isn't a file that can be written.
        FileNotFoundError
            If no thread starts on line `thread`.
        """
        path = self.writable(rel)
        text = path.read_text()
        author = self.ctx.config.who(self.ctx.root)
        if to is not None:
            found = next((n for t in Walk(self.ctx, rel, text).threads if (n := t.find(to))), None)
            if found is None:
                raise FileNotFoundError(f"no note on line {to}")
            text = notes.reply_to(text, found, kind, author, body)
        elif thread is not None:
            found = next((t for t in Walk(self.ctx, rel, text).threads if t.line == thread), None)
            if found is None:
                raise FileNotFoundError(f"no thread on line {thread}")
            text = notes.reply(text, found, kind, author, body)
        elif about is not None:
            text = notes.ask_about(text, about, author, body)
        else:
            text = notes.ask(text, after or 0, author, body)
        path.write_text(text)
        return {"written": True, "author": author}

    def resolve(self, rel: str, thread: int, mode: str) -> dict:
        """Take a settled thread out of a codewalk: into its changelog, or away."""
        import datetime

        path = self.writable(rel)
        w = Walk(self.ctx, rel)
        found = next((t for t in w.threads if t.line == thread), None)
        if found is None:
            raise FileNotFoundError(f"no thread on line {thread}")
        about = [
            r.key
            for r in w.refs
            if r.kind in ("embed", "proposal") and found.about_line is not None and found.about_line <= r.line < found.line
        ]
        path.write_text(notes.resolve(w.text, found, mode, datetime.date.today().isoformat(), about))
        return {"resolved": mode}

    def settle(self, rel: str, line: int) -> dict:
        path = self.writable(rel)
        w = Walk(self.ctx, rel)
        ref = next((r for r in w.refs if r.kind == "proposal" and r.line == line and w.made(r)), None)
        if ref is None:
            raise FileNotFoundError(f"no written proposal on line {line}")
        path.write_text(settle(w.text, line, ref.target))
        return {"settled": ref.target}

    # r[impl proposal.unsettle]
    def unsettle(self, rel: str, line: int) -> dict:
        path = self.writable(rel)
        w = Walk(self.ctx, rel)
        ref = next((r for r in w.refs if r.settled and r.line == line), None)
        if ref is None:
            raise FileNotFoundError(f"no settled block on line {line}")
        path.write_text(unsettle(w.text, line))
        return {"unsettled": ref.target}

    # r[impl proposal.agree]
    def agree(self, rel: str, line: int, end: int, body: str) -> dict:
        """Agree the proposal on line `line`: a decision in the thread after its block, or a new one.

        Parameters
        ----------
        rel : str
            The codewalk, from the root.
        line : int
            The proposal's line: its name's, as the reference has it.
        end : int
            The block's last line, which a new thread goes after.
        body : str
            The decision, in the person's words.

        Returns
        -------
        dict
            `agreed`, the proposal's name, and the `author` it was written as.
        """
        path = self.writable(rel)
        w = Walk(self.ctx, rel)
        ref = next((r for r in w.refs if r.kind == "proposal" and r.line == line), None)
        if ref is None:
            raise FileNotFoundError(f"no proposal on line {line}")
        author = self.ctx.config.who(self.ctx.root)
        t = w.thread_after(ref)
        text = notes.reply(w.text, t, "decision", author, body) if t else notes.ask(w.text, end, author, body, kind="decision")
        path.write_text(text)
        return {"agreed": ref.target, "author": author}

    # r[impl prd.stage-set]
    def set_stage(self, rel: str, stage: str) -> dict:
        """Set a PRD's stage in its front matter, from its page."""
        if stage not in STAGES:
            raise ValueError(f"not a stage: {stage}")
        path = self.writable(rel)
        if Walk(self.ctx, rel).meta.kind != "prd":
            raise ValueError(f"{rel} isn't a PRD")
        path.write_text(set_front_matter(path.read_text(), "stage", stage))
        return {"stage": stage}

    # r[impl prd.start+2]
    # r[impl prd.from-thread]
    # r[impl serve.local+2]
    def start_prd(self, title: str, ask: str, source: str | None = None, thread: int | None = None) -> dict:
        """Start a PRD from the index, or from a thread in a codewalk, and say where to open it.

        From a thread, the PRD's request says which codewalk it came from, and a note added
        to the thread says where the PRD is.

        Parameters
        ----------
        title : str
            The PRD's title.
        ask : str
            What the person wants, in their own words.
        source : str or None
            The codewalk the thread is in, from the root, if it's started from one.
        thread : int or None
            The line the thread starts on.

        Returns
        -------
        dict
            `started`, the PRD's path, and `href`, where to open it.

        Raises
        ------
        ValueError
            If there's a PRD by that name already, or the thread isn't there.
        """
        origin = None
        if source and thread:
            w = Walk(self.ctx, source)
            found = next((t for t in w.threads if t.line == thread), None)
            if found is None:
                raise ValueError(f"no thread on line {thread} of {source}")
            origin = (self.writable(source), found)
            ask = f"{ask.rstrip()}\n\nFrom [{w.title}]({os.path.relpath(source, prd.FOLDER)})."
        try:
            rel = prd.start(self.ctx, title, ask)
        except FileExistsError as e:
            raise ValueError(f"there's a PRD at {e} already") from e
        if origin:
            path, found = origin
            note = f"Taken up in a PRD: [{title}]({os.path.relpath(rel, os.path.dirname(source))})."
            path.write_text(notes.reply(path.read_text(), found, "note", self.ctx.config.who(self.ctx.root), note))
        return {"started": rel, "href": f"{base()}/walk/{rel}"}

    # r[impl review.people]
    def review(self, rel: str, ref: str | None) -> dict:
        w = Walk(self.ctx, rel)
        # A pinned codewalk's code is as it was at its pin
        files = w.ctx.index.files
        done = []
        for r in w.embeds:
            if r.symbol and (ref is None or r.key == ref):
                self.ctx.review.mark(rel, r.key, r.symbol.digest(files), r.symbol.text(files))
                done.append(r.key)
        if ref is None:
            self.ctx.review.forget_missing(rel, {r.key for r in w.embeds})
        return {"reviewed": done}

    # r[impl review.reopen]
    def reopen(self, rel: str, ref: str) -> dict:
        """Forget the review of one reference in a codewalk, so it reads as not reviewed."""
        if not self.ctx.review.forget(rel, ref):
            raise KeyError(f"{ref} isn't reviewed in {rel}")
        return {"reopened": ref}

    # ---- Watching -----------------------------------------------------------------------

    def watched(self) -> list[Path]:
        """The folders the globs look in: each glob up to its first wildcard.

        Returns
        -------
        list of Path
            The folders, any inside another left out.
        """
        dirs = set()
        for g in [*self.ctx.config.sources, *self.ctx.spec.globs, *self.ctx.config.docs]:
            fixed = []
            for part in Path(g).parts:
                if any(c in part for c in "*?["):
                    break
                fixed.append(part)
            path = self.ctx.root.joinpath(*fixed)
            # A source read from a branch's worktree is watched there
            if g in self.ctx.config.sources and self.ctx.worktrees and (at := self.ctx.worktrees.where(str(Path(*fixed)) + "/")):
                path = at
            path = path.resolve()
            dirs.add(path if path.is_dir() else path.parent)
        # Drop any folder inside another
        return sorted(d for d in dirs if not any(o != d and o in d.parents for o in dirs))

    # r[impl serve.live]
    def changed(self, paths: set[str]) -> Change | None:
        """What a batch of changed files means for the pages.

        Parameters
        ----------
        paths : set of str
            The files that changed, as full paths.

        Returns
        -------
        Change or None
            None if nothing a page shows has changed.
        """
        with self.lock:
            code = self.ctx.refresh()
            docs = set(self.ctx.doc_paths())
        rels = {str(Path(p).relative_to(self.ctx.root)) for p in paths if Path(p).is_relative_to(self.ctx.root)}
        change = Change(code=code, docs=sorted(rels & docs), review=self.ctx.review.path.name in rels)
        return change if change.code or change.docs or change.review else None

    # r[impl serve.live.settle]
    async def catch_up(self, paths: set[str], tries: int = 5, wait: float = 0.25) -> Change | None:
        """What a batch of changed files means for the pages, read again a moment later
        while it can't be read.

        A change caught half-made, as git makes them in a rebase, can't always be read: a
        file goes between being found and being read, or the review file is half-written.
        It's read again, a little later each time, and given up only for this batch, so the
        watching carries on.

        Parameters
        ----------
        paths : set of str
            The files that changed, as full paths.
        tries : int
            How many times to read it.
        wait : float
            Seconds before the second try; each try after waits that much longer.

        Returns
        -------
        Change or None
            None if nothing a page shows has changed, or it still couldn't be read.
        """
        for attempt in range(1, tries + 1):
            try:
                return await asyncio.to_thread(self.changed, paths)
            except Exception as e:
                if attempt == tries:
                    log.warning("couldn't read a change after %d tries: %s", tries, e)
                    return None
                await asyncio.sleep(wait * attempt)
        return None

    async def watch(self, stop: asyncio.Event) -> None:
        review = self.ctx.review.path.name
        self.loop = asyncio.get_running_loop()

        async def follow(paths, recursive: bool, keep, until: asyncio.Event):
            async for batch in watchfiles.awatch(*paths, recursive=recursive, debounce=120, step=40, stop_event=until, watch_filter=keep):
                change = await self.catch_up({p for _, p in batch})
                if change:
                    for q in list(self.subscribers):
                        q.put_nowait(change)

        # Watched afresh whenever the folders change: when a branch's worktrees are read, or
        # no longer read
        while not stop.is_set():
            self.rewatch = asyncio.Event()
            until = asyncio.Event()
            waits = [asyncio.create_task(stop.wait()), asyncio.create_task(self.rewatch.wait())]

            async def relay(waits: list[asyncio.Task], until: asyncio.Event) -> None:
                await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
                until.set()

            relay_task = asyncio.create_task(relay(waits, until))
            await asyncio.gather(
                follow(self.watched(), True, lambda _, p: p.endswith((".rs", ".py", ".md")), until),
                # The review file is at the root, which is too big to watch whole
                follow([self.ctx.root], False, lambda _, p: Path(p).name == review, until),
            )
            for t in [*waits, relay_task]:
                t.cancel()

    # ---- Reading a branch's worktrees ---------------------------------------------------

    # r[impl review.branches]
    def branches(self) -> dict:
        """The branches with a worktree in any of the project's repositories, and the one
        being read, if any."""
        found = worktrees.branches(self.ctx.root, self.ctx.config.sources)
        current = self.ctx.worktrees.branch if self.ctx.worktrees else None
        return {
            "current": current,
            "branches": [
                {
                    "name": name,
                    "repos": [c.repo.name for c in w.checkouts],
                    "base": sorted({c.base_ref for c in w.checkouts}),
                }
                for name, w in found.items()
            ],
        }

    # r[impl review.branch-code]
    def read_branch(self, branch: str | None) -> dict:
        """Read the project's code from a branch's worktrees, or, with None, as it is.

        Nothing is written: the choice is the server's, for every page of the project.

        Parameters
        ----------
        branch : str or None
            The branch.

        Returns
        -------
        dict
            The branch now being read.
        """
        found = worktrees.branches(self.ctx.root, self.ctx.config.sources) if branch else {}
        if branch and branch not in found:
            raise KeyError(f"no worktree on {branch}")
        self.ctx = Context(self.ctx.root, self.ctx.config, found.get(branch) if branch else None)
        if (loop := getattr(self, "loop", None)) and (rewatch := getattr(self, "rewatch", None)):
            loop.call_soon_threadsafe(rewatch.set)
        return {"branch": branch}


def make_app(ctx: Context, watch: bool = True, base: str = "", workspace: Workspace | None = None) -> Starlette:
    """The pages and API of one project.

    Parameters
    ----------
    ctx : Context
        The project.
    watch : bool
        Whether to watch its files and refresh pages as they change.
    base : str
        The path it's served under: empty on its own, `/p/<name>` in a workspace.
    workspace : Workspace or None
        The workspace it's one of, if any.

    Returns
    -------
    Starlette
        The app, with its `App` as `state.app`.
    """
    app = App(ctx, base, workspace)

    def locked(fn):
        def run(*args):
            with app.lock:
                # The project's links, for whatever this renders
                token = BASE.set(app.base)
                try:
                    return fn(*args)
                finally:
                    BASE.reset(token)

        return run

    async def threaded(fn, *args):
        return await asyncio.to_thread(locked(fn), *args)

    async def index(request: Request):
        return HTMLResponse(await threaded(app.index_page))

    async def walk(request: Request):
        return HTMLResponse(await threaded(app.walk_page, request.path_params["rel"]))

    async def glossary(request: Request):
        return HTMLResponse(await threaded(app.glossary_page))

    async def spec_(request: Request):
        return HTMLResponse(await threaded(app.spec_page, request.path_params["rel"]))

    async def reconcile(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.reconcile, b["path"], b.get("id")))

    async def edit(request: Request):
        return HTMLResponse(await threaded(app.edit_page, request.path_params["rel"]))

    async def file(request: Request):
        return JSONResponse(await threaded(app.file_view, request.query_params["path"], request.query_params.get("at")))

    async def named(request: Request):
        q = request.query_params
        s = (await threaded(app.pinned, q.get("at"))).index.named_at(q["name"], q["file"], int(q.get("line", 0)))
        if s is None:
            raise FileNotFoundError(f"no one symbol called {q['name']}")
        return JSONResponse({"file": s.file, "start": s.start, "end": s.end, "line": s.line, "qualified": s.qualified})

    async def symbols(request: Request):
        return JSONResponse(await threaded(app.symbols, request.query_params.get("q", "")))

    async def source(request: Request):
        rel = request.query_params["path"]
        return JSONResponse({"text": (await threaded(app.writable, rel)).read_text()})

    async def render_(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.render, b["path"], b["text"]))

    async def save(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.save, b["path"], b["text"]))

    async def review(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.review, b["path"], b.get("ref")))

    async def reopen(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.reopen, b["path"], b["ref"]))

    async def note(request: Request):
        b = await request.json()
        return JSONResponse(
            await threaded(app.note, b["path"], b["kind"], b["text"], b.get("after"), b.get("thread"), b.get("to"), b.get("about"))
        )

    async def resolve(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.resolve, b["path"], int(b["thread"]), b["mode"]))

    async def stage(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.set_stage, b["path"], b["stage"]))

    async def start_prd(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.start_prd, b["title"], b["ask"], b.get("source"), b.get("thread")))

    async def agree(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.agree, b["path"], int(b["line"]), int(b["end"]), b["text"]))

    async def branches_(request: Request):
        return JSONResponse(await threaded(app.branches))

    async def read_branch(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.read_branch, b.get("branch")))

    async def settle_(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.settle, b["path"], int(b["line"])))

    async def unsettle_(request: Request):
        b = await request.json()
        return JSONResponse(await threaded(app.unsettle, b["path"], int(b["line"])))

    async def events(request: Request):
        q: asyncio.Queue[Change] = asyncio.Queue()
        app.subscribers.add(q)

        async def stream():
            try:
                yield ": connected\n\n"
                quiet = 0
                while not app.closing and not await request.is_disconnected():
                    try:
                        change = await asyncio.wait_for(q.get(), timeout=1)
                        quiet = 0
                        yield f"data: {change.model_dump_json()}\n\n"
                    except TimeoutError:
                        quiet += 1
                        if quiet % 15 == 0:
                            yield ": ping\n\n"
            finally:
                app.subscribers.discard(q)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})

    async def not_found(request: Request, exc):
        return PlainTextResponse(f"Not found: {exc}", status_code=404)

    async def refused(request: Request, exc):
        return JSONResponse({"error": str(exc)}, status_code=409)

    async def forbidden(request: Request, exc):
        return JSONResponse({"error": f"not a codewalk: {exc}"}, status_code=403)

    @asynccontextmanager
    async def lifespan(_):
        stop = asyncio.Event()
        task = asyncio.create_task(app.watch(stop)) if watch else None
        yield
        stop.set()
        if task:
            task.cancel()

    starlette = Starlette(
        routes=[
            Route("/", index),
            Route("/walk/{rel:path}", walk),
            Route("/edit/{rel:path}", edit),
            Route("/spec/{rel:path}", spec_),
            Route("/glossary", glossary),
            Route("/api/file", file),
            Route("/api/symbols", symbols),
            Route("/api/named", named),
            Route("/api/source", source),
            Route("/api/render", render_, methods=["POST"]),
            Route("/api/save", save, methods=["POST"]),
            Route("/api/review", review, methods=["POST"]),
            Route("/api/reopen", reopen, methods=["POST"]),
            Route("/api/note", note, methods=["POST"]),
            Route("/api/settle", settle_, methods=["POST"]),
            Route("/api/unsettle", unsettle_, methods=["POST"]),
            Route("/api/branches", branches_),
            Route("/api/branch", read_branch, methods=["POST"]),
            Route("/api/agree", agree, methods=["POST"]),
            Route("/api/stage", stage, methods=["POST"]),
            Route("/api/prd", start_prd, methods=["POST"]),
            Route("/api/resolve", resolve, methods=["POST"]),
            Route("/api/reconcile", reconcile, methods=["POST"]),
            Route("/events", events),
            Mount("/static", StaticFiles(directory=STATIC)),
        ],
        exception_handlers={FileNotFoundError: not_found, PermissionError: forbidden, KeyError: not_found, ValueError: refused},
        lifespan=lifespan,
    )
    starlette.state.app = app
    return starlette


class _Server(uvicorn.Server):
    """uvicorn's server, which tells the pages' event streams to end when it's asked to stop.

    Parameters
    ----------
    config : uvicorn.Config
        The server's settings.
    apps : Callable
        The projects being served, when it's asked to stop: one, or a workspace's.
    """

    def __init__(self, config: uvicorn.Config, apps: Callable[[], list[App]]):
        super().__init__(config)
        self.apps = apps

    def handle_exit(self, sig, frame) -> None:
        for app in self.apps():
            app.closing = True
        super().handle_exit(sig, frame)


# r[impl serve.local+2]
# r[impl serve.stop]
def serve(ctx: Context, port: int) -> None:
    starlette = make_app(ctx)
    # However the streams behave, don't wait more than a moment for them
    config = uvicorn.Config(starlette, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2)
    _Server(config, lambda: [starlette.state.app]).run()


# r[impl serve.local+2]
# r[impl serve.stop]
# r[impl serve.workspace]
def serve_workspace(folder: Path, port: int) -> None:
    """Serve every project in the folders one level below `folder`, at once.

    Parameters
    ----------
    folder : Path
        The workspace: its folders with a `codewalk.toml` are its projects.
    port : int
        The port to listen on, on 127.0.0.1.
    """
    from codewalk.web.workspace import Workspace

    workspace = Workspace(folder)
    config = uvicorn.Config(workspace.starlette, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2)
    _Server(config, workspace.apps).run()
