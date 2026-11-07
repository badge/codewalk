"""The prose and the spec, side by side.

A spec file opens with prose: what the thing is for and how we mean to do it. The
requirements after it say exactly what must happen, and tracey holds the code to them.
The prose is written by people; the requirements are written from it, often by an agent,
and the two have to keep saying the same thing.

So the prose cites the requirements it gives rise to: a requirement's ID in backticks
(`program.ercot-ers-strict.end`), `[[r:program.ercot-ers-strict.end]]`, or
`[the end](req:program.ercot-ers-strict.end)`. The spec view shows each cited requirement
in the margin beside the prose that cites it, and says:

- which requirements in the file no prose cites,
- which citations name requirements that don't exist yet (written in the prose, waiting
  to be written in the spec),
- and, for each requirement, whether it or the prose citing it has changed since the two
  were last reconciled, so a change to one side shows on the other.

Reconciling records both sides as they stand, in the review file. Everything else about
requirements (coverage, validation) stays with tracey.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel

from . import tracey
from .doc import WIKI, Context, Walk
from .index import Requirement, SpecIndex

REQ_LINE = re.compile(rf"^[a-z][a-z0-9]*\[{tracey.ID}\]")
CITE_CODE = re.compile(r"`([a-z0-9][a-z0-9.\-]*\.[a-z0-9.\-]+)`")
CITE_LINK = re.compile(rf"\]\(req:({tracey.QUALIFIED})\)")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


class Citation(BaseModel):
    """A requirement the prose cites, where, and how it stands against the prose."""

    id: str
    # The top-level blocks of prose citing it, by first line
    lines: list[int]
    requirement: Requirement | None = None
    # The prose citing it, as it stands
    prose: str = ""
    # never: not reconciled yet; ok; prose, spec or both: changed since reconciled
    state: Literal["never", "ok", "prose", "spec", "both", "missing"] = "never"


class SpecView(BaseModel):
    rel: str
    # The requirements this file defines, in order
    defined: list[Requirement]
    citations: list[Citation]

    @property
    def uncited(self) -> list[Requirement]:
        cited = {c.id for c in self.citations}
        return [r for r in self.defined if r.id not in cited]

    @property
    def missing(self) -> list[Citation]:
        return [c for c in self.citations if c.requirement is None]

    @property
    def drifted(self) -> list[Citation]:
        return [c for c in self.citations if c.state in ("prose", "spec", "both")]


def _blocks(walk: Walk) -> list[tuple[int, int, str]]:
    """The blocks of prose, as (first line, end line, Markdown).

    Each paragraph, wherever it is (a bullet's is its own), and each table; not the
    requirements themselves.

    Parameters
    ----------
    walk : Walk
        The parsed file.

    Returns
    -------
    list of tuple of (int, int, str)
        Each block's first line (1-based), its end line, and its Markdown.
    """
    lines = walk.text.split("\n")
    out = []
    for tok in walk.tokens:
        if tok.type not in ("paragraph_open", "table_open") or not tok.map:
            continue
        start, end = tok.map
        text = "\n".join(lines[start:end])
        if REQ_LINE.match(text.strip()):
            continue
        out.append((start + 1, end, text))
    return out


def cited_ids(text: str, known: SpecIndex, rel: str | None = None) -> list[str]:
    """The requirement IDs a block of prose cites, in order.

    That's backticked IDs that are requirements (or look like them, and are cited as such
    elsewhere), `[[r:…]]`, and `(req:…)` links.

    Parameters
    ----------
    text : str
        The block's Markdown.
    known : SpecIndex
        Every requirement; a backticked ID counts only if it's one.
    rel : str or None
        The file the prose is in, for IDs written without their spec's name.

    Returns
    -------
    list of str
        The IDs, each once.
    """
    out: list[str] = []
    for m in CITE_CODE.finditer(text):
        if r := known.find(m.group(1), rel):
            out.append(r.id)
    written = [m.group(1).strip()[2:] for m in WIKI.finditer(text) if m.group(1).strip().startswith("r:")]
    for rid in written + CITE_LINK.findall(text):
        r = known.find(rid, rel)
        out.append(r.id if r else rid)
    return list(dict.fromkeys(out))


def review_key(rel: str) -> str:
    return f"spec:{rel}"


def view(ctx: Context, rel: str, text: str | None = None) -> SpecView:
    walk = Walk(ctx, rel, text)
    known = ctx.spec
    defined = sorted((r for r in known.requirements.values() if r.file == rel), key=lambda r: r.line)
    by_id: dict[str, list[tuple[int, str]]] = {}
    for line, _, block in _blocks(walk):
        for rid in cited_ids(block, known, rel):
            by_id.setdefault(rid, []).append((line, block))
    citations = []
    for rid, blocks in by_id.items():
        req = known.requirements.get(rid)
        c = Citation(id=rid, lines=[line for line, _ in blocks], requirement=req, prose="\n\n".join(b for _, b in blocks))
        if req is None:
            c.state = "missing"
        else:
            prose = _digest("\n\n".join(b for _, b in blocks))
            spec = _digest(req.text)
            was_prose = ctx.review.get(review_key(rel), f"{rid}#prose")
            was_spec = ctx.review.get(review_key(rel), f"{rid}#spec")
            if was_prose is None or was_spec is None:
                c.state = "never"
            else:
                moved = (was_prose.digest != prose, was_spec.digest != spec)
                c.state = {(False, False): "ok", (True, False): "prose", (False, True): "spec", (True, True): "both"}[moved]
        citations.append(c)
    return SpecView(rel=rel, defined=defined, citations=citations)


def reconcile(ctx: Context, rel: str, rid: str | None = None) -> list[str]:
    """Record the prose citing a requirement, and the requirement, as they stand.

    That is, they say the same thing. All the cited requirements if `rid` is None.

    Parameters
    ----------
    ctx : Context
        The project.
    rel : str
        The spec file.
    rid : str or None
        The requirement; every cited one if None.

    Returns
    -------
    list of str
        The requirements reconciled; one cited but not defined is skipped.
    """
    walk = Walk(ctx, rel)
    known = ctx.spec
    blocks: dict[str, list[str]] = {}
    for _, _, block in _blocks(walk):
        for cid in cited_ids(block, known, rel):
            blocks.setdefault(cid, []).append(block)
    done = []
    for cid, texts in blocks.items():
        if (rid is None or cid == rid) and cid in known.requirements:
            prose = "\n\n".join(texts)
            ctx.review.mark(review_key(rel), f"{cid}#prose", _digest(prose), prose)
            ctx.review.mark(review_key(rel), f"{cid}#spec", _digest(known.requirements[cid].text), known.requirements[cid].text)
            done.append(cid)
    return done
