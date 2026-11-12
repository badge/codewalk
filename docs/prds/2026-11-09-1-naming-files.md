---
title: "Files by name, and docs as prose"
summary: "A source file is a symbol of its own, named by its module or its path; and an excerpt's doc comments and docstrings read as prose, with their lines as written a click away."
kind: prd
stage: work
tags: [index, references, ui]
related: ["../codewalk.md"]
---

# Files by name, and docs as prose

## The problem

**A codewalk can't name a file.** It can name a function, a type or a field, but the
nearest it gets to a file is a Rust module, as the line that declares it:

```walk
codewalk::code::index::index_file > if t == "mod_item" and body is not None:
```

A `mod storing;` is indexed like any other item, so `[[core::storing]]` resolves, but to
the one line `mod storing;` in `core/mod.rs`: no docs on hover, and a click lands on the
declaration, not the file. Its docs are in the file, as `//!` comments, which nothing
reads. A Python module isn't a symbol at all. And a file's path, which is how people
usually write about one (`store/encode.rs`), is only a name inside a reference
(`store/encode.rs#terms_json`), never a reference on its own.

So a codewalk that says where something lives writes the path in backticks, unlinked. The
ancillaries service's database codewalk has a table of layers, with a column saying where
each is: the core is `core/dispatching.rs` and `core/storing.rs`, and the encoding
`store/encode.rs`. They're the obvious things to link, and the nearest it can do is name
a handful of the functions in each.

**Docs in an excerpt read as code.** An excerpt shows every line as it's written, so a
symbol's docs are shown as comments: `///` down the left of every line, Markdown as its
raw characters, and code examples as comment text, grey and unhighlighted. It's right,
but it's hard to read, and it's most of what `sig` shows. The ancillaries service's
`BatteryState sig`, in its batteries codewalk, is 70 lines of `///`, most of them four
code examples. A Python docstring is the same, in the string's colour.

```walk
Renderer::embed > # Shown without the indent
```

## What we want

### Files

Every source file codewalk indexes is a symbol of its own, of kind `file`, spanning the
whole file. Its qualified name is its module's: `core::storing` for
`src/core/storing.rs`, `codewalk::code::index` for `codewalk/code/index.py`. Its docs are
its module docs: a Rust file's `//!` comments at the top, a Python file's docstring. A
Rust module declared in a file of its own (`mod storing;`) isn't indexed as its own
symbol any more: the file stands for it, so `[[core::storing]]` names the file, with its
docs. A module written inline, `mod tests { … }`, is still the item it was. A crate's root
(`src/lib.rs`, `src/main.rs`) has no module path, so it's named by its path only.

A file can also be named by its path, or any tail of it on `/` boundaries:
`[[store/encode.rs]]`, `[[encode.rs]]`, or `[the encoding](walk:store/encode.rs)`. A name
never has a `/` or a `.` in it, so a reference with either, and no `#`, is a path. A tail
that ends more than one file's path is ambiguous, as a name is. A file and an item in it
can share a name (Python's `render` module and its `render` function): the item is meant,
as a method is over a field of the same name, and the file is named by more of its module
path, or by its path.

Everything else follows from its being a symbol. An inline reference shows the module
docs on hover and opens the file at its top on click. Review records its digest like any
other. A requirement marker outside every item, which belonged to no symbol, now belongs
to its file. In a `walk` block, `> text` shows the block from the first line with `text`
in it, as for any symbol, and `sig` shows its module docs. A whole file in a `walk` block
is shown, but it's a warning: a file is linked inline, or shown in part.

### Docs as prose

In an excerpt, each run of docs is shown as what it says, in the prose font, in one row
beside the code, indented as the docs are:

- **Rust's doc comments** (`///` and `//!`) are Markdown, as rustdoc reads them. Code
  blocks are highlighted, as Rust unless their info string names another language, with
  their rustdoc attributes (`no_run`, `compile_fail, E0616`) as a label and without the
  lines rustdoc hides (`# use …`). An intra-doc link, ``[`BatteryState::update_battery`]``
  or `[text](Self::update)`, links to the symbol it names, as an inline reference does,
  with `Self` read as the type the docs are on or in; one codewalk can't find (another
  crate's type, say) is plain code.
- **A Python docstring** is read as NumPy style. Its text is Markdown, and its section
  headings (`Parameters` over a line of dashes) are headings. In a section that lists
  names or types (Parameters, Other Parameters, Attributes, Returns, Yields, Receives,
  Raises, Warns), each entry is its first line, `name : type`, shown as the name and
  the type, both as code (the name in bold), with its description, the indented lines
  below, as Markdown. In Returns, Yields, Raises and the like, a line with no ` : ` is a
  type. An Examples section that's a Python session (`>>>`) is highlighted as one.

The lines as written are a click away: **as written** in the caption swaps every run in
that excerpt back to its lines, with their numbers, and **as prose** swaps them back.
Review, diffs and drafts are unchanged: they're about the code as written. So is the
context panel, which shows the whole file as it is.

`SYNTAX.md` gains the path form of a name, and the data model the `file` kind.

## The spec

r[index.languages+2]
The source files matched by the `sources` globs MUST be indexed: `.rs` files for Rust's
functions, types, traits, impls, inline modules and consts, and `.py` files for Python's
functions, classes, methods and the names assigned at the top level of a module or class.

r[index.files]
Each indexed file MUST itself be indexed as a symbol of kind `file`, spanning the whole
file, whose qualified name is its module path (a Rust file's from `src`, a Python file's
as `index.python-path` gives it) and whose docs are its module docs: a Rust file's
leading `//!` comments, or a Python file's docstring. A crate's root, which has no module
path, MUST be named by its path only. A Rust module declared without a body MUST NOT also
be indexed as a symbol of its own.

r[ref.file]
A reference with a `/` or a `.` in it and no `#` MUST be read as a file's path, and MUST
resolve to the one indexed file whose path from the root is it or ends with it on `/`
boundaries. One that ends more than one file's path MUST NOT resolve, and MUST be
reported with each file as a candidate. A name that ends both a file's qualified name and
one item's MUST resolve to the item.

r[ref.sig+2]
A line of a `walk` block ending ` sig` MUST show only the symbol's outline: for Rust, its
doc comments and first line; for Python, its header and docstring and, for a class, its
fields and its `__init__`'s header and docstring; for a file, its module docs.

r[check.whole-file]
A line of a `walk` block that shows a whole file, with neither ` sig` nor `> text`, MUST
be reported as a warning.

r[embed.docs]
In an excerpt, each run of Rust doc comments MUST be shown as one row of its text
rendered as Markdown, its code blocks highlighted (as Rust unless they name another
language, without the lines rustdoc hides) and each intra-doc link that names a symbol
linked to it as an inline reference is; and each Python docstring as one row, read as
NumPy style: its text and each entry's description rendered as Markdown, and each entry
in a section listing names or types shown as its name and its type, both as code. An
excerpt with docs MUST offer to show them as written instead, with their line numbers.

## The code

### Files

A file's symbol is made where the rest of its symbols are, by each language's
`index_file`, since only the language knows where its module docs are, and the same way
in both:

```walk settled python
codewalk::code::index::file_symbol
def file_symbol(rel: str, qualified: list[str], length: int, doc: tuple[str, str], docs: tuple[int, int] | None) -> Symbol:
    """A file as a symbol of its own, spanning all of it.

    Parameters
    ----------
    rel : str
        The file, from the root.
    qualified : list of str
        Its module path; empty for a crate's root, which is named by its path only.
    length : int
        Its number of lines.
    doc : tuple of (str, str)
        Its module docs' summary and the rest.
    docs : tuple of (int, int) or None
        The lines its module docs are on, which are what `sig` shows; None if it has none.
    """
    return Symbol(
        qualified="::".join(qualified) or rel,
        kind="file",
        file=rel,
        start=1,
        line=1,
        end=length,
        signature=rel,
        doc=doc[0],
        details=doc[1],
        outline=[docs] if docs else [],
    )
```

Its outline is the lines of its module docs, so `sig` needs no change of its own. A
crate's root takes its path as its qualified name, which no name can match, since a name
has no `/` or `.` in it. In Rust, the module docs are the `//!` lines at the top, and a
bodiless `mod` is skipped:

```walk settled python
codewalk::code::index::index_file
# r[impl index.languages+2]
# r[impl index.files]
# r[impl index.start]
def index_file(rel: str, source: bytes, parser: Parser) -> list[Symbol]:
    tree = parser.parse(source)
    lines = source.decode().split("\n")
    # The module docs: the `//!` lines at the top, after any blank lines and `#![…]`
    docs: list[int] = []
    for n, line in enumerate(lines, start=1):
        text = line.strip()
        if text.startswith("//!"):
            docs.append(n)
        elif text and not text.startswith("#!") or docs and not text:
            break
    summary, _, rest = "\n".join(lines[n - 1].strip()[3:].removeprefix(" ") for n in docs).strip().partition("\n\n")
    out: list[Symbol] = [
        file_symbol(
            rel,
            module_path(rel),
            len(lines),
            (re.sub(r"\s+", " ", summary), rest.strip()),
            (docs[0], docs[-1]) if docs else None,
        )
    ]
    ...
    def walk(container: Node, scope: list[str]):
        siblings = list(container.children)
        for node in container.named_children:
            t = node.type
            # A module in a file of its own is that file
            if t == "mod_item" and node.child_by_field_name("body") is None:
                continue
            ...
```

In Python, from the module's docstring, which `_docstring` reads from a module as it does
from a definition:

```walk settled python
codewalk::code::python::index_file
# r[impl index.languages+2]
# r[impl index.files]
# r[impl index.start]
def index_file(rel: str, source: bytes, parser: Parser, root: Path | None = None) -> list[Symbol]:
    tree = parser.parse(source)
    module = tree.root_node
    first = module.named_children[0] if module.named_children else None
    doc = _docstring(module, source)
    docs = (first.start_point.row + 1, first.end_point.row + 1) if first is not None and doc[0] else None
    out: list[Symbol] = [file_symbol(rel, module_path(rel, root), source.count(b"\n") + 1, doc, docs)]
    ...
```

```walk settled python
codewalk::code::python::_docstring
def _docstring(definition: Node, source: bytes) -> tuple[str, str]:
    """A module's, function's or class's docstring, NumPy style. ..."""
    # A module's docstring is its first statement; a definition's, its body's
    body = definition if definition.type == "module" else definition.child_by_field_name("body")
    ...
```

A path is told from a name before anything else, and matched against the files rather
than the qualified names; and a file gives way to an item of the same name:

```walk settled python
CodeIndex::resolve
# r[impl ref.tail]
# r[impl ref.ambiguous]
# r[impl ref.crate]
# r[impl ref.file]
def resolve(self, ref: str) -> tuple[Symbol | None, list[Symbol]]:
    # A file, by its path or any tail of it: `store/encode.rs`, `index.py`
    if "#" not in ref and ("/" in ref or "." in ref):
        files = [s for s in self.symbols if s.kind == "file" and (s.file == ref or s.file.endswith("/" + ref))]
        if len(files) == 1:
            return files[0], []
        return None, files or self.nearest(ref.rsplit("/", 1)[-1].split(".")[0])
    ...
    items = [s for s in hits if s.kind not in ("field",)]
    if len(hits) > 1 and len(items) == 1:
        return items[0], []
    # So can a module's file and an item in it (`render` and `render::render`): the
    # item is meant, and the file is named by more of its module path, or its path
    items = [s for s in items if s.kind != "file"]
    if len(hits) > 1 and len(items) == 1:
        return items[0], []
    ...
```

The warning is one more problem a resolved excerpt can have:

```walk settled python
Walk::problems
# r[impl check.whole-file]
def problems(self) -> list[Problem]:
    ...
            if ref.symbol:
                if ref.kind == "embed" and ref.symbol.kind == "file" and not (ref.sig or ref.focus):
                    message = f"`{ref.target}` shows the whole file: link it inline, or show part of it with `sig` or `> text`"
                    out.append(Problem(severity="warning", line=ref.line, message=message, ref=ref.key))
    ...
```

### Docs as prose

A new module, `codewalk/web/docs.py`, finds the docs in a run of lines and renders them.
Finding them is by line: a Rust doc comment by its `///` or `//!`, a Python docstring by
the class Pygments already gives it (`sd`), which is what tells it from any other string:

```walk settled python
codewalk::web::docs::doc_runs
def doc_runs(lines: list[str], highlighted: list[str], suffix: str) -> list[tuple[int, int]]:
    """Where the docs are in a run of lines.

    Returns
    -------
    list of tuple of (int, int)
        Each run of docs, as the indices of its first and last lines.
    """
    runs: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if suffix == ".rs" and RUST_DOC.match(lines[i]):
            j = i
            while j + 1 < len(lines) and RUST_DOC.match(lines[j + 1]):
                j += 1
            runs.append((i, j))
            i = j + 1
        elif suffix == ".py" and (m := PY_DOC_OPEN.match(lines[i])) and 'class="sd"' in highlighted[i]:
            quote, j = m.group(1), i
            if lines[i].count(quote) < 2:
                j += 1
                while j < len(lines) and quote not in lines[j]:
                    j += 1
            runs.append((i, min(j, len(lines) - 1)))
            i = j + 1
        else:
            i += 1
    return runs
```

Rust docs are rendered with a markdown-it of their own, whose rules highlight a fence
(rustdoc's attributes mean Rust, and its hidden `# ` lines are dropped) and pass a link
whose target is a Rust path to a linker, which gives the opening tag of a link to the
symbol, or nothing if there's none. Intra-doc links with no target are given one first:

```walk settled python
codewalk::web::docs::rust_doc_html
def rust_doc_html(lines: list[str], link: Linker) -> str:
    """A run of Rust doc comments, as HTML."""
    text = "\n".join(RUST_DOC.sub("", line).removeprefix(" ") for line in lines)
    text = INTRA.sub(lambda m: f"[{m.group(0)[1:-1]}]({m.group(2)})", text)
    return _md.render(text, {"link": link, "closing": []})
```

A Python docstring is split at its section headings. The text before them, and any
section that isn't a list of entries, is Markdown, through the same markdown-it, with
Python as its code blocks' language. A list's entries are a `<dl>`: each unindented line
a head (`_head`: the name and the type as code, or a type alone in the sections that
list types), and the indented lines under it its description, dedented, as Markdown:

```walk settled python
codewalk::web::docs::python_doc_html
def python_doc_html(lines: list[str]) -> str:
    """A NumPy-style Python docstring, as HTML.

    Its text is Markdown. Each entry in a section that lists names or types (Parameters,
    Returns, Raises, …) is its name and its type, both as code, with its description below, as
    Markdown. An Examples section that's a Python session is highlighted as one.
    """
    raw = "\n".join(lines).strip()
    raw = re.sub(r"""^[rRuU]?("{3}|'{3})|("{3}|'{3})$""", "", raw)
    first, _, rest = raw.partition("\n")
    text = (first.strip() + "\n" + textwrap.dedent(rest)).strip("\n")
    parts = SECTION.split(text)
    out = [_markdown(parts[0])]
    for title, body in zip(parts[1::2], parts[2::2], strict=True):
        key = title.strip().lower()
        body = body.strip("\n")
        out.append(f'<div class="doc-h">{html.escape(title.strip())}</div>')
        if key in ENTRIES:
            out.append(_entries(body, key in TYPED))
        elif key == "examples" and ">>>" in body:
            out.append(_markdown(f"```pycon\n{body}\n```"))
        else:
            out.append(_markdown(body))
    return "".join(out)
```

The renderer builds an excerpt's rows from these, instead of a row a line in `embed`.
A row now has a kind as well as a line and its HTML, which `figure.html` uses: a run of
docs is a `doc` row, followed by its lines as `raw` rows, which are hidden until **as
written** is clicked (a class on the figure, set by `app.js`, and CSS):

```walk settled python
Renderer::code_rows
# r[impl embed.docs]
def code_rows(self, s: Symbol, shown: list[int], indent: int, highlighted: list[str]) -> list[tuple[int | None, Markup, str]]:
    """An excerpt's rows: its code a line at a time, and each run of its docs as one.

    Returns
    -------
    list of tuple of (int or None, Markup, str)
        Each row's line number (None for a gap), its HTML and its kind: `code`, `doc`
        for a run of docs as prose, `raw` for its lines as written (shown instead, on
        request), or `gap`.
    """
    lines = self.ctx.index.files.lines(s.file)
    suffix = os.path.splitext(s.file)[1]
    # Contiguous stretches of what's shown, so a run of docs never spans a gap
    stretches: list[list[int]] = []
    for n in shown:
        if stretches and n == stretches[-1][-1] + 1:
            stretches[-1].append(n)
        else:
            stretches.append([n])
    rows: list[tuple[int | None, Markup, str]] = []
    for k, stretch in enumerate(stretches):
        if k:
            rows.append((None, Markup("…"), "gap"))
        raw = [lines[n - 1] for n in stretch]
        runs = dict(doc_runs(raw, [highlighted[n - 1] for n in stretch], suffix))
        i = 0
        while i < len(stretch):
            j = runs.get(i)
            if j is None:
                rows.append((stretch[i], Markup(_dedent_html(highlighted[stretch[i] - 1], indent) or " "), "code"))
                i += 1
                continue
            text = raw[i : j + 1]
            body = rust_doc_html(text, self.doc_linker(s)) if suffix == ".rs" else python_doc_html(text)
            pad = len(text[0]) - len(text[0].lstrip()) - indent
            kind = "rust" if suffix == ".rs" else "python"
            title = f"Lines {stretch[i]}–{stretch[j]}"
            prose = f'<div class="doc {kind}" style="--pad: {pad}ch" title="{title}">{body}</div>'
            rows.append((stretch[i], Markup(prose), "doc"))
            for n in stretch[i : j + 1]:
                rows.append((n, Markup(_dedent_html(highlighted[n - 1], indent) or " "), "raw"))
            i = j + 1
    return rows
```

```walk settled python
Renderer::doc_linker
def doc_linker(self, s: Symbol):
    """What links a name in `s`'s docs to its symbol, as rustdoc would: `Self` is the
    type the docs are on or in."""

    def link(name: str) -> str | None:
        target = name.removesuffix("()")
        if target == "Self" or target.startswith("Self::"):
            types = ("struct", "enum", "trait", "union", "type")
            owner = s.name if s.kind in types else (s.segments[-2] if len(s.segments) > 1 else "")
            target = owner + target[4:]
        sym, _ = self.ctx.index.resolve(target)
        if sym is None:
            return None
        self.symbols[target] = symbol_data(self.walk, sym)
        return f'<a class="sym" href="#" data-ref="{html.escape(target)}">'

    return link
```

The prose sits in the code's box but is sized by it, not by the code: the figure is a CSS
container, and a `doc` row is as wide as the figure shows less its indent (`--pad`), at
most 72 characters, and stays put when long code scrolls sideways. Its class is `docrow`, since `.doc` and
`.prose` are taken.

### Tests

```walk settled python
test_a_file_is_a_symbol_named_by_its_module_with_its_module_docs
# r[verify index.files]
# r[verify index.languages+2]
def test_a_file_is_a_symbol_named_by_its_module_with_its_module_docs(filed, pyrepo):
    """`core::storing` names `src/core/storing.rs`, with its `//!` docs, and there's no
    `mod storing` symbol; `lib.rs` is named by its path only; a Python module has its
    docstring."""
```

```walk settled python
test_a_file_is_named_by_its_path_or_any_tail_of_it
# r[verify ref.file]
def test_a_file_is_named_by_its_path_or_any_tail_of_it(filed):
    """`src/core/storing.rs`, `core/storing.rs` and `storing.rs` resolve; `ore/storing.rs`
    doesn't; a tail two files end with is ambiguous, with both as candidates."""
```

```walk settled python
test_an_item_is_meant_over_the_file_of_the_same_name
# r[verify ref.file]
def test_an_item_is_meant_over_the_file_of_the_same_name(filed): ...
```

```walk settled python
test_a_files_outline_is_its_module_docs
# r[verify ref.sig+2]
def test_a_files_outline_is_its_module_docs(filed): ...
```

```walk settled python
test_a_whole_file_in_a_walk_block_is_a_warning
# r[verify check.whole-file]
def test_a_whole_file_in_a_walk_block_is_a_warning(filed):
    """A whole file is a warning; with `sig` or `> text`, it isn't."""
```

```walk settled python
test_rust_doc_comments_are_shown_as_markdown_with_their_lines_as_written_too
# r[verify embed.docs]
def test_rust_doc_comments_are_shown_as_markdown_with_their_lines_as_written_too(repo):
    """Intra-doc links (and `Self::`) link to their symbols; a `compile_fail,E0616` block is
    highlighted as Rust, labelled, without its `# ` lines; every line as written is there
    too, hidden, with the button to show them."""
```

```walk settled python
test_a_numpy_docstrings_entries_are_shown_with_their_types_as_code
# r[verify embed.docs]
def test_a_numpy_docstrings_entries_are_shown_with_their_types_as_code(pyrepo):
    """`root : str` under Parameters is `root` and `str`, both as code, with its
    description as Markdown below."""
```

```walk settled python
test_a_type_alone_in_returns_or_raises_is_a_type
# r[verify embed.docs]
def test_a_type_alone_in_returns_or_raises_is_a_type(repo): ...
```

`test_python_symbols_are_named_from_their_package` leaves files out of the symbols it
lists, and the tests citing `index.languages` and `ref.sig` cite their new versions.

### Tried

All of this was written in a scratch copy of codewalk, not here, to check the drafts work:
the tests above and the existing ones pass (101), ruff is clean, `codewalk check` passes
on both this repository and the ancillaries service (whose 617 references all still
resolve), and `BatteryState sig` and codewalk's own `embed_line` were looked at in the
browser, as prose and as written.

At the work stage the scratch copy's code was brought here as it was, so each settled
block's code differs from its draft only where the draft elides the routine parts with `...`.

## Terms

## Facts

## Questions

> [!question] @claude: A Rust crate's root (`src/lib.rs`, `src/main.rs`) has no module
> path, so I've called it `crate`, which a crate with both makes ambiguous: each is still
> named by its path. Is `crate` worth having, or should a root file be named by its path
> only?
>
> > [!decision] @matthew: Yes, a root file should be named by its path only.

> [!question] @claude: A `walk` block of a whole file shows all of it, which for
> `core/storing.rs` is 1,500 lines. That's what it says, and `sig` and `> text` are there
> for the rest, but should a whole file in a `walk` block be a warning, so it's only ever
> linked inline or shown in part?
>
> > [!decision] @matthew: Yes, a warning seems reasonable.

> [!question] @claude: A Python docstring is shown as written rather than as Markdown,
> since NumPy's parameter lists (`name : type`, then an indented description) don't
> survive Markdown. Is that the right call, or would you rather NumPy docstrings were
> parsed into a proper list of parameters, as numpydoc does?
>
> > [!decision] @matthew: Parameters, returns and raises should render their types as
> > code, and the indented description lines are good to be rendered as Markdown.
> > Parameter names are code too.

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-09: @matthew asked for docs in excerpts to be addressed here too: in the
  ancillaries service's batteries codewalk, `BatteryState sig` shows its whole docstring
  as code, and suggested hiding the `///`, showing the text in a proportional font and
  highlighting the code blocks. That's Docs as prose, in [What we want](#what-we-want)
  and in the code.
