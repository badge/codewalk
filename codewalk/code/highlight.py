"""Syntax highlighting, a line at a time.

Highlighting a line at a time means any range of a file can be shown with its own line
numbers and lines picked out. Each file is highlighted once, and again only once it's
changed.
"""

from __future__ import annotations

import html
import re
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


def highlight_fixed(key: str, text: str, suffix: str) -> list[str]:
    """A file that never changes, as it was at a commit, highlighted once.

    Parameters
    ----------
    key : str
        What it is, such as its commit and path; it's cached under this for good.
    text : str
        Its text.
    suffix : str
        Its file's suffix, which picks the lexer.

    Returns
    -------
    list of str
        One string of HTML per line.
    """
    cached = _cache.get(key)
    if cached is None:
        cached = (0.0, _lines(text, _LEXERS.get(suffix, TextLexer())))
        _cache[key] = cached
    return cached[1]


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


TYPE = re.compile(r"[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*")
CONSTANT = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*")


# r[impl embed.names]
def _named(tokens, lexer):
    """The lexer's tokens, with a plain name coloured by how it's written: a CamelCase one
    as a type, an enum's variant included, and an UPPER_CASE one as a constant.

    The lexers mark a type only where one is expected ([[f:pygments.names]]).
    """
    if not isinstance(lexer, RustLexer | PythonLexer):
        yield from tokens
        return
    for ttype, value in tokens:
        if ttype is Token.Name:
            if TYPE.fullmatch(value):
                ttype = Token.Name.Class
            elif len(value) > 1 and CONSTANT.fullmatch(value):
                ttype = Token.Name.Constant
        yield ttype, value


def _lines(text: str, lexer) -> list[str]:
    lines: list[list[str]] = [[]]
    for ttype, value in _named(lex(text, lexer), lexer):
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
