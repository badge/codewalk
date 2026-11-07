"""Where codewalk looks, from `codewalk.toml` at the repository's root if there is one."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

FILE = "codewalk.toml"


class Config(BaseModel):
    """Globs, from the repository's root."""

    model_config = ConfigDict(extra="forbid")

    # The code walkthroughs can refer to: `.rs` and `.py` files
    sources: list[str] = ["src/**/*.rs"]
    # Markdown with tracey's requirement markers, `r[id]` on a line of its own
    specs: list[str] = ["docs/spec/**/*.md"]
    # Where walkthroughs are: any Markdown file here that makes a reference is one
    docs: list[str] = ["docs/**/*.md"]
    # Who notes written in the browser are from, as `@author`; else the first word of
    # git's user.name, in lower case
    author: str | None = None

    def who(self, root: Path) -> str | None:
        if self.author:
            return self.author
        out = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, cwd=root)
        name = out.stdout.strip().split()
        return name[0].lower() if name else None

    @classmethod
    def load(cls, root: Path) -> Config:
        path = root / FILE
        return cls.model_validate(tomllib.loads(path.read_text())) if path.exists() else cls()


def repo_root(start: Path | None = None) -> Path:
    """The root of the git repository `start` (or the current folder) is in.

    Outside a repository, it's the folder itself.

    Parameters
    ----------
    start : Path or None
        Where to start looking; the current folder if None.

    Returns
    -------
    Path
        The repository's root, or `start` (or the current folder) outside one.
    """
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, cwd=start)
    return Path(out.stdout.strip()) if out.returncode == 0 else (start or Path.cwd())
