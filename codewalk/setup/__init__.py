"""`codewalk init`: set codewalk up in a project, for people and agents alike.

- `codewalk.toml`, if there isn't one, so it's clear where codewalk looks.
- A section in `AGENTS.md` saying how codewalks, specs and the glossary work here,
  between markers so running init again replaces it rather than adding another.
- Two skills, in `.claude/skills/`: `codewalk-propose`, to propose a change as a
  codewalk before writing it, and `codewalk-work`, to carry one forward.

Every file it would touch is reported, and `--dry-run` touches none.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

START = "<!-- codewalk:start (written by `codewalk init`; edit freely, init replaces it) -->"
END = "<!-- codewalk:end -->"
PAST = {
    "write": "wrote",
    "write the skill": "wrote the skill",
    "add a codewalk section to": "added a codewalk section to",
    "update the codewalk section of": "updated the codewalk section of",
}

CONFIG = """# Where codewalk looks, as globs from here.
# The code codewalks can refer to: .rs and .py files
sources = {sources}
# Markdown with tracey's requirement markers, r[id] on a line of its own
specs = ["docs/spec/**/*.md"]
# Codewalks: any Markdown file here that makes a reference is one
docs = ["docs/**/*.md"]
"""


def _text(name: str) -> str:
    return (resources.files("codewalk") / "setup" / name).read_text()


def _fill(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def init(root: Path, command: str | None = None, codewalks: str = "docs/codewalks", dry_run: bool = False) -> list[str]:
    """Set codewalk up in the project at `root`.

    Parameters
    ----------
    root : Path
        The project's root.
    command : str or None
        How to run codewalk there, for the docs and skills; worked out if None.
    codewalks : str
        Where codewalks go, from the root.
    dry_run : bool
        Report what it would do, and touch nothing.

    Returns
    -------
    list of str
        What it did (or would do), a line for each file.
    """
    package = Path(__file__).resolve().parents[2]
    inside = package.is_relative_to(root)
    if command is None:
        command = f"uv run --project {os.path.relpath(package, root)} codewalk" if inside else "codewalk"
    # Linked when codewalk is in the project; outside it, there's nothing in the project to link to
    if inside:
        link = f"[codewalk]({os.path.relpath(package / 'README.md', root)})"
        syntax = f"[`SYNTAX.md`]({os.path.relpath(package / 'SYNTAX.md', root)})"
    else:
        link, syntax = "codewalk", "codewalk's own `SYNTAX.md`"
    install = ""
    if not inside:
        install = "\nIf `codewalk` isn't a command yet, install it from its repository with\n`uv tool install --editable .`.\n"
    values = {"codewalk": command, "codewalk_link": link, "codewalk_syntax": syntax, "install": install, "codewalks": codewalks}
    done: list[str] = []

    def write(rel: str, text: str, what: str) -> None:
        done.append(f"{'would ' + what if dry_run else PAST[what]}: {rel}")
        if not dry_run:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    if not (root / "codewalk.toml").exists():
        langs = []
        if any(root.glob("src/**/*.rs")):
            langs.append('"src/**/*.rs"')
        if any(root.glob("src/**/*.py")) or any(root.glob("*/**/*.py")):
            langs.append('"**/*.py"')
        write("codewalk.toml", CONFIG.format(sources="[" + ", ".join(langs or ['"src/**/*.rs"']) + "]"), "write")

    section = f"{START}\n{_fill(_text('agents.md'), values).rstrip()}\n{END}\n"
    agents = root / "AGENTS.md"
    if agents.exists():
        current = agents.read_text()
        if START.split(" ")[0] in current and END in current:
            head = current[: current.index(START.split(" ")[0])]
            tail = current[current.index(END) + len(END) :].lstrip("\n")
            updated = head + section + ("\n" + tail if tail else "")
            if updated != current:
                write("AGENTS.md", updated, "update the codewalk section of")
        else:
            write("AGENTS.md", current.rstrip("\n") + "\n\n" + section, "add a codewalk section to")
    else:
        write("AGENTS.md", "# Contributing\n\n" + section, "write")

    for name, skill in (("codewalk-propose", "skill-propose.md"), ("codewalk-work", "skill-work.md")):
        rel = f".claude/skills/{name}/SKILL.md"
        text = _fill(_text(skill), values)
        if not (root / rel).exists() or (root / rel).read_text() != text:
            write(rel, text, "write the skill")
    return done
