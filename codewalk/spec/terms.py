"""Terms and facts: what words mean here, and what we know about the world.

Both are defined as tracey's requirements are, with IDs of their own under `term.` and
`fact.`, so they sit in the same files, read the same way, and tracey reads the spec
whole (it allows one prefix in a spec: `fact.tracey.one-prefix`):

    r[term.deadband]
    How far above its target a site's import can rise before we act.

    r[fact.ercot.settlement-periods] observed
    ERCOT judges a dispatch in 15-minute settlement periods, aligned to the clock.

Tracey counts them as requirements, never implemented; codewalk doesn't.

A **term** is a word with a meaning of its own here. Its ID is the word, with hyphens for
spaces (`r[term.settlement-period]`); a mention of the word in prose, or its plural, is linked
to it, so a reader can hover any use of it for what it means.

A **fact** is something about the world we rely on and don't control: an API's
behaviour, a market's rules. It says how we know it: `documented`, `observed` or
`assumed` (the default). Facts aren't requirements, which say what we do; a requirement
or a codewalk cites the facts it rests on, so when one turns out wrong, what rests on
it can be found.

Cite either explicitly with `[[t:deadband]]` and `[[f:ercot.settlement-periods]]`, or as
links, `[the deadband](term:deadband)` and `[periods](fact:ercot.settlement-periods)`.
Each is defined in the spec it belongs to, so the spec reads complete on its own.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# A PRD's front matter: its definitions are its own proposals, not the glossary's
PRD = re.compile(r"\A---\n(?:.*\n)*?kind:[ \t]*[\"']?prd[\"']?[ \t]*\n(?:.*\n)*?---", re.MULTILINE)
# `r[term.id]` or `r[fact.id]`, or with a spec's name for `r`, and what's known of it
DEF_LINE = re.compile(
    r"^[a-z][a-z0-9]*\[(?P<kind>term|fact)\.(?P<id>[a-z0-9][a-z0-9.\-]*)\]"
    r"(?:[ \t]+(?P<mod>documented|observed|assumed|cited-only))?[ \t]*$"
)
# Any marker line: a definition's text ends at the next
MARKER_LINE = re.compile(r"^[a-z][a-z0-9]*\[")
# The IDs requirements can't have, being terms' and facts'
KINDS = ("term.", "fact.")
STATUSES = ("documented", "observed", "assumed")


class Definition(BaseModel):
    kind: Literal["term", "fact"]
    id: str
    # How a fact is known; None for a term
    status: Literal["documented", "observed", "assumed"] | None = None
    # A term linked only where it's cited, `r[term.id] cited-only`, since its word is often used
    # in its ordinary sense
    cited_only: bool = False
    file: str
    line: int
    text: str

    @property
    def words(self) -> str:
        """A term as it's written in prose."""
        return self.id.replace("-", " ")


# r[impl glossary.define]
def parse(rel: str, text: str) -> list[Definition]:
    """The terms and facts defined in one file's text, in order.

    Parameters
    ----------
    rel : str
        The file, from the root.
    text : str
        Its Markdown.

    Returns
    -------
    list of Definition
    """
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not (m := DEF_LINE.match(line)):
            continue
        body = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip() or MARKER_LINE.match(nxt):
                break
            body.append(nxt.strip())
        kind, mod = m["kind"], m["mod"]
        # `cited-only` is a term's; a fact's status is one of the others
        if kind == "fact" and mod == "cited-only":
            continue
        status = (mod or "assumed") if kind == "fact" else None
        cited_only = mod == "cited-only"
        out.append(Definition(kind=kind, id=m["id"], status=status, cited_only=cited_only, file=rel, line=i + 1, text=" ".join(body)))
    return out


def is_prd(text: str) -> bool:
    """Whether a file's front matter says it's a PRD."""
    return bool(PRD.match(text))


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

    # r[impl glossary.define]
    # r[impl glossary.errors]
    # r[impl prd.terms]
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
            text = p.read_text()
            # A PRD's definitions are its own, proposed, not the spec's
            if is_prd(text):
                continue
            for d in parse(rel, text):
                table = terms if d.kind == "term" else facts
                if d.id in table:
                    dups.setdefault(f"{d.kind[0]}:{d.id}", [table[d.id]]).append(d)
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

    # r[impl glossary.cite]
    def mentions(self) -> re.Pattern | None:
        """A pattern for every term as it's written in prose, but those cited only.

        Longest first, singular or plural, whole words only, ignoring case.

        Returns
        -------
        re.Pattern or None
            None if no terms are to be found in prose.
        """
        if self._pattern is None:
            words = sorted((d.words for d in self.terms.values() if not d.cited_only), key=len, reverse=True)
            alts = "|".join(re.escape(w).replace(r"\ ", r"[ \-]") for w in words)
            self._pattern = re.compile(rf"\b({alts})(?:s|es)?\b", re.IGNORECASE) if words else None
        return self._pattern

    def term_for(self, mention: str) -> Definition | None:
        key = re.sub(r"[ ]+", "-", mention.lower())
        for cand in (key, re.sub(r"es$", "", key), re.sub(r"s$", "", key)):
            if cand in self.terms:
                return self.terms[cand]
        return None
