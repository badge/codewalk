"""What tracey's config says about the specs: their names, and which files are theirs.

tracey keeps its config in `.config/tracey/config.styx`. codewalk reads just enough of it
to know which Markdown files are specs, and which prefixes their requirements are written
with: `r[id]`, and a spec's own name (`v1[id]` for the spec named `v1`). Everything else
in it (the implementations, coverage) is tracey's.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

FILE = Path(".config/tracey/config.styx")
# A requirement's ID, and the same with the spec it's in (`v1:slack.client`) when that
# spec writes its requirements with a prefix other than `r`
ID = r"[a-z0-9][a-z0-9.\-]*"
QUALIFIED = rf"(?:[a-z][a-z0-9]*:)?{ID}"
# A requirement's marker in code, `r[impl id]` or `v1[verify id]`
MARKER = re.compile(rf"\b([a-z][a-z0-9]*)\[(impl|verify)\s+({ID})\]")
# `t` and `f` are the glossary's
RESERVED = {"t", "f"}


class Spec(BaseModel):
    name: str
    include: list[str]


def key(prefix: str, rid: str) -> str:
    """What codewalk calls a requirement: its ID, with its spec's name unless it's an `r[…]` one."""
    return rid if prefix == "r" else f"{prefix}:{rid}"


def load(root: Path) -> list[Spec]:
    """The specs tracey's config names, each with the globs of its Markdown.

    Parameters
    ----------
    root : Path
        The repository's root.

    Returns
    -------
    list of Spec
        In the config's order; none if there's no config.
    """
    path = root / FILE
    if not path.exists():
        return []
    text = re.sub(r"//[^\n]*", "", path.read_text())
    out = []
    # Each spec: its name, then its own `include`, before its `impls`
    # (an implementation has a name and an include too, but one brace deeper)
    for m in re.finditer(r"\bname\s+([A-Za-z0-9_\-]+)\s+include\s*\(([^)]*)\)", text):
        before = text[: m.start()]
        if before.count("{") - before.count("}") == 1:
            out.append(Spec(name=m.group(1), include=m.group(2).split()))
    return out


def prefixes(specs: list[Spec]) -> set[str]:
    """The prefixes a requirement line can have: `r`, and each spec's name."""
    return ({"r"} | {s.name for s in specs}) - RESERVED
