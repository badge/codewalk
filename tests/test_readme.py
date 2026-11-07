"""The README's examples name codewalk's own code, so they're checked against it like any
walkthrough: a renamed function shows up here, not in a reader's confusion."""

import re
from pathlib import Path

from codewalk.config import Config
from codewalk.walk.doc import Context, Walk

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


def context() -> Context:
    return Context(ROOT, Config.load(ROOT))


def test_every_example_walkthrough_in_the_readme_resolves():
    ctx = context()
    examples = re.findall(r"^````markdown\n(.*?)^````$", README, flags=re.M | re.S)
    assert examples
    for text in examples:
        w = Walk(ctx, "README.md", text)
        errors = [p.message for p in w.problems() if p.severity == "error"]
        assert not errors, errors


def test_every_name_the_readme_writes_in_backticks_resolves():
    ctx = context()
    names = set(re.findall(r"`((?:crate::)?[A-Za-z_][\w]*(?:::[\w]+)+|[\w]+\.py#\w+)`", README))
    assert {"Walk::problems", "Renderer::embed", "doc.py#Context"} <= names
    for name in names:
        sym, _ = ctx.index.resolve(name)
        assert sym, name
