"""The trail from prose to spec to code, so each can be read beside the others.

A spec's prose gives rise to its requirements; a walkthrough proposes the code that will
meet them, and once it's written, shows it. The link at each step is already there:

- the prose cites the requirements it gives rise to (see `spec.py`);
- code, written or proposed, carries tracey's markers, `// r[impl id]` and
  `// r[verify id]`, and a draft in a `walk proposed` block carries them too;
- a walkthrough's prose can cite requirements, as `[[r:id]]` or an ID in backticks.

So for each block of a walkthrough, `margin` finds the requirements it proposes,
implements, verifies or cites, and for each, the prose in its spec that gave rise to it:
the walkthrough page shows them in its margin, level with the block. And `uses` goes the
other way, for a spec's margin: for each requirement, the walkthroughs that propose,
implement or cite it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# A marker in a comment, not one written about in a docstring
from codewalk.code.index import MARKER
from codewalk.spec import prose, tracey
from codewalk.walk.doc import Context, Walk

Role = Literal["proposes", "proposes a test of", "implements", "verifies", "cites"]


class Link(BaseModel):
    """A requirement as one block of a walkthrough has it."""

    id: str
    role: Role
    # The walkthrough's block: its first line
    line: int


# r[impl spec.trail]
def links(walk: Walk) -> list[Link]:
    """Every requirement each block of a walkthrough proposes, implements, verifies or cites.

    In order, once for each block and role.

    Parameters
    ----------
    walk : Walk
        The walkthrough.

    Returns
    -------
    list of Link
        Each requirement with its role, at the first line of its block.
    """
    known = walk.ctx.spec
    files = walk.ctx.index.files
    out: list[Link] = []
    fences = [t for t in walk.tokens if t.type == "fence" and t.map and t.info.split()[:1] == ["walk"]]

    def block_of(line: int) -> int:
        for t in fences:
            if t.map[0] < line <= t.map[1]:
                return t.map[0] + 1
        return line

    for ref in walk.refs:
        at = block_of(ref.line)
        if ref.kind == "proposal":
            for prefix, kind, rid, _ in MARKER.findall(ref.draft or ""):
                rid = tracey.key(prefix, rid)
                out.append(Link(id=rid, role="proposes" if kind == "impl" else "proposes a test of", line=at))
        elif ref.kind == "embed" and ref.symbol:
            text = ref.symbol.text(files)
            for prefix, kind, rid, _ in MARKER.findall(text):
                rid = tracey.key(prefix, rid)
                out.append(Link(id=rid, role="implements" if kind == "impl" else "verifies", line=at))
        elif ref.kind == "embed" and ref.requirement:
            out.append(Link(id=ref.requirement.id, role="cites", line=at))
    for line, _, block in prose._blocks(walk):
        for rid in prose.cited_ids(block, known, walk.rel):
            out.append(Link(id=rid, role="cites", line=line))
    seen, unique = set(), []
    for link in out:
        key = (link.id, link.role, link.line)
        if key not in seen:
            seen.add(key)
            unique.append(link)
    return unique


class Origin(BaseModel):
    """Where a requirement comes from: its spec, and the prose there that cites it."""

    file: str
    # The prose citing it, and the line it starts on; None if no prose cites it
    prose: str | None = None
    line: int | None = None


# r[impl spec.trail]
def origin(ctx: Context, rid: str, views: dict[str, prose.SpecView]) -> Origin | None:
    req = ctx.spec.requirements.get(rid)
    if req is None:
        return None
    if req.file not in views:
        views[req.file] = prose.view(ctx, req.file)
    cite = next((c for c in views[req.file].citations if c.id == rid), None)
    if cite is None:
        return Origin(file=req.file)
    return Origin(file=req.file, prose=cite.prose.split("\n\n")[0], line=cite.lines[0])


class Use(BaseModel):
    """A walkthrough's use of a requirement."""

    walkthrough: str
    title: str
    line: int
    role: Role


def uses(ctx: Context) -> dict[str, list[Use]]:
    """For each requirement, the walkthroughs that propose, implement, verify or cite it.

    Parameters
    ----------
    ctx : Context
        The project.

    Returns
    -------
    dict of str to list of Use
        By requirement ID.
    """
    out: dict[str, list[Use]] = {}
    for rel in ctx.walkthroughs():
        w = Walk(ctx, rel)
        for link in links(w):
            out.setdefault(link.id, []).append(Use(walkthrough=rel, title=w.title, line=link.line, role=link.role))
    return out
