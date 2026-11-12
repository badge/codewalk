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
the nearest (`ref.nearest`). `crate::` pins a name to the root (`ref.crate`). A file is
named by its path, or any tail of it, which a name can't be mistaken for, since a name has
no `/` or `.` in it; and where a file and an item in it share a name, the item is meant
(`ref.file`).

A name is written inline as `[[Name]]` or as a `walk:` link, and to show the code itself,
on a line of its own in a `walk` block (`ref.forms`). A line can show just the part of a
symbol that starts on a line containing some text, to the end of the statement or block
that line starts (`ref.focus`), or just its signature and documentation, `sig`
(`ref.sig`).

Rust and Python are both indexed: functions, types, methods, impls and classes, and the
names assigned at the top of a module or class (`index.languages`). Each file is a
symbol too, named by its module, with its module docs as its docs; a Rust module declared
in a file of its own is that file, and a crate's root, which has no module path, is named
by its path (`index.files`). A Python symbol's
qualified name comes from its package, so it reads like a Rust one (`index.python-path`).
A symbol starts at its doc comments, attributes, decorators and the comments directly
above it, since that's where its requirement markers are (`index.start`).

### Showing it

Each name in a `walk` block is shown as its code as it stands, highlighted, with its line
numbers, and a caption saying what and where it is (`embed.current`). A type, or an enum's
variant, is coloured as one wherever it's named, and so is a constant, though the lexer
marks a type only where one is expected ([[f:pygments.names]]); codewalk goes by how they're
named (`embed.names`). A block can also
show what the spec says, where that's the point of a passage: a requirement as its text,
and a run of terms and facts as one table of what each means (`embed.definitions`). An inline name is a
link: hover for its signature and docs, click for its file (`embed.inline`).

Docs in an excerpt read as what they say, not as comments: Rust's doc comments as
Markdown, with their code highlighted and their intra-doc links linked, and a Python
docstring as NumPy style, each entry's name and type as code and its description as
Markdown. Their lines as written are a click away (`embed.docs`).

### Checking it

`codewalk check` resolves every reference in every codewalk, and says what's broken,
by file and line, and fails if anything is (`check.broken`). A link to a Markdown file
that isn't there is broken too (`check.links`). Code that's changed since it was reviewed
isn't broken, so it's a warning, unless asked to be strict (`check.strict`). So is a
whole file in a `walk` block: a file is linked inline, or shown in part
(`check.whole-file`).

### Reviewing it

Reading an excerpt and marking it reviewed records the code as it was, in
`codewalk.review.json` at the root, by codewalk and reference (`review.record`). When
the code changes, the excerpt says so, with what changed since (`review.changed`).
Marking code reviewed is a person's to do (`review.people`). Code reviewed and unchanged since
can be reopened, which forgets the review, so it reads as not reviewed again
(`review.reopen`).

### Pinning it

A codewalk about code that's since changed, or gone, can be pinned to a ref in its
project's repository, a tag being the one that lasts: `at: <ref>` in its front matter. It's
then read against the code as it was at that ref's commit, straight from git, with
nothing checked out and nothing written (`pin.at`). It's shown that way everywhere: its
excerpts, its links, the file opened beside it, and `codewalk check` and `export`; and
reading a branch's worktrees doesn't move it (`pin.everywhere`). Code in another
repository, through a `../` glob, is read as it's checked out, since the ref is only
the project's own (`pin.own-repo`). The page says what it's pinned to, and when that
commit was made (`pin.label`). A ref that names no commit is broken (`pin.broken`).

### Taking it elsewhere

A codewalk exports to plain Markdown, with each excerpt written out as it stands and
linked to its file, for anywhere codewalk isn't (`export.plain`).

## Terms

r[term.reference]
A name for code in a codewalk: inline, as `[[Name]]` or a `walk:` link, or on a line
of its own in a `walk` block. It resolves to one symbol, or it's broken.

r[term.qualified-name]
A symbol's full name: the path to it and then its own name, with `::` between, as
`codewalk::walk::doc::Walk::problems`. A Python module's dotted path is written the same
way.

r[term.excerpt]
The code a line of a `walk` block shows: a symbol as it stands in its file, all of it,
part of it (`> text`), or its outline (`sig`).

r[term.broken]
A reference that names no symbol, or more than one, or a link to a Markdown file that
isn't there. `codewalk check` fails on one. A proposal's name, not written yet, is in
hand instead.

r[term.pin]
The ref a codewalk is read at, from `at` in its front matter, and the commit it names
then: its code is the code as it was there, not as it is.

r[term.review]
A person's record of having read an excerpt: the digest and text of its code as it was,
in `codewalk.review.json`. Once the code's digest differs, the excerpt has changed since
its review.

## Facts

r[fact.pygments.names] observed
Pygments' Rust lexer marks a name as a class (`Name.Class`) only where a type is expected,
as in a signature or after `impl`. Elsewhere, a type, an enum's variant or a constant is a
plain `Name`: `Setpoint::Idle` in a match arm, or `TOLERANCE_KW` in an expression. Its
Python lexer is the same outside `class` and `def`. Observed in Pygments 2.21, November 2026.

r[fact.markdown-it.token-types] observed
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

r[ref.focus+2]
A line of a `walk` block of the form `Name > text` MUST show only the part of the symbol
that starts on the first line containing `text`: from that line, with the comments directly
above it, to the end of the statement, item or block it starts, whichever reaches
furthest. It MUST be an error if no line contains `text`.

r[ref.sig+2]
A line of a `walk` block ending ` sig` MUST show only the symbol's outline: for Rust, its
doc comments and first line; for Python, its header and docstring and, for a class, its
fields and its `__init__`'s header and docstring; for a file, its module docs.

r[ref.file]
A reference with a `/` or a `.` in it and no `#` MUST be read as a file's path, and MUST
resolve to the one indexed file whose path from the root is it or ends with it on `/`
boundaries. One that ends more than one file's path MUST NOT resolve, and MUST be
reported with each file as a candidate. A name that ends both a file's qualified name and
one item's MUST resolve to the item.

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

r[index.python-path]
A Python symbol's qualified name MUST start with its module's dotted path, as `::`
segments, from the outermost folder of its package.

r[index.start]
A symbol MUST be taken to start at the first of its doc comments, attributes, decorators
and the comments directly above it.

r[embed.current]
Each resolved line of a `walk` block MUST be rendered as the symbol's code as it is in
the file now, highlighted, with its line numbers and its qualified name, file and line.

r[embed.names]
In highlighted Rust and Python, a name written in CamelCase MUST be coloured as a type,
and one written in UPPER_CASE as a constant, wherever it appears, as in a match arm's
`Setpoint::Idle` or an expression's `TOLERANCE_KW`.

r[embed.definitions]
A line of a `walk` block of the form `t:id` or `f:id` MUST be read as the term or fact
`id`, and an unknown one MUST be an error. Each run of such lines in a block MUST be
rendered as one table, a row each, in order: the term's words, or the fact's ID and how
it's known, linked to its definition, and its whole text. `codewalk export` MUST write
the table as a Markdown table.

r[embed.inline]
An inline reference MUST be rendered as a link to the symbol showing its signature and
docs on hover and its file, at the symbol, on click.

r[embed.docs]
In an excerpt, each run of Rust doc comments MUST be shown as one row of its text
rendered as Markdown, its code blocks highlighted (as Rust unless they name another
language, without the lines rustdoc hides) and each intra-doc link that names a symbol
linked to it as an inline reference is; and each Python docstring as one row, read as
NumPy style: its text and each entry's description rendered as Markdown, and each entry
in a section listing names or types shown as its name and its type, both as code. An
excerpt with docs MUST offer to show them as written instead, with their line numbers.

r[check.broken]
`codewalk check` MUST report each unresolved reference with its file, line and
candidates, and MUST exit non-zero if there is one.

r[check.links]
A relative link in a codewalk to a Markdown file that doesn't exist MUST be reported
as an error.

r[check.strict]
Code changed since it was reviewed MUST be reported as a warning, and `codewalk check
--strict` MUST exit non-zero on one.

r[check.whole-file]
A line of a `walk` block that shows a whole file, with neither ` sig` nor `> text`, MUST
be reported as a warning.

r[review.record]
Marking a reference reviewed MUST record a digest and the text of its code, under the
codewalk and the reference as written, in `codewalk.review.json` at the root.

r[review.changed]
A reference whose code's digest differs from the one recorded MUST be shown as changed,
with a diff from the code as recorded to the code as it is.

r[review.people]
codewalk MUST NOT mark code reviewed except at a person's request, from the browser or
`codewalk review`.

r[review.reopen]
An excerpt reviewed and unchanged since MUST offer to reopen it in place of marking it
reviewed; reopening it MUST drop its record from `codewalk.review.json`, so it's shown as
not reviewed.

r[review.branches]
codewalk MUST find every branch with a worktree in any of the project's repositories:
its own, and each one beside it that a `../` source glob reaches.

r[review.branch-pick]
Every page MUST show whether the code is read as it's checked out or from a branch's
worktrees, and MUST let a person choose either, listing each branch with its
repositories and where it started.

r[review.branch-code]
While a branch is read, each source file in a repository with a worktree on it MUST be
read from that worktree, under the same path and so the same names; the others as
they're checked out. The choice MUST be the server's, for every page of the project,
and nothing MUST be written.

r[review.branch-base]
A branch MUST be compared with the commit it shares with the ref it was made from, as
its reflog records it, or else with its repository's default branch.

r[review.branch-diff]
While a branch is read, each embedded symbol in one of its worktrees MUST be labelled
new, changed or unchanged on it, by its text against the symbol of the same name and
kind at that commit; a whole symbol that changed MUST be shown as a diff from there to
now in place of its code, and an excerpt only labelled.

r[review.branch-gone]
While a branch is read, a reference that names nothing on it but a symbol as it's
checked out, which was there where the branch started, MUST be shown as that symbol,
removed, and labelled gone.

r[export.plain]
`codewalk export` MUST write the codewalk as plain Markdown, with each `walk` block
replaced by the code it shows, in a fenced block in its language, linked to its file and
line.

r[pin.at]
A codewalk whose front matter has `at` MUST have its references resolved, and its code
shown, against the source files as they were at the commit that ref names in the
project's repository, read from git objects, without checking out or writing anything.

r[pin.everywhere]
A pinned codewalk's code MUST be read at its commit wherever it's shown or checked: its
excerpts, inline references, the file opened beside it, `codewalk check` and `codewalk
export`; and MUST be read so whichever branch's worktrees are being read.

r[pin.own-repo]
A source file outside the project's repository, through a `../` glob, MUST be read as
it's checked out for a pinned codewalk.

r[pin.label]
A pinned codewalk's page MUST say the ref it's pinned to, its commit, and the date of
that commit.

r[pin.broken]
An `at` that names no commit in the project's repository MUST be reported as an error,
by `codewalk check` and on the page.
