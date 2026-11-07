"""Syntax highlighting, a line at a time.

Highlighting a line at a time means any range of a file can be shown with its own line
numbers and lines picked out. Each file is highlighted once, and again only once it's
changed.
"""

from __future__ import annotations

import html
from pathlib import Path

from pygments import lex
from pygments.lexers import PythonLexer, RustLexer, TextLexer, get_lexer_by_name
from pygments.token import STANDARD_TYPES, Token
from pygments.util import ClassNotFound

from codewalk.spec import tracey

_LEXERS = {".rs": RustLexer(), ".py": PythonLexer()}
_cache: dict[str, tuple[float, list[str]]] = {}

MARKER = tracey.MARKER


def _css_class(ttype) -> str:
    while ttype not in STANDARD_TYPES and ttype is not Token:
        ttype = ttype.parent
    return STANDARD_TYPES.get(ttype, "")


def highlight_lines(path: Path) -> list[str]:
    """The file's lines as HTML, highlighted, one string per line.

    Parameters
    ----------
    path : Path
        The file to highlight; its suffix picks the lexer.

    Returns
    -------
    list of str
        One string of HTML per line, cached until the file changes.
    """
    key = str(path)
    mtime = path.stat().st_mtime
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    rendered = _lines(path.read_text(), _LEXERS.get(path.suffix, TextLexer()))
    _cache[key] = (mtime, rendered)
    return rendered


def highlight_text(text: str, lang: str | None) -> list[str]:
    """Code that isn't in a file (a proposal's draft), highlighted as `lang`.

    Parameters
    ----------
    text : str
        The code.
    lang : str or None
        A Pygments lexer name; Rust if None, plain text if Pygments doesn't know it.

    Returns
    -------
    list of str
        One string of HTML per line.
    """
    try:
        lexer = get_lexer_by_name(lang) if lang else RustLexer()
    except ClassNotFound:
        lexer = TextLexer()
    return _lines(text, lexer)


def _lines(text: str, lexer) -> list[str]:
    lines: list[list[str]] = [[]]
    for ttype, value in lex(text, lexer):
        cls = _css_class(ttype)
        for i, part in enumerate(value.split("\n")):
            if i > 0:
                lines.append([])
            if part:
                esc = html.escape(part)
                if cls.startswith("c") and "[" in part:
                    esc = MARKER.sub(
                        lambda m: f'<a class="req" data-req="{tracey.key(m.group(1), m.group(3))}" href="#">{m.group(0)}</a>',
                        esc,
                    )
                lines[-1].append(f'<span class="{cls}">{esc}</span>' if cls else esc)
    rendered = ["".join(parts) for parts in lines]
    # `lex` ends with a newline the text may not have had
    want = len(text.split("\n"))
    return rendered[:want] + [""] * (want - len(rendered))
