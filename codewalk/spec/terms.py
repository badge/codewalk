"""Terms and facts: what words mean here, and what we know about the world.

Both are defined the way tracey defines requirements, a marker on its own line and then
the text, so they sit in the same files and read the same way:

    t[deadband]
    How far above its target a site's import can rise before we act.

    f[ercot.settlement-periods] observed
    ERCOT judges a dispatch in 15-minute settlement periods, aligned to the clock.

A **term** is a word with a meaning of its own here. Its ID is the word, with hyphens for
spaces (`t[settlement-period]`); a mention of the word in prose, or its plural, is linked
to it, so a reader can hover any use of it for what it means.

A **fact** is something about the world we rely on and don't control: an API's
behaviour, a market's rules. It says how we know it: `documented`, `observed` or
`assumed` (the default). Facts aren't requirements, which say what we do; a requirement
or a walkthrough cites the facts it rests on, so when one turns out wrong, what rests on
it can be found.

Cite either explicitly with `[[t:deadband]]` and `[[f:ercot.settlement-periods]]`, or as
links, `[the deadband](term:deadband)` and `[periods](fact:ercot.settlement-periods)`.
Each is defined in the spec it belongs to, so the spec reads complete on its own. We
assume tracey passes over both kinds of line (`f[tracey.other-markers]`, not yet checked).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DEF_LINE = re.compile(r"^(t|f)\[([a-z0-9][a-z0-9.\-]*)\](?:[ \t]+(documented|observed|assumed))?[ \t]*$")
STATUSES = ("documented", "observed", "assumed")


class Definition(BaseModel):
    kind: Literal["term", "fact"]
    id: str
    # How a fact is known; None for a term
    status: Literal["documented", "observed", "assumed"] | None = None
    file: str
    line: int
    text: str

    @property
    def words(self) -> str:
        """A term as it's written in prose."""
        return self.id.replace("-", " ")


class Glossary:
    """Every term and fact defined in the given Markdown files, read again when one changes.

    Parameters
    ----------
    root : Path
        The repository's root.
    globs : list of str
        The Markdown files to look in, from the root.
    """

    def __init__(self, root: Path, globs: list[str]):
        self.root = root
        self.globs = globs
        self.terms: dict[str, Definition] = {}
        self.facts: dict[str, Definition] = {}
        # IDs defined more than once, with every place
        self.duplicates: dict[str, list[Definition]] = {}
        self._mtimes: dict[str, float] = {}
        self._pattern: re.Pattern | None = None
        self.refresh()

    # r[impl term.define]
    # r[impl term.errors]
    def refresh(self) -> bool:
        paths = sorted({p for g in self.globs for p in self.root.glob(g) if p.is_file() and p.suffix == ".md"})
        mtimes = {str(p.relative_to(self.root)): p.stat().st_mtime for p in paths}
        if mtimes == self._mtimes:
            return False
        self._mtimes = mtimes
        terms: dict[str, Definition] = {}
        facts: dict[str, Definition] = {}
        dups: dict[str, list[Definition]] = {}
        for p in paths:
            rel = str(p.relative_to(self.root))
            lines = p.read_text().split("\n")
            for i, line in enumerate(lines):
                m = DEF_LINE.match(line)
                if not m:
                    continue
                body = []
                for nxt in lines[i + 1 :]:
                    if not nxt.strip() or DEF_LINE.match(nxt) or nxt.startswith("r["):
                        break
                    body.append(nxt.strip())
                kind = "term" if m.group(1) == "t" else "fact"
                d = Definition(
                    kind=kind,
                    id=m.group(2),
                    status=(m.group(3) or "assumed") if kind == "fact" else None,
                    file=rel,
                    line=i + 1,
                    text=" ".join(body),
                )
                table = terms if kind == "term" else facts
                if d.id in table:
                    dups.setdefault(f"{m.group(1)}:{d.id}", [table[d.id]]).append(d)
                table[d.id] = d
        self.terms, self.facts, self.duplicates = terms, facts, dups
        self._pattern = None
        return True

    def get(self, ref: str) -> Definition | None:
        """A term or fact by its reference: `t:deadband` or `f:ercot.settlement-periods`.

        Parameters
        ----------
        ref : str
            `t:` or `f:`, then the ID.

        Returns
        -------
        Definition or None
            None if nothing by that ID is defined, or the kind isn't `t` or `f`.
        """
        kind, _, rid = ref.partition(":")
        return (self.terms if kind == "t" else self.facts if kind == "f" else {}).get(rid)

    def mentions(self) -> re.Pattern | None:
        """A pattern for every term as it's written in prose.

        Longest first, singular or plural, whole words only, ignoring case.

        Returns
        -------
        re.Pattern or None
            None if no terms are defined.
        """
        if self._pattern is None and self.terms:
            words = sorted((d.words for d in self.terms.values()), key=len, reverse=True)
            alts = "|".join(re.escape(w).replace(r"\ ", r"[ \-]") for w in words)
            self._pattern = re.compile(rf"\b({alts})(?:s|es)?\b", re.IGNORECASE)
        return self._pattern

    def term_for(self, mention: str) -> Definition | None:
        key = re.sub(r"[ ]+", "-", mention.lower())
        for cand in (key, re.sub(r"es$", "", key), re.sub(r"s$", "", key)):
            if cand in self.terms:
                return self.terms[cand]
        return None
