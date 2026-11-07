---
weight: 10
---

## Codewalks

A codewalk is an ordinary Markdown file under the docs folders that makes at least one
reference to the code (`walk.what`). It reads as Markdown anywhere: on GitLab, in an
editor, in a diff. codewalk adds to it, and never needs it to be anything else.

### Naming code

Code is named the way people say it: `Walk::render`, not a file and a line range. A name
can be any tail of a symbol's qualified name, as long as only one symbol ends that way
(`ref.tail`); if several do, it's ambiguous, and codewalk says which they are rather than
guessing (`ref.ambiguous`). A name that matches nothing is broken, and codewalk suggests
the nearest (`ref.nearest`). `crate::` pins a name to the root (`ref.crate`).

A name is written inline as `[[Name]]` or as a `walk:` link, and to show the code itself,
on a line of its own in a `walk` block (`ref.forms`). A line can show just the part of a
symbol that opens on a line containing some text (`ref.focus`), or just its signature and
documentation, `sig` (`ref.sig`).

Rust and Python are both indexed: functions, types, methods, impls and classes, and the
names assigned at the top of a module or class (`index.languages`). A Python symbol's
qualified name comes from its package, so it reads like a Rust one (`index.python-path`).
A symbol starts at its doc comments, attributes, decorators and the comments directly
above it, since that's where its requirement markers are (`index.start`).

### Showing it

Each name in a `walk` block is shown as its code as it stands, highlighted, with its line
numbers, and a caption saying what and where it is (`embed.current`). An inline name is a
link: hover for its signature and docs, click for its file (`embed.inline`).

### Checking it

`codewalk check` resolves every reference in every codewalk, and says what's broken,
by file and line, and fails if anything is (`check.broken`). A link to a Markdown file
that isn't there is broken too (`check.links`). Code that's changed since it was reviewed
isn't broken, so it's a warning, unless asked to be strict (`check.strict`).

### Reviewing it

Reading an excerpt and marking it reviewed records the code as it was, in
`codewalk.review.json` at the root, by codewalk and reference (`review.record`). When
the code changes, the excerpt says so, with what changed since (`review.changed`).
Marking code reviewed is a person's to do (`review.people`).

### Taking it elsewhere

A codewalk exports to plain Markdown, with each excerpt written out as it stands and
linked to its file, for anywhere codewalk isn't (`export.plain`).

## Terms

t[reference]
A name for code in a codewalk: inline, as `[[Name]]` or a `walk:` link, or on a line
of its own in a `walk` block. It resolves to one symbol, or it's broken.

t[qualified-name]
A symbol's full name: the path to it and then its own name, with `::` between, as
`codewalk::walk::doc::Walk::problems`. A Python module's dotted path is written the same
way.

t[excerpt]
The code a line of a `walk` block shows: a symbol as it stands in its file, all of it,
part of it (`> text`), or its outline (`sig`).

t[broken]
A reference that names no symbol, or more than one, or a link to a Markdown file that
isn't there. `codewalk check` fails on one. A proposal's name, not written yet, is in
hand instead.

t[review]
A person's record of having read an excerpt: the digest and text of its code as it was,
in `codewalk.review.json`. Once the code's digest differs, the excerpt has changed since
its review.

## Facts

f[markdown-it.token-types] observed
markdown-it-py's token types (`fence`, `paragraph_open`) are plain strings it makes up as
it parses, with no enum of its own. Observed in markdown-it-py 3, November 2026.

## Requirements

r[walk.what]
A Markdown file matched by the `docs` globs in `codewalk.toml` MUST be treated as a
codewalk if it contains a `walk` block or a `[[…]]` reference, and isn't a spec file.

r[ref.tail]
A name MUST resolve to the one symbol whose qualified name ends with it, segment by
segment.

r[ref.ambiguous]
A name that ends more than one symbol's qualified name MUST NOT resolve, and MUST be
reported with each of those symbols as a candidate.

r[ref.nearest]
A name that ends no symbol's qualified name MUST NOT resolve, and MUST be reported with
the nearest names as candidates.

r[ref.crate]
A name starting `crate::` MUST resolve only to a symbol whose qualified name starts with
the rest of it.

r[ref.forms]
A reference MUST be recognised as `[[Name]]` or `[[Name|label]]` inline, as a link with
the `walk:` scheme, and as a line of a `walk` block.

r[ref.focus]
A line of a `walk` block of the form `Name > text` MUST show only the block of the symbol
that opens on the first line containing `text`, and it MUST be an error if no line does.

r[ref.sig]
A line of a `walk` block ending ` sig` MUST show only the symbol's outline: for Rust, its
doc comments and first line; for Python, its header and docstring and, for a class, its
fields and its `__init__`'s header and docstring.

r[index.languages]
The source files matched by the `sources` globs MUST be indexed: `.rs` files for Rust's
functions, types, traits, impls, modules and consts, and `.py` files for Python's
functions, classes, methods and the names assigned at the top level of a module or class.

r[index.python-path]
A Python symbol's qualified name MUST start with its module's dotted path, as `::`
segments, from the outermost folder of its package.

r[index.start]
A symbol MUST be taken to start at the first of its doc comments, attributes, decorators
and the comments directly above it.

r[embed.current]
Each resolved line of a `walk` block MUST be rendered as the symbol's code as it is in
the file now, highlighted, with its line numbers and its qualified name, file and line.

r[embed.inline]
An inline reference MUST be rendered as a link to the symbol showing its signature and
docs on hover and its file, at the symbol, on click.

r[check.broken]
`codewalk check` MUST report each unresolved reference with its file, line and
candidates, and MUST exit non-zero if there is one.

r[check.links]
A relative link in a codewalk to a Markdown file that doesn't exist MUST be reported
as an error.

r[check.strict]
Code changed since it was reviewed MUST be reported as a warning, and `codewalk check
--strict` MUST exit non-zero on one.

r[review.record]
Marking a reference reviewed MUST record a digest and the text of its code, under the
codewalk and the reference as written, in `codewalk.review.json` at the root.

r[review.changed]
A reference whose code's digest differs from the one recorded MUST be shown as changed,
with a diff from the code as recorded to the code as it is.

r[review.people]
codewalk MUST NOT mark code reviewed except at a person's request, from the browser or
`codewalk review`.

r[export.plain]
`codewalk export` MUST write the codewalk as plain Markdown, with each `walk` block
replaced by the code it shows, in a fenced block in its language, linked to its file and
line.
