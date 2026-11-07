"""All the codewalks together, as the index page shows them.

That's what each says about itself, how they relate, and how far each has been reviewed.

Codewalks relate by linking to each other, in their text or in their front matter's
`related`. A link is one way, but either end shows it: a codewalk lists what it links
to and what links to it.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath

from pydantic import BaseModel

from codewalk.spec import prose
from codewalk.walk.doc import Context, Stage, Walk


class Summary(BaseModel):
    """One codewalk, as the index shows it."""

    rel: str
    # From its front matter: where it goes in its folder
    weight: int | None = None
    title: str
    summary: str | None
    tags: list[str]
    # Its folder, which is how the index groups codewalks
    folder: str
    # Other codewalks it links to, and that link to it, as paths from the root
    links_to: list[str]
    linked_from: list[str] = []
    references: int
    embedded: int
    reviewed: int
    broken: int
    changed: int
    # "prd", say, from its front matter
    kind: str | None = None
    # For a PRD, its stage, from its front matter
    stage: Stage | None = None
    # Its proposals: not written yet, written, settled
    proposed: int = 0
    written: int = 0
    settled: int = 0

    @property
    def plan(self) -> int:
        return self.proposed + self.written + self.settled

    @property
    def plan_status(self) -> str:
        if not self.plan:
            return ""
        return "proposed" if self.proposed == self.plan else "done" if self.settled == self.plan else "in progress"

    @property
    def reviewed_pct(self) -> int:
        return int(100 * self.reviewed / self.embedded) if self.embedded else 100


class SpecSummary(BaseModel):
    """A spec file, as the index shows it: its requirements against its prose."""

    rel: str
    weight: int | None = None
    title: str
    requirements: int
    # Requirements here that its prose cites, and that it doesn't
    cited: int
    uncited: int
    # Citations in its prose of requirements not written yet
    missing: int
    drifted: int


# r[impl ui.weight]
def by_weight(s: Summary | SpecSummary) -> tuple:
    """Where a codewalk or spec goes in its folder: lighter first, then the rest, by title."""
    return (s.weight is None, s.weight or 0, s.title.lower())


class Library(BaseModel):
    codewalks: list[Summary]
    specs: list[SpecSummary] = []

    @classmethod
    def of(cls, ctx: Context) -> Library:
        rels = ctx.codewalks()
        known = set(rels)
        out: dict[str, Summary] = {}
        for rel in rels:
            w = Walk(ctx, rel)
            problems = w.problems()
            reviewed, embedded = w.reviewed_count()
            out[rel] = Summary(
                rel=rel,
                weight=w.meta.weight,
                title=w.title,
                summary=w.summary,
                tags=sorted(set(w.meta.tags)),
                folder=str(PurePosixPath(rel).parent),
                links_to=[l for l in w.links if l in known],
                references=len(w.refs),
                embedded=embedded,
                reviewed=reviewed,
                broken=sum(1 for p in problems if p.severity == "error"),
                changed=sum(1 for p in problems if p.severity == "warning"),
                kind=w.meta.kind,
                stage=(w.meta.stage or "problem") if w.meta.kind == "prd" else None,
                **w.progress().model_dump(),
            )
        for s in out.values():
            for target in s.links_to:
                out[target].linked_from.append(s.rel)
        specs = []
        for rel in ctx.spec_paths():
            v = prose.view(ctx, rel)
            uncited = len(v.uncited)
            specs.append(
                SpecSummary(
                    rel=rel,
                    weight=(sw := Walk(ctx, rel)).meta.weight,
                    title=sw.title,
                    requirements=len(v.defined),
                    cited=len(v.defined) - uncited,
                    uncited=uncited,
                    missing=len(v.missing),
                    drifted=len(v.drifted),
                )
            )
        return cls(codewalks=list(out.values()), specs=specs)

    def get(self, rel: str) -> Summary | None:
        return next((s for s in self.codewalks if s.rel == rel), None)

    def titles(self) -> dict[str, str]:
        return {s.rel: s.title for s in self.codewalks}

    def tags(self) -> list[tuple[str, int]]:
        """Every tag, with how many codewalks have it, most used first.

        Returns
        -------
        list of tuple of (str, int)
            Each tag and its count; ties in order of tag.
        """
        counts = Counter(t for s in self.codewalks for t in s.tags)
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    def folders(self) -> list[tuple[str, list[Summary]]]:
        """The codewalks grouped by folder, folders in order, each in order of weight.

        Lighter first; those without a weight after, by title.

        Returns
        -------
        list of tuple of (str, list of Summary)
            Each folder and its codewalks.
        """
        groups: dict[str, list[Summary]] = {}
        for s in self.codewalks:
            groups.setdefault(s.folder, []).append(s)
        return [(f, sorted(g, key=by_weight)) for f, g in sorted(groups.items())]

    # r[impl ui.index]
    def spec_tree(self) -> list[tuple[int, str | None, SpecSummary | None]]:
        """The specs as a tree of folders, for the index: each folder, then what's in it.

        Returns
        -------
        list of tuple of (int, str or None, SpecSummary or None)
            Each row's depth, and either a folder's name (from the one above it) or a spec.
        """
        # A folder's own files before the folders in it
        # In order of weight within a folder; its own files before the folders in it
        paths = sorted(self.specs, key=lambda s: (s.rel.split("/")[:-1], by_weight(s)))
        paths = sorted(paths, key=lambda s: [*s.rel.split("/")[:-1], "\0"])
        dirs = [s.rel.split("/")[:-1] for s in paths]
        # The folders every spec is in aren't worth a row each
        common = 0
        while dirs and all(len(d) > common and d[common] == dirs[0][common] for d in dirs):
            common += 1
        out: list[tuple[int, str | None, SpecSummary | None]] = []
        shown: list[str] = []
        for s, d in zip(paths, dirs, strict=False):
            d = d[common:]
            keep = 0
            while keep < min(len(shown), len(d)) and shown[keep] == d[keep]:
                keep += 1
            out += [(depth, d[depth], None) for depth in range(keep, len(d))]
            shown = d
            out.append((len(d), None, s))
        return out
