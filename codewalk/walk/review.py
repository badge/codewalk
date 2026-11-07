"""What a reader has reviewed.

For each walkthrough, it's each reference's code as it stood when it was last marked
reviewed. A reference whose code has changed since shows as changed, with the difference,
until it's reviewed again.

Kept in one file at the root, `codewalk.review.json`, so it's committed beside the code it
describes and travels with it.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

FILE = "codewalk.review.json"


class Reviewed(BaseModel):
    """The code a reference showed when it was marked reviewed, and its digest."""

    digest: str
    text: str


# Walkthrough, then reference as written, then what was reviewed
ReviewFile = TypeAdapter(dict[str, dict[str, Reviewed]])


class ReviewState:
    """What's been reviewed, as it was, kept in `codewalk.review.json` at the root.

    By walkthrough, then by reference: the code's digest and text when it was reviewed,
    so a change since can be seen and shown.

    Parameters
    ----------
    root : Path
        The repository's root, where the file is.
    """

    def __init__(self, root: Path):
        self.path = root / FILE
        self.data: dict[str, dict[str, Reviewed]] = {}
        self._mtime = None
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.data, self._mtime = {}, None
            return
        mtime = self.path.stat().st_mtime
        if mtime != self._mtime:
            self.data = ReviewFile.validate_json(self.path.read_bytes())
            self._mtime = mtime

    def save(self) -> None:
        ordered = {doc: dict(sorted(refs.items())) for doc, refs in sorted(self.data.items())}
        self.path.write_bytes(ReviewFile.dump_json(ordered, indent=2) + b"\n")
        self._mtime = self.path.stat().st_mtime

    def get(self, doc: str, ref: str) -> Reviewed | None:
        self.load()
        return self.data.get(doc, {}).get(ref)

    # r[impl review.record]
    def mark(self, doc: str, ref: str, digest: str, text: str) -> None:
        self.load()
        self.data.setdefault(doc, {})[ref] = Reviewed(digest=digest, text=text)
        self.save()

    def forget_missing(self, doc: str, refs: set[str]) -> None:
        """Drop what's recorded for references the walkthrough no longer makes.

        Parameters
        ----------
        doc : str
            The walkthrough.
        refs : set of str
            The references it makes now, as written.
        """
        self.load()
        entries = self.data.get(doc, {})
        gone = [r for r in entries if r not in refs]
        for r in gone:
            del entries[r]
        if gone:
            self.save()


def diff(before: str, after: str, start_before: int = 1, start_after: int = 1) -> list[tuple[str, str]]:
    """A line diff, as (kind, line) with kind one of ' ', '-', '+'.

    Parameters
    ----------
    before, after : str
        The text before and after.
    start_before, start_after : int
        The line numbers each starts at.

    Returns
    -------
    list of tuple of (str, str)
        Each line with its kind: ' ' unchanged, '-' removed, '+' added.
    """
    out = []
    for line in difflib.ndiff(before.split("\n"), after.split("\n")):
        tag, text = line[:1], line[2:]
        if tag in (" ", "-", "+"):
            out.append((tag, text))
    return out
