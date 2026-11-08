"""The spec's requirements, from the files tracey's config names as specs."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from codewalk.spec import terms, tracey


class Requirement(BaseModel):
    id: str
    file: str
    line: int
    text: str
    # From `r[id+N]`; 1 without a suffix
    version: int = 1
    # Only in a PRD: `r[id+N] removed`, a requirement it takes out of the spec
    removed: bool = False


REQ = re.compile(rf"^([a-z][a-z0-9]*)\[({tracey.ID}){tracey.VERSION}\](?:[ \t]+(removed))?\s*$")


# r[impl spec.prefix+2]
def parse(rel: str, text: str, prefixes: set[str], removals: bool = False) -> list[Requirement]:
    """The requirements in one file's text, in order, each with its version.

    Parameters
    ----------
    rel : str
        The file, from the root.
    text : str
        Its Markdown.
    prefixes : set of str
        The prefixes a requirement line can have, from `tracey::prefixes`.
    removals : bool
        Whether to read `r[id+N] removed` as a removal: in a PRD, and nowhere else.

    Returns
    -------
    list of Requirement
    """
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = REQ.match(line)
        # A term or a fact is written as one, but isn't one (`glossary.define`)
        if not m or m.group(1) not in prefixes or (m.group(4) and not removals) or m.group(2).startswith(terms.KINDS):
            continue
        body = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip() or REQ.match(nxt):
                break
            body.append(nxt.strip())
        out.append(
            Requirement(
                id=tracey.key(m.group(1), m.group(2)),
                file=rel,
                line=i + 1,
                text="" if m.group(4) else " ".join(body),
                version=int(m.group(3) or 1),
                removed=bool(m.group(4)),
            )
        )
    return out


class SpecIndex:
    """Each requirement in the spec: its ID, where it is, and its text.

    The spec is the files tracey's config names as specs, and any more the config gives.
    A requirement is a line of its own, `r[id]` or with the name of a spec in tracey's
    config, `v1[id]`. One with a spec's name is known by both, `v1:id`, since two specs
    can have the same ID.

    Parameters
    ----------
    root : Path
        The repository's root, where tracey's config is looked for.
    globs : list of str
        Spec files, from the root, as well as those tracey's config names.
    """

    # r[impl spec.files]
    def __init__(self, root: Path, globs: list[str]):
        self.root = root
        specs = tracey.load(root)
        self.globs = list(dict.fromkeys([*globs, *(g for s in specs for g in s.include)]))
        self.prefixes = tracey.prefixes(specs)
        self.requirements: dict[str, Requirement] = {}
        # The prefix each spec file writes its requirements with
        self.prefix_of: dict[str, str] = {}
        self._mtimes: dict[str, float] = {}
        self.refresh()

    # r[impl spec.prefix+2]
    def find(self, rid: str, rel: str | None = None) -> Requirement | None:
        """The requirement `rid` names, as written in `rel`.

        In the spec `rel` is in (`slack.client` in a `v1` file is `v1:slack.client`),
        else exactly, else the one requirement of any spec with that ID.

        Parameters
        ----------
        rid : str
            The ID as written.
        rel : str or None
            The file it's written in.

        Returns
        -------
        Requirement or None
            None if there's none, or several with that ID in different specs.
        """
        if rel and (p := self.prefix_of.get(rel)) and (r := self.requirements.get(tracey.key(p, rid))):
            return r
        if r := self.requirements.get(rid):
            return r
        found = [r for k, r in self.requirements.items() if k.split(":")[-1] == rid]
        return found[0] if len(found) == 1 else None

    # r[impl spec.prefix+2]
    def refresh(self) -> bool:
        paths = sorted({p for g in self.globs for p in self.root.glob(g) if p.is_file()})
        mtimes = {str(p.relative_to(self.root)): p.stat().st_mtime for p in paths}
        if mtimes == self._mtimes:
            return False
        self._mtimes = mtimes
        reqs = {}
        self.prefix_of = {}
        for p in paths:
            rel = str(p.relative_to(self.root))
            for r in parse(rel, p.read_text(), self.prefixes):
                self.prefix_of.setdefault(rel, r.id.split(":")[0] if ":" in r.id else "r")
                reqs[r.id] = r
        self.requirements = reqs
        return True
