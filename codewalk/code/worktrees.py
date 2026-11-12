"""Reading a project's code from a branch's worktrees, and from where that branch started.

A project reads code from its own repository and, through `../` globs, from others beside
it. Work on a branch that spans them is often a worktree of each, on the same branch. To
review it, the project's code can be read from those worktrees instead, under the same
names, and each symbol shown against the same symbol where the branch started: the commit
it shares with the branch it was made from, or with the repository's default branch.
"""

from __future__ import annotations

import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


def _git(cwd: Path, *args: str) -> str | None:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


class Checkout(BaseModel):
    """One repository's worktree on the branch, and where the branch started."""

    # The prefix of the project's paths into this repository: "" for the project's own,
    # `../other/` for one beside it
    prefix: str
    # The repository, as the project reads it today
    repo: Path
    # The worktree on the branch
    worktree: Path
    # The project's root within the repository: "" unless the project is a subfolder of it
    within: str = ""
    # The ref the branch started from, and the commit it shares with it
    base_ref: str
    base: str


class Worktrees(BaseModel):
    """A branch's worktrees, across the project's repositories."""

    branch: str
    checkouts: list[Checkout]

    def checkout(self, rel: str) -> Checkout | None:
        """The checkout a project path is in, if it's in one; the longest prefix wins."""
        # The project's own repository has no prefix, but no path out of it is in it
        found = [c for c in self.checkouts if rel.startswith(c.prefix) and (c.prefix or not rel.startswith("../"))]
        return max(found, key=lambda c: len(c.prefix), default=None)

    def where(self, rel: str) -> Path | None:
        """Where a project path is read from on the branch, if it's in one of its checkouts."""
        c = self.checkout(rel)
        return c.worktree / c.within / rel[len(c.prefix) :] if c else None

    def in_repo(self, rel: str) -> tuple[Checkout, str] | None:
        """The checkout a project path is in, and the path within that repository."""
        c = self.checkout(rel)
        return (c, os.path.normpath(os.path.join(c.within, rel[len(c.prefix) :]))) if c else None


def repositories(root: Path, globs: list[str]) -> dict[str, Path]:
    """The repositories a project reads code from, by the prefix of its paths into each.

    Parameters
    ----------
    root : Path
        The project's root.
    globs : list of str
        Its sources.

    Returns
    -------
    dict of str to Path
        `""` for the project's own repository, and `../name/` for each other one a glob
        reaches, with the repository's top folder.
    """
    out: dict[str, Path] = {}
    own = _git(root, "rev-parse", "--show-toplevel")
    if own:
        out[""] = Path(own)
    for g in globs:
        fixed = []
        for part in Path(g).parts:
            if any(c in part for c in "*?["):
                break
            fixed.append(part)
        if not fixed or fixed[0] != "..":
            continue
        folder = root.joinpath(*fixed)
        folder = folder if folder.is_dir() else folder.parent
        top = _git(folder, "rev-parse", "--show-toplevel") if folder.is_dir() else None
        if top and Path(top) != out.get(""):
            out[os.path.relpath(top, root) + "/"] = Path(top)
    return out


def _worktrees(repo: Path) -> dict[str, Path]:
    """The repository's worktrees other than the checkout itself, by branch."""
    out: dict[str, Path] = {}
    path = None
    for line in (_git(repo, "worktree", "list", "--porcelain") or "").split("\n"):
        if line.startswith("worktree "):
            path = Path(line[len("worktree ") :])
        elif line.startswith("branch refs/heads/") and path and path.resolve() != repo.resolve():
            out[line[len("branch refs/heads/") :]] = path
    return out


def started_from(worktree: Path, branch: str) -> str | None:
    """The ref the branch was made from, as its reflog records it, if that's a branch."""
    log = (_git(worktree, "reflog", "show", "--format=%gs", f"refs/heads/{branch}") or "").split("\n")
    first = log[-1] if log else ""
    ref = first.removeprefix("branch: Created from ").strip() if first.startswith("branch: Created from ") else ""
    if not ref or ref == "HEAD" or not _git(worktree, "rev-parse", "--verify", "--quiet", ref):
        return None
    return ref


# r[impl review.branch-base]
def base_of(worktree: Path, branch: str) -> tuple[str, str] | None:
    """Where the branch started: the ref it was made from, or the default branch, and the
    commit it shares with that ref.

    Parameters
    ----------
    worktree : Path
        A worktree on the branch.
    branch : str
        The branch.

    Returns
    -------
    tuple of (str, str) or None
        The ref and the commit; None if neither can be found.
    """
    ref = started_from(worktree, branch) or _git(worktree, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if not ref:
        return None
    commit = _git(worktree, "merge-base", branch, ref)
    return (ref, commit) if commit else None


# r[impl review.branches]
def branches(root: Path, globs: list[str]) -> dict[str, Worktrees]:
    """Every branch with a worktree in any of the project's repositories.

    Parameters
    ----------
    root : Path
        The project's root.
    globs : list of str
        Its sources.

    Returns
    -------
    dict of str to Worktrees
        By branch.
    """
    out: dict[str, Worktrees] = {}
    for prefix, repo in repositories(root, globs).items():
        within = os.path.relpath(root, repo) if prefix == "" else ""
        within = "" if within == "." else within
        for branch, worktree in _worktrees(repo).items():
            base = base_of(worktree, branch)
            if base is None:
                continue
            c = Checkout(prefix=prefix, repo=repo, worktree=worktree, within=within, base_ref=base[0], base=base[1])
            out.setdefault(branch, Worktrees(branch=branch, checkouts=[])).checkouts.append(c)
    return dict(sorted(out.items()))


@lru_cache(maxsize=512)
def blob(worktree: Path, commit: str, path: str) -> bytes | None:
    """A file as it was at a commit, or None if it wasn't there."""
    out = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=worktree, capture_output=True)
    return out.stdout if out.returncode == 0 else None


class Pin(BaseModel):
    """A ref in the project's repository that a codewalk is read at, and what it names."""

    # The ref as written
    ref: str
    commit: str
    # When the commit was made, as YYYY-MM-DD
    date: str
    # The repository's top folder
    repo: Path
    # The project's root within the repository: "" unless the project is a subfolder of it
    within: str = ""

    def path(self, rel: str) -> str:
        """A project path's path within the repository."""
        return os.path.normpath(os.path.join(self.within, rel))


# r[impl pin.at]
def pin(root: Path, ref: str) -> Pin | None:
    """The commit a ref names in the project's repository, if it names one.

    Parameters
    ----------
    root : Path
        The project's root.
    ref : str
        A tag, branch or commit.

    Returns
    -------
    Pin or None
        None if the ref names no commit, or the project isn't in a repository.
    """
    top = _git(root, "rev-parse", "--show-toplevel")
    commit = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") if top else None
    if not top or not commit:
        return None
    within = os.path.relpath(root.resolve(), Path(top).resolve())
    date = _git(root, "show", "-s", "--format=%cs", commit) or ""
    return Pin(ref=ref, commit=commit, date=date, repo=Path(top), within="" if within == "." else within)


@lru_cache(maxsize=64)
def tree(repo: Path, commit: str, within: str) -> tuple[str, ...]:
    """The files in a commit under a folder, as paths from that folder."""
    out = _git(repo, "ls-tree", "-r", "--name-only", commit, "--", within or ".") or ""
    prefix = within + "/" if within else ""
    return tuple(p[len(prefix) :] for p in out.split("\n") if p)


def glob_re(pattern: str) -> re.Pattern[str]:
    """A path glob as a regular expression: `**` any folders, `*` and `?` within one."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")
