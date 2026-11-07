"""What a codewalk can refer to: every item in the source, and every requirement in the spec.

The source is Rust or Python, found with tree-sitter. Rust is indexed here; Python in
`python.py`.

A symbol's qualified name is its module path from the file it's in, then its own name,
then, for what's inside an item, the inner name: `v2::battery::controller::
BatteryController::on_site_load`, `v2::fleet::BatteryUpdate::Short`. A reference can use
any tail of that on `::` boundaries (`BatteryController::on_site_load`), and it resolves
if exactly one symbol ends that way.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import tree_sitter_rust
from pydantic import BaseModel
from tree_sitter import Language, Node, Parser

from codewalk.spec import tracey

RUST = Language(tree_sitter_rust.language())

# Item node types, and the kind each is shown as
ITEM_KINDS = {
    "function_item": "fn",
    "function_signature_item": "fn",
    "struct_item": "struct",
    "enum_item": "enum",
    "union_item": "union",
    "trait_item": "trait",
    "const_item": "const",
    "static_item": "static",
    "type_item": "type",
    "mod_item": "mod",
    "macro_definition": "macro",
}


class Symbol(BaseModel):
    """One thing a codewalk can point at."""

    qualified: str
    kind: str
    file: str
    # 1-based, inclusive. `start` takes in its doc comments, attributes and markers
    start: int
    line: int
    end: int
    signature: str
    doc: str
    # Requirement markers on it, `impl` or `verify`, with their IDs and the versions they
    # name, 1 without a suffix
    markers: list[tuple[str, str, int]] = []
    # The rest of its documentation after the summary: for Python, a NumPy-style
    # docstring's extended summary and sections (Parameters, Returns, …)
    details: str = ""
    # What `sig` shows, as runs of lines (1-based, inclusive), if more than its doc
    # comments and first line: for Python, a def's header and docstring; a class's, with
    # its fields and its `__init__`'s header and docstring
    outline: list[tuple[int, int]] = []

    @property
    def name(self) -> str:
        return self.qualified.rsplit("::", 1)[-1]

    @property
    def segments(self) -> list[str]:
        return self.qualified.split("::")

    def text(self, files: SourceFiles) -> str:
        return "\n".join(files.lines(self.file)[self.start - 1 : self.end])

    def digest(self, files: SourceFiles) -> str:
        return hashlib.sha256(self.text(files).encode()).hexdigest()[:12]


class SourceFiles:
    """The source files, read once each, and read again only once they've changed.

    Parameters
    ----------
    root : Path
        The repository's root, which the files' paths are from.
    """

    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, tuple[float, list[str]]] = {}

    def lines(self, rel: str) -> list[str]:
        path = self.root / rel
        mtime = path.stat().st_mtime
        cached = self._cache.get(rel)
        if cached and cached[0] == mtime:
            return cached[1]
        lines = path.read_text().split("\n")
        self._cache[rel] = (mtime, lines)
        return lines


MARKER = re.compile(rf"(?://|#)\s*([a-z][a-z0-9]*)\[(impl|verify)\s+({tracey.ID}){tracey.VERSION}\]")


def module_path(rel: str) -> list[str]:
    """A Rust file's module path, as `::` segments.

    `src/v2/battery/controller/mod.rs` is `v2::battery::controller`; `src/lib.rs` is the
    crate root.

    Parameters
    ----------
    rel : str
        The file, from the root.

    Returns
    -------
    list of str
        The segments; empty for the crate root.
    """
    parts = Path(rel).with_suffix("").parts
    if parts and parts[0] == "src":
        parts = parts[1:]
    parts = list(parts)
    if parts and parts[-1] in ("mod", "lib", "main"):
        parts = parts[:-1]
    return parts


def _text(node: Node | None, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode() if node else ""


def _leading(node: Node, siblings: list[Node]) -> list[Node]:
    """The comments and attributes directly above `node`, with no blank line between.

    `siblings` are its parent's children. They're in order, first to last: its span starts
    at the first. Found by position, not `prev_sibling`, which crashes this version of
    tree-sitter.

    Parameters
    ----------
    node : Node
        The item.
    siblings : list of Node
        Its parent's children, unnamed ones included.

    Returns
    -------
    list of Node
        The comments and attributes, first to last; a `//!` comment stops them.
    """
    i = next(k for k, s in enumerate(siblings) if s.start_byte == node.start_byte and s.type == node.type)
    above: list[Node] = []
    top_row = node.start_point.row
    for prev in reversed(siblings[:i]):
        if prev.type not in ("line_comment", "block_comment", "attribute_item"):
            break
        # A line comment's span takes in its newline, so it ends at column 0 of the next row
        end_row = prev.end_point.row - (1 if prev.end_point.column == 0 else 0)
        if end_row < top_row - 1:
            break
        if prev.type == "line_comment" and (prev.text or b"").startswith(b"//!"):
            break
        above.append(prev)
        top_row = prev.start_point.row
    above.reverse()
    return above


def _doc(above: list[Node], source: bytes) -> tuple[str, list[tuple[str, str, int]]]:
    """The `///` doc text and the requirement markers in the comments above an item."""
    doc, markers = [], []
    for n in above:
        if n.type != "line_comment":
            continue
        t = _text(n, source)
        if t.startswith("///"):
            doc.append(t[3:].strip())
        for m in MARKER.finditer(t):
            markers.append((m.group(2), tracey.key(m.group(1), m.group(3)), int(m.group(4) or 1)))
    return " ".join(doc).strip(), markers


def _signature(node: Node, source: bytes) -> str:
    body = node.child_by_field_name("body")
    end = body.start_byte if body is not None else node.end_byte
    sig = source[node.start_byte : end].decode().strip()
    return re.sub(r"\s+", " ", sig)


def _base_type(text: str) -> str:
    """A type's bare name: `Dispatch<S>` is `Dispatch`; `&'a crate::x::Foo` is `Foo`."""
    names = re.findall(r"[A-Za-z_]\w*", text.split("<", 1)[0])
    names = [n for n in names if n not in ("mut", "dyn", "impl")]
    return names[-1] if names else ""


# r[impl index.languages]
# r[impl index.start]
def index_file(rel: str, source: bytes, parser: Parser) -> list[Symbol]:
    tree = parser.parse(source)
    out: list[Symbol] = []

    def add(node: Node, siblings: list[Node], qualified: list[str], kind: str, signature: str | None = None):
        above = _leading(node, siblings)
        doc, markers = _doc(above, source)
        first = above[0] if above else node
        out.append(
            Symbol(
                qualified="::".join(qualified),
                kind=kind,
                file=rel,
                start=first.start_point.row + 1,
                line=node.start_point.row + 1,
                end=node.end_point.row + 1,
                signature=signature if signature is not None else _signature(node, source),
                doc=doc,
                markers=markers,
            )
        )

    def walk(container: Node, scope: list[str]):
        siblings = list(container.children)
        for node in container.named_children:
            t = node.type
            if t in ITEM_KINDS:
                name = _text(node.child_by_field_name("name"), source)
                if not name:
                    continue
                here = scope + [name]
                add(node, siblings, here, ITEM_KINDS[t])
                body = node.child_by_field_name("body")
                if t == "mod_item" and body is not None:
                    walk(body, here)
                elif t == "trait_item" and body is not None:
                    walk(body, here)
                elif t == "enum_item" and body is not None:
                    variants = list(body.children)
                    for v in body.named_children:
                        if v.type == "enum_variant":
                            vname = _text(v.child_by_field_name("name"), source)
                            add(v, variants, here + [vname], "variant", _text(v, source).split("{")[0].strip())
                elif t == "struct_item" and body is not None and body.type == "field_declaration_list":
                    fields = list(body.children)
                    for f in body.named_children:
                        if f.type == "field_declaration":
                            fname = _text(f.child_by_field_name("name"), source)
                            add(f, fields, here + [fname], "field", re.sub(r"\s+", " ", _text(f, source)))
            elif t == "impl_item":
                ty = _base_type(_text(node.child_by_field_name("type"), source))
                trait = _text(node.child_by_field_name("trait"), source)
                body = node.child_by_field_name("body")
                if body is None or not ty:
                    continue
                label = f"impl {trait} for {ty}" if trait else f"impl {ty}"
                add(node, siblings, scope + [ty, f"<{label}>"], "impl")
                walk(body, scope + [ty])

    walk(tree.root_node, module_path(rel))
    # A method in `impl Trait for Type` shouldn't shadow the impl's own entry
    return [s for s in out if not s.qualified.endswith(">") or s.kind == "impl"]


class Trace(BaseModel):
    """A requirement marker in the code, `r[impl id]` or `r[verify id]`, and the symbol it's in or on.

    This is for finding the code a requirement is about; whether every requirement is
    implemented and verified is tracey's to say, not codewalk's.
    """

    kind: str
    requirement: str
    # The version of the requirement it names, `+N` after the ID; 1 without
    version: int = 1
    file: str
    line: int
    symbol: Symbol | None = None


def _loose(text: str) -> str:
    return re.sub(r"[_:]+", " ", text)


class CodeIndex:
    """Every symbol in the source files under `globs`, rebuilt when a file changes.

    Parameters
    ----------
    root : Path
        The repository's root.
    globs : list of str
        The source files, from the root: `.rs` and `.py` files are indexed.
    """

    def __init__(self, root: Path, globs: list[str]):
        self.root = root
        self.globs = globs
        self.files = SourceFiles(root)
        from codewalk.code import python

        self.parsers = {
            ".rs": (Parser(RUST), index_file),
            ".py": (python.parser(), lambda rel, source, parser: python.index_file(rel, source, parser, root)),
        }
        self._by_file: dict[str, tuple[float, list[Symbol]]] = {}
        self.symbols: list[Symbol] = []
        self._traces: dict[str, list[Trace]] | None = None
        self.refresh()

    def paths(self) -> list[Path]:
        seen = []
        for g in self.globs:
            seen.extend(p for p in self.root.glob(g) if p.is_file() and p.suffix in self.parsers)
        return sorted(set(seen))

    def refresh(self) -> bool:
        """Re-read changed files.

        Returns
        -------
        bool
            Whether anything changed, a file added or gone included.
        """
        changed = False
        current = {}
        for p in self.paths():
            rel = str(p.relative_to(self.root))
            mtime = p.stat().st_mtime
            cached = self._by_file.get(rel)
            if cached and cached[0] == mtime:
                current[rel] = cached
                continue
            parser, index = self.parsers[p.suffix]
            current[rel] = (mtime, index(rel, p.read_bytes(), parser))
            changed = True
        if set(current) != set(self._by_file):
            changed = True
        self._by_file = current
        if changed:
            self.symbols = [s for _, syms in current.values() for s in syms]
            self._traces = None
        return changed

    # r[impl spec.traces+2]
    def traces(self) -> dict[str, list[Trace]]:
        """For each requirement ID, the markers that name it, in file and line order.

        Returns
        -------
        dict of str to list of Trace
            By requirement ID; each with the smallest symbol around it, if any.
        """
        if self._traces is None:
            out: dict[str, list[Trace]] = {}
            for rel, (_, syms) in sorted(self._by_file.items()):
                spans = [s for s in syms if s.kind not in ("impl", "field")]
                for n, line in enumerate(self.files.lines(rel), start=1):
                    if "[" not in line:
                        continue
                    for m in MARKER.finditer(line):
                        around = [s for s in spans if s.start <= n <= s.end]
                        sym = min(around, key=lambda s: s.end - s.start, default=None)
                        rid = tracey.key(m.group(1), m.group(3))
                        version = int(m.group(4) or 1)
                        trace = Trace(kind=m.group(2), requirement=rid, version=version, file=rel, line=n, symbol=sym)
                        out.setdefault(rid, []).append(trace)
            self._traces = out
        return self._traces

    def in_file(self, rel: str) -> list[Symbol]:
        return self._by_file.get(rel, (0, []))[1]

    # r[impl ref.tail]
    # r[impl ref.ambiguous]
    # r[impl ref.crate]
    def resolve(self, ref: str) -> tuple[Symbol | None, list[Symbol]]:
        """The one symbol `ref` names, or None and the candidates.

        The candidates are several if it's ambiguous, the nearest few if there's none.

        `ref` is a tail of a qualified name (`BatteryController::on_site_load`), or a file
        and a name inside it (`src/v2/fleet.rs#BatteryUpdate::Short`).

        Parameters
        ----------
        ref : str
            The reference, as written.

        Returns
        -------
        symbol : Symbol or None
            The symbol, if exactly one matches.
        candidates : list of Symbol
            Empty if it resolved; else the matches, or the nearest names.
        """
        file = None
        if "#" in ref:
            file, ref = ref.split("#", 1)
        # A file is its path from the root, or any tail of it: `lib.rs`, `controller/mod.rs`
        pool = (
            [s for rel, (_, syms) in self._by_file.items() if rel == file or rel.endswith("/" + file) for s in syms]
            if file
            else self.symbols
        )
        if ref.startswith("impl "):
            return self._resolve_impl(ref, pool)
        # `crate::` anchors it at the root: the whole qualified name, not a tail of it
        anchored = ref.startswith("crate::")
        want = ref.removeprefix("crate::").split("::")
        hits = [s for s in pool if s.kind != "impl" and (s.segments == want if anchored else s.segments[-len(want) :] == want)]
        # A method and a field can share a name: the method is what's meant, unless the
        # reference says `field:`
        items = [s for s in hits if s.kind not in ("field",)]
        if len(hits) > 1 and len(items) == 1:
            return items[0], []
        if len(hits) == 1:
            return hits[0], []
        if len(hits) > 1:
            return None, hits
        return None, self.nearest(ref)

    def _resolve_impl(self, ref: str, pool: list[Symbol]) -> tuple[Symbol | None, list[Symbol]]:
        """An impl block, named by its type, as far qualified as it needs to be.

        `impl Site`, `impl ercot_ers_strict::Site` or `impl ProgramRules for ErcotErsStrict`.

        Parameters
        ----------
        ref : str
            The reference, starting `impl `.
        pool : list of Symbol
            The symbols to look in.

        Returns
        -------
        symbol : Symbol or None
            The impl block, if exactly one matches.
        candidates : list of Symbol
            Empty if it resolved; else the matches, or up to five impls of the type.
        """
        body = ref[len("impl ") :].strip()
        trait, _, ty = body.rpartition(" for ")
        anchored = ty.startswith("crate::")
        path = ty.removeprefix("crate::").split("::")
        label = f"<impl {trait.split('::')[-1]} for {path[-1]}>" if trait else f"<impl {path[-1]}>"
        want = path + [label]
        hits = [s for s in pool if s.kind == "impl" and (s.segments == want if anchored else s.segments[-len(want) :] == want)]
        if len(hits) == 1:
            return hits[0], []
        if hits:
            return None, hits
        return None, [s for s in pool if s.kind == "impl" and s.segments[-2] == path[-1]][:5]

    # r[impl ui.context]
    def named_at(self, name: str, file: str, line: int) -> Symbol | None:
        """The symbol a name in the code most likely means, from where it's written.

        A name is only a name, not a path, so it's taken to mean one in the same file if
        there is one (the innermost around `line`, else the first), else the one symbol
        anywhere with that name.

        Parameters
        ----------
        name : str
            The name, as it is in the code.
        file : str
            The file it's in.
        line : int
            The line it's on.

        Returns
        -------
        Symbol or None
            None if no symbol has that name, or several in other files do.
        """
        found = [s for s in self.symbols if s.name == name and s.kind != "impl"]
        here = [s for s in found if s.file == file]
        if here:
            # Not the one it's written in, unless that's all there is
            others = [s for s in here if not (s.start <= line <= s.end)] or here
            return min(others, key=lambda s: abs(s.line - line))
        return found[0] if len(found) == 1 else None

    # r[impl ref.nearest]
    def nearest(self, ref: str, n: int = 5) -> list[Symbol]:
        """The symbols `ref` most likely meant.

        Names close to its last part, best first by how closely the whole of it matches the
        end of theirs.

        Parameters
        ----------
        ref : str
            The reference that didn't resolve.
        n : int
            How many to return, at most.

        Returns
        -------
        list of Symbol
            Best first.
        """
        from difflib import SequenceMatcher, get_close_matches

        want = ref.split("::")
        tail = want[-1]
        pool = [s for s in self.symbols if s.kind != "impl"]
        close = set(get_close_matches(tail, list({s.name for s in pool}), n=25, cutoff=0.6))

        def score(s: Symbol) -> float:
            name = SequenceMatcher(None, tail.lower(), s.name.lower()).ratio()
            whole = SequenceMatcher(None, ref.lower(), "::".join(s.segments[-len(want) :]).lower()).ratio()
            return name + whole

        return sorted((s for s in pool if s.name in close), key=score, reverse=True)[:n]

    def search(self, query: str, limit: int = 30) -> list[Symbol]:
        """Symbols matching `query`, best first.

        The name starting with it, then containing it, then the qualified name containing it.

        Parameters
        ----------
        query : str
            What to look for, ignoring case.
        limit : int
            How many to return, at most.

        Returns
        -------
        list of Symbol
            Best first; impl blocks left out.
        """
        q = query.strip().lower()
        words = _loose(q).split()
        scored = []
        for s in self.symbols:
            if s.kind == "impl":
                continue
            name, qual = s.name.lower(), s.qualified.lower()
            if name == q:
                score = 0
            elif name.startswith(q):
                score = 1
            elif q in name:
                score = 2
            elif q in qual:
                score = 3
            elif words and all(w in loose for w in words if (loose := _loose(qual))):
                # Words in any order, ignoring case and `_`: "target below" finds
                # TARGET_BELOW_CEILING, "strict hold" finds ercot_ers_strict::HOLD.
                score = 4
            else:
                continue
            scored.append((score, len(s.qualified), s.qualified, s))
        scored.sort(key=lambda x: x[:3])
        return [s for *_, s in scored[:limit]]

    def shortest_unique(self, sym: Symbol) -> str:
        """The shortest tail of its qualified name that names only it.

        A method, field or variant keeps its owner (`Dispatch::on_short`, not `on_short`) so
        it reads well where it's written; an impl block is `impl` and its type.

        Parameters
        ----------
        sym : Symbol
            The symbol.

        Returns
        -------
        str
            The reference to write; its qualified name if no shorter tail is unique.
        """
        segs = sym.segments
        if sym.kind == "impl":
            label = segs[-1][1:-1]  # "impl Trait for Type" or "impl Type"
            trait = label[len("impl ") :].rpartition(" for ")[0]
            path = segs[:-1]
            for k in range(1, len(path) + 1):
                tail = path[-k:] + [segs[-1]]
                if sum(1 for s in self.symbols if s.kind == "impl" and s.segments[-len(tail) :] == tail) == 1:
                    return f"impl {trait + ' for ' if trait else ''}{'::'.join(path[-k:])}"
            return f"impl {trait + ' for ' if trait else ''}{'::'.join(path)}"
        member = len(segs) > 1 and segs[-2][:1].isupper()
        for k in range(2 if member else 1, len(segs) + 1):
            tail = segs[-k:]
            if sum(1 for s in self.symbols if s.kind != "impl" and s.segments[-k:] == tail) == 1:
                return "::".join(tail)
        return sym.qualified


# r[impl ref.focus]
def narrow(sym: Symbol, focus: str, files: SourceFiles) -> Symbol | None:
    """The part of `sym` that starts at the first line containing `focus`.

    It takes in the comments directly above that line, through the end of the block the line
    opens (or the line itself, if it opens none). None if no line contains it.

    Parameters
    ----------
    sym : Symbol
        The symbol to narrow.
    focus : str
        Text on the line to start at.
    files : SourceFiles
        The source files.

    Returns
    -------
    Symbol or None
        A copy of `sym` over just that part, its first line as the signature and no doc;
        None if no line contains `focus`.
    """
    lines = files.lines(sym.file)
    first = next((n for n in range(sym.line, sym.end + 1) if focus in lines[n - 1]), None)
    if first is None:
        return None
    top = first
    while top - 1 > sym.start and lines[top - 2].strip().startswith(("//", "#")):
        top -= 1
    if sym.file.endswith(".py"):
        from codewalk.code.python import block_end

        return sym.model_copy(
            update={"start": top, "line": first, "end": block_end(lines, first, sym.end), "signature": lines[first - 1].strip(), "doc": ""}
        )
    depth, last = 0, first
    for n in range(first, sym.end + 1):
        code = lines[n - 1].split("//", 1)[0]
        opened = depth > 0 or "{" in code or "(" in code
        depth += code.count("{") + code.count("(") - code.count("}") - code.count(")")
        last = n
        if not opened or depth <= 0:
            break
    first_line = lines[first - 1].strip()
    return sym.model_copy(update={"start": top, "line": first, "end": last, "signature": first_line, "doc": ""})
