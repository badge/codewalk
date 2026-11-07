"""Python's symbols, found with tree-sitter.

That's functions, classes, methods, the functions inside functions, and names assigned at
the top of a module or class.

A Python symbol's qualified name is built like a Rust one, from its file's path, with
`::` between: `codewalk::doc::Walk::render`, `codewalk::doc::Walk::render::embed`. So a
reference to one reads the same as a reference to Rust (`Walk::render`).
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import tree_sitter_python
from tree_sitter import Language, Node, Parser

from codewalk.code.index import MARKER, Symbol
from codewalk.spec import tracey

PYTHON = Language(tree_sitter_python.language())


def parser() -> Parser:
    return Parser(PYTHON)


# r[impl index.python-path]
def module_path(rel: str, root: Path | None = None) -> list[str]:
    """A file's dotted module name, as `::` segments.

    `codewalk/doc.py`, in a package `codewalk` (a folder with an `__init__.py`), is
    `codewalk::doc`, wherever the package sits. A file outside any package is its path from
    the root.

    Parameters
    ----------
    rel : str
        The file, from the root.
    root : Path or None
        The root; without it, the file is taken to be outside any package.

    Returns
    -------
    list of str
        The segments, without `__init__`.
    """
    path = Path(rel).with_suffix("")
    folder = (root / rel).parent if root else None
    if folder is None or not (folder / "__init__.py").exists():
        return [p for p in path.parts if p != "__init__"]
    parts = [] if path.name == "__init__" else [path.name]
    while folder != root and (folder / "__init__.py").exists():
        parts.insert(0, folder.name)
        folder = folder.parent
    return parts


def _text(node: Node | None, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode() if node else ""


def _comments_above(node: Node, siblings: list[Node]) -> list[Node]:
    """The `#` comments directly above `node`, with no blank line between."""
    i = next(k for k, s in enumerate(siblings) if s.start_byte == node.start_byte)
    above: list[Node] = []
    top = node.start_point.row
    for prev in reversed(siblings[:i]):
        if prev.type != "comment" or prev.end_point.row < top - 1:
            break
        above.append(prev)
        top = prev.start_point.row
    return list(reversed(above))


def _docstring(definition: Node, source: bytes) -> tuple[str, str]:
    """A function's or class's docstring, NumPy style.

    Returns
    -------
    summary : str
        Its first paragraph, on one line.
    details : str
        The rest, dedented: the extended summary and the sections (Parameters, Returns,
        Raises, …), as written.
    """
    body = definition.child_by_field_name("body")
    if body is None or not body.named_children:
        return "", ""
    first = body.named_children[0]
    if first.type != "expression_statement" or not first.named_children or first.named_children[0].type != "string":
        return "", ""
    raw = _text(first.named_children[0], source)
    text = re.sub(r'^[rbuf]*("""|\'\'\'|"|\')|("""|\'\'\'|"|\')$', "", raw).strip("\n")
    summary, _, rest = text.strip().partition("\n\n")
    return re.sub(r"\s+", " ", summary), textwrap.dedent("\n" + rest).strip("\n") if rest else ""


def _signature(definition: Node, source: bytes) -> str:
    body = definition.child_by_field_name("body")
    end = body.start_byte if body is not None else definition.end_byte
    return re.sub(r"\s+", " ", source[definition.start_byte : end].decode().strip())


def _head(definition: Node) -> int:
    """The last row (0-based) of a definition's header and docstring."""
    body = definition.child_by_field_name("body")
    if body is None:
        return definition.end_point.row
    end = max(definition.start_point.row, body.start_point.row - 1)
    first = body.named_children[0] if body.named_children else None
    if first is not None and first.type == "expression_statement" and first.named_children and first.named_children[0].type == "string":
        end = first.end_point.row
    return end


# r[impl ref.sig]
def _outline(outer: Node, inner: Node, start: int) -> list[tuple[int, int]]:
    """What `sig` shows of a definition: its header and docstring and, for a class, its
    fields and its `__init__`'s header and docstring.

    Parameters
    ----------
    outer : Node
        The definition with its decorators.
    inner : Node
        The definition itself.
    start : int
        Its first line, 1-based, taking in the comments above it.

    Returns
    -------
    list of tuple of (int, int)
        Runs of lines, 1-based and inclusive, in order, with runs that touch joined.
    """
    runs = [(start, _head(inner) + 1)]
    body = inner.child_by_field_name("body")
    if inner.type == "class_definition" and body is not None:
        kids = list(body.named_children)
        for i, node in enumerate(kids):
            d = node.child_by_field_name("definition") if node.type == "decorated_definition" else node
            if d is None:
                continue
            top = node.start_point.row
            # Comments directly above it go with it
            k = i - 1
            while k >= 0 and kids[k].type == "comment" and kids[k].end_point.row >= top - 1:
                top = kids[k].start_point.row
                k -= 1
            if d.type == "expression_statement" and d.named_children and d.named_children[0].type == "assignment":
                runs.append((top + 1, node.end_point.row + 1))
            elif d.type == "function_definition" and d.child_by_field_name("name") and d.child_by_field_name("name").text == b"__init__":
                runs.append((top + 1, _head(d) + 1))
    out: list[tuple[int, int]] = []
    for a, b in sorted(runs):
        if out and a <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


# r[impl index.languages]
# r[impl index.start]
def index_file(rel: str, source: bytes, parser: Parser, root: Path | None = None) -> list[Symbol]:
    tree = parser.parse(source)
    out: list[Symbol] = []

    def add(outer: Node, inner: Node, siblings: list[Node], qualified: list[str], kind: str, signature: str, doc: tuple[str, str]):
        # `outer` takes in any decorators; `inner` is the definition itself
        above = _comments_above(outer, siblings)
        markers = [(m[2], tracey.key(m[1], m[3]), int(m[4] or 1)) for n in above for m in MARKER.finditer(_text(n, source))]
        start = (above[0] if above else outer).start_point.row + 1
        defines = inner.type in ("function_definition", "class_definition")
        out.append(
            Symbol(
                qualified="::".join(qualified),
                kind=kind,
                file=rel,
                outline=_outline(outer, inner, start) if defines else [],
                start=start,
                line=inner.start_point.row + 1,
                end=outer.end_point.row + 1,
                signature=signature,
                doc=doc[0],
                details=doc[1],
                markers=markers,
            )
        )

    def walk(container: Node, scope: list[str], in_class: bool, top: bool):
        siblings = list(container.named_children)
        for node in siblings:
            inner = node.child_by_field_name("definition") if node.type == "decorated_definition" else node
            if inner is None:
                continue
            if inner.type in ("function_definition", "class_definition"):
                name = _text(inner.child_by_field_name("name"), source)
                kind = "class" if inner.type == "class_definition" else ("method" if in_class else "def")
                here = scope + [name]
                add(node, inner, siblings, here, kind, _signature(inner, source), _docstring(inner, source))
                body = inner.child_by_field_name("body")
                if body is not None:
                    walk(body, here, inner.type == "class_definition", False)
            elif (top or in_class) and inner.type == "expression_statement" and inner.named_children:
                assign = inner.named_children[0]
                left = assign.child_by_field_name("left") if assign.type == "assignment" else None
                if left is not None and left.type == "identifier":
                    name = _text(left, source)
                    kind = "const" if name.isupper() else ("field" if in_class else "var")
                    line = _text(inner, source).split("\n")[0]
                    add(node, inner, siblings, scope + [name], kind, line, ("", ""))

    walk(tree.root_node, module_path(rel, root), False, True)
    return out


def block_end(lines: list[str], first: int, last: int) -> int:
    """Where the block that line `first` opens ends, by indentation.

    It's the last line, up to `last`, indented further than it, past any brackets left open.

    Parameters
    ----------
    lines : list of str
        The file's lines.
    first, last : int
        The line that opens the block, and the last it can reach; 1-based.

    Returns
    -------
    int
        The block's last line, 1-based; `first` if nothing is indented under it.
    """
    base = len(lines[first - 1]) - len(lines[first - 1].lstrip())
    depth = 0
    end = first
    for n in range(first, last + 1):
        line = lines[n - 1]
        code = line.split("#", 1)[0]
        if n > first and line.strip() and depth <= 0 and len(line) - len(line.lstrip()) <= base:
            break
        depth += sum(code.count(c) for c in "([{") - sum(code.count(c) for c in ")]}")
        if line.strip():
            end = n
    return end
