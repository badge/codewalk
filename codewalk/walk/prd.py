"""PRDs: a change agreed before it's made, in stages, in a file that reads on its own.

A PRD is a codewalk with `kind: prd`. Its requirements, terms and facts are written in
it as they'll read in the spec, but they're its own proposals, not the spec's: the spec
index never reads PRDs, and the glossary skips them. Here each is set against the spec as
it stands, so a reader sees what's new, what changes and what goes.
"""

from __future__ import annotations

import re
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from codewalk.spec import requirements, terms
from codewalk.walk import notes
from codewalk.walk.doc import Context, Walk

# Where the browser starts a PRD, from the root
FOLDER = "docs/prds"


class SpecChange(BaseModel):
    """A requirement, term or fact a PRD proposes, as it stands against the spec."""

    kind: Literal["requirement", "term", "fact"]
    id: str
    # Its line in the PRD
    line: int
    # The version it's written with; 1 for a term or fact
    version: int = 1
    how: Literal["new", "changed", "removed", "quoted", "error"]
    # Its text in the PRD, and the spec's, if the spec has it
    text: str = ""
    was: str | None = None
    # Why it's an error
    error: str | None = None


# r[impl prd.requirements]
# r[impl prd.compare]
# r[impl prd.terms]
def spec_changes(w: Walk) -> list[SpecChange]:
    """What a PRD proposes for the spec, each against the spec as it stands.

    Parameters
    ----------
    w : Walk
        The PRD.

    Returns
    -------
    list of SpecChange
        In the order they're written in it.
    """
    ctx = w.ctx
    out = []
    for r in requirements.parse(w.rel, w.text, ctx.spec.prefixes, removals=True):
        now = ctx.spec.find(r.id)
        if now is None:
            how, error = ("error", f"removes `{r.id}`, which the spec doesn't have") if r.removed else ("new", None)
        elif r.version <= now.version:
            same = r.version == now.version and r.text == now.text and not r.removed
            message = f"changes `{r.id}` without a new version: the spec's is version {now.version}"
            how, error = ("quoted", None) if same else ("error", message)
        else:
            how, error = ("removed" if r.removed else "changed"), None
        was = now.text if now else None
        out.append(SpecChange(kind="requirement", id=r.id, line=r.line, version=r.version, how=how, text=r.text, was=was, error=error))
    for d in terms.parse(w.rel, w.text):
        now = ctx.glossary.get(f"{d.kind[0]}:{d.id}")
        how = "new" if now is None else "quoted" if now.text == d.text else "changed"
        out.append(SpecChange(kind=d.kind, id=d.id, line=d.line, how=how, text=d.text, was=now.text if now else None))
    return sorted(out, key=lambda c: c.line)


# r[impl prd.template]
def template(title: str) -> str:
    """A new PRD's Markdown: `kind: prd`, at the problem stage, a section for each stage."""
    return (resources.files("codewalk") / "setup" / "prd.md").read_text().replace("{title}", title)


def slug(title: str) -> str:
    """A title as a file name: lower case, words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def name(folder: Path, title: str, day: date) -> str:
    """A new PRD's file name: the day, its number that day, and the title's slug.

    Parameters
    ----------
    folder : Path
        The PRDs' folder.
    title : str
        The PRD's title.
    day : date
        The day it's started.

    Returns
    -------
    str
        As `2026-11-12-1-stop-a-battery.md`: one more than the highest number of that day's
        PRDs, or 1.

    Raises
    ------
    FileExistsError
        If a PRD of the same slug was started that day.
    ValueError
        If the title has nothing a file can be named from.
    """
    s = slug(title)
    if not s:
        raise ValueError("a PRD needs a title with a letter or a number in it")
    taken = [m for p in folder.glob(f"{day.isoformat()}-*.md") if (m := re.fullmatch(rf"{day.isoformat()}-(\d+)-(.+)\.md", p.name))]
    if any(m.group(2) == s for m in taken):
        raise FileExistsError(f"a PRD called {s} was started on {day.isoformat()}")
    n = max((int(m.group(1)) for m in taken), default=0) + 1
    return f"{day.isoformat()}-{n}-{s}.md"


# r[impl prd.start+2]
def start(ctx: Context, title: str, ask: str, day: date | None = None) -> str:
    """Start a PRD in `docs/prds/`, named by the day, its number that day and the title's
    slug, with what was asked as a request.

    Parameters
    ----------
    ctx : Context
        The project.
    title : str
        Its title.
    ask : str
        What the person wants, in their own words.
    day : date or None
        The day it's started; today if None.

    Returns
    -------
    str
        The PRD's path, from the root.

    Raises
    ------
    FileExistsError
        If a PRD of the same slug was started that day.
    ValueError
        If the title has nothing a file can be named from.
    """
    rel = f"{FOLDER}/{name(ctx.root / FOLDER, title, day or date.today())}"
    target = ctx.root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(notes.request(template(title), ctx.config.who(ctx.root), ask))
    return rel
