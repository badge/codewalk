# codewalk

Codewalks of the code, for people to review it by. A codewalk is a Markdown file
that **names** the code it talks about rather than pasting it. codewalk checks every name
still resolves, shows each one's code as it stands, with its context a click away, and
remembers what you've reviewed, so it can show you what's changed since.

codewalk is written about in codewalk:

- [codewalk, walked through](docs/codewalk.md): how it works, from parsing a
  codewalk to the page in the browser.
- [Its data model](docs/data_model.md): the things it knows about and how they relate.
- [Its spec](docs/spec/README.md): what it must do, as prose and the requirements that
  follow from it, with the words each part uses defined beside it.

Every example below names codewalk's own code, and a test checks each one still
resolves.

## Running it

It needs [uv](https://docs.astral.sh/uv/). Install it as a command, from this
repository, editable so it follows your checkout:

```bash
uv tool install --editable .
```

Then, from the root of the repository you want to walk through (this one, to start
with):

```bash
codewalk serve
```

Then open <http://localhost:4471>. Everything stays local: the server listens on
127.0.0.1 only. The only files it writes are codewalks and specs, when you save one in
the browser, and `codewalk.review.json`. Ctrl-C stops it.

| Command                               | What it does                                                   |
| ------------------------------------- | -------------------------------------------------------------- |
| `codewalk serve [--port 4471]`        | The web view, with editing and live reload                     |
| `codewalk check [CODEWALK...]`     | Every reference resolves; exits 1 if one doesn't               |
| `codewalk check --strict`             | The same, and also fails on code changed since it was reviewed |
| `codewalk export CODEWALK OUT`     | Plain Markdown, with the code written out and linked           |
| `codewalk review CODEWALK`         | Marks every embedded symbol reviewed as it stands              |
| `codewalk find QUERY`                 | Symbols matching QUERY, with the reference to write            |
| `codewalk context [--json]`           | What's in hand, for an agent starting a run                    |
| `codewalk lsp`                        | A language server, for your editor                             |
| `codewalk init [--dry-run]`           | Set a project up: config, an `AGENTS.md` section, two skills   |
| `codewalk new PATH --title T [--prd]` | Start a codewalk, or a PRD                                  |

## Writing a codewalk

Any Markdown file under the docs folders that makes a reference is a codewalk. Names
can point into Python or Rust. There are three kinds of reference, and each still reads
as plain Markdown:

````markdown
A codewalk is parsed into a [[Walk]], and every name in it is checked by
[[Walk::problems]], against [[r:ref.tail]]. A line of a `walk` block is read by
[an ordinary link](walk:embed_line).

```walk
Walk::problems
doc::Context sig
Renderer::embed > if ref.sig
```
````

| Written                       | Shown as                                                                |
| ----------------------------- | ----------------------------------------------------------------------- |
| `[[Name]]`, `[[Name\|label]]` | The name, linked: hover for its signature and docs, click for its file  |
| `[label](walk:Name)`          | The same, as an ordinary Markdown link                                  |
| `[[r:requirement.id]]`        | The requirement, linked: hover for its text                             |
| A `walk` block                | Each line's code, with its docs, requirement markers and line numbers   |

**Names.** A name is any tail of a symbol's path that names only it: `embed_line` if
there's one, `Renderer::embed` if there are several `embed`s. Methods and fields keep
their class (`Walk::problems`, `FrontMatter::weight`). In Rust, an impl block is `impl`
and its type. To pin one down further:

| Write                    | To mean                                                     |
| ------------------------ | ----------------------------------------------------------- |
| `crate::codewalk::config::Config` | The one whose whole path that is, not any `…::config::Config` |
| `doc.py#Context`         | The one in that file. Any tail of its path will do          |

**In a `walk` block**, one name per line. `//` starts a comment.

| After the name  | Shows                                                                     |
| --------------- | ------------------------------------------------------------------------- |
| `sig`           | Its outline: for Python, its header and docstring, and for a class, its fields and `__init__`'s header and docstring too; for Rust, its doc comments and first line |
| `> some text`   | Only part of it: from the first line containing the text, with the comments just above it, through the end of the block that line opens |

A name that's ambiguous or names nothing is an error. `check` and the editor list the
candidates, and the page shows them in place of the code.

**Front matter**, all optional, says what a codewalk is about. Other keys are left
alone:

```yaml
---
title: codewalk, walked through   # else the first heading
summary: How codewalk turns Markdown that names code into a page.   # else the first paragraph
tags: [codewalk, tooling]
related: [data_model.md]   # paths from this file
weight: 10   # where it goes in its folder: lighter first, then the rest by title
---
```

**Codewalks relate** by linking to each other, in the text or in `related`. Either
end shows the link: what a codewalk links to, and what links to it.

**Proposed code.** A change is usually argued for before it's written. Draft it under the
name it will have:

````markdown
```walk proposed python
Library::uses
def uses(self, ctx: Context, sym: Symbol) -> list[tuple[str, int]]:
    """The codewalks that show or mention `sym`, with the line of each reference."""
```
````

Until the name exists, it's shown as proposed and `check` lists it as in hand, not
broken. Once it's written, the page shows the code with the draft against it, and
**Settle** turns the block into `walk settled`: the code as written, with the draft kept,
so **as proposed** shows what was planned against what happened. Inline, `[[?Name]]`.

**A PRD** is a codewalk with all its code proposed (`codewalk new --prd`): the
problem, with the existing code named; the outcome; the spec prose it gives rise to,
citing the requirements it adds; the code and the tests, drafted with the requirement
markers they'll carry; and questions. Implementing it settles each proposal in turn, and
the page and the index show how far it's got. Done, it's a codewalk of what was
built, with the plan kept under each excerpt. Its front matter says `kind: prd`.

**Notes** are blockquotes, written under what they're about:

```markdown
> [!question] @matthew: Should `sig` show a class's methods too?
>
> [!answer] @claude: Only `__init__`: it's how the class is made.
>
> [!decision] @matthew: Only `__init__`.
```

A thread is open until its last question is answered or decided. A `[!request]` is a
standing ask, for something that applies throughout rather than to one excerpt; put it
at the top. It stands until a `[!done]` after it.

A reply to one note nests under it, as a blockquote inside the thread (`> > [!question]
…`), so a refinement stays with what it refines; a thread is open while anything in it,
at any depth, is. Once it's settled, **To changelog** takes it out of the text and keeps
one line of it in a `## Changelog` at the end (what was asked, how it was settled, how
many notes came between), newest first, and **Remove** takes it out altogether.

Write notes in the Markdown, or from the browser: **Ask** on an excerpt, **Answer**,
**Ask more** or **Decide** on a thread, and **Reply** on any note. Asking about one
excerpt of several in a block puts the question directly under it. Notes from the browser
are signed with `author` from `codewalk.toml`, or the first word of git's `user.name`.

**Terms and facts** are defined like tracey's requirements, a marker on its own line and
the text after, in the spec they belong to. From codewalk's
[codewalks spec](docs/spec/codewalks.md) and [specs spec](docs/spec/specs.md):

```markdown
t[excerpt]
The code a line of a `walk` block shows: a symbol as it stands in its file.

f[tracey.prefix] documented
tracey infers a spec's prefix, the `r` in `r[id]`, from the requirement markers in its files.
```

A fact says how we know it: `documented`, `observed` or `assumed` (the default). Cite
them with `[[t:excerpt]]`, `[[f:tracey.prefix]]`, or `term:` and `fact:` links. A term is
also linked wherever its words appear in prose (the first time in each paragraph), so any
use of it can be hovered for what it means.

[`SYNTAX.md`](SYNTAX.md) has all of it as a grammar.

## Specs

A spec's prose says what we mean; its requirements say exactly what must happen, and
they're written from the prose. The prose cites the requirements it gives rise to, as an
ID in backticks (`` `ref.tail` ``), `[[r:id]]` (for one not written yet), or a `req:`
link. `/spec/<file>` shows the prose with each cited requirement in the margin beside it,
and lists:

- requirements no prose cites;
- citations of requirements that don't exist yet;
- drift: the prose or the requirement changed since they were last reconciled, with what
  changed. **They agree** reconciles them, recording both in the review file.

Each requirement shows the code that implements and verifies it, from tracey's markers,
and the codewalks that propose, implement or cite it. That's for finding the code;
coverage and validation are tracey's. The spec files are the ones tracey's config
(`.config/tracey/config.styx`) names, and any more in `codewalk.toml`. A requirement is
`r[id]`, or with a spec's name as its prefix (`codewalk[id]`); codewalk's own
[spec](docs/spec/README.md) uses `r`.

**Prose, spec and code, side by side.** A codewalk's margin shows, level with each
block, the requirements the block proposes, implements, verifies or cites (from the
markers in its code, written or drafted, and its citations). Each card leads to its spec,
at the prose that gave rise to it, which stays lit until you click away. **Requirements**,
or `m`, puts the margin away.

## In the browser

- **The index.** Codewalks grouped by folder, in order of weight, filtered by tag or
  text (kept in the URL); and the specs, as a tree of their folders.
- **The codewalk.** Each excerpt has a caption showing its kind and path, and whether
  it's been reviewed. Its tags and related codewalks are in the sidebar. **Zed** opens
  it in Zed. **Copy** copies its name. Click its path or line, or any name in its code,
  to see it in its file.
- **Its file.** The panel on the right shows the whole file, highlighted, with the symbol
  marked, and the file's outline docked on its right, to filter or put away (`o`).
  Requirement markers in the code link to their spec.
- **Find a symbol**, with `/`. Enter shows it in its file. Shift+Enter copies the name to
  write.
- **Editing.** Press `e`, or click Edit, to edit from where you're reading, with a live
  preview. The two scroll together (**Linked scrolling** turns it off), a click in the
  preview puts the caret on its line, and the caret's block is marked in the preview.
  **Done** or Esc goes back to reading at the same place. Type `[[`, or start a line in a
  `walk` block, to complete a name. Problems are listed under the editor: click one to
  go to its line, or click a suggestion to use it. Cmd+S or Ctrl+S saves.
- **Live.** A page updates when its codewalk, the code or the review file changes.
  Edit in your own editor and the page keeps up.
- **The glossary,** at `/glossary`: every term and fact, grouped by the spec that
  defines it, with where each is used.

## Reviewing

**Reviewed**, on an excerpt, records its code as it stands in `codewalk.review.json` at
the repository root. Commit that file, so the record travels with the code. When the code
changes, the badge turns to **changed since review**. Click it to see what changed since
you reviewed it, then mark it reviewed again. **Mark all reviewed** does the whole
codewalk.

## For agents

`codewalk context` is what a session should pick up, across codewalks and specs:
standing requests, open questions (with what they're about), proposals not written yet,
proposals written and waiting to be settled, code changed since review, and broken
references. `codewalk init` sets a project up for it:

- `codewalk.toml`, if there isn't one;
- a section in `AGENTS.md`, between markers, saying how codewalks, specs and the
  glossary work (running init again replaces it);
- two skills in `.claude/skills/`: `codewalk-propose`, to propose a change as a
  codewalk before writing it, and `codewalk-work`, to carry one forward.

This repository is set up that way: see its [`AGENTS.md`](AGENTS.md).

## In your editor

`codewalk lsp` is a language server over stdin and stdout: diagnostics as you type,
completion after `[[` and in `walk` blocks, hover, go to definition, and quick fixes for
names with candidates. Point your editor's Markdown at it. In Helix, for example, in
`languages.toml`:

```toml
[language-server.codewalk]
command = "codewalk"
args = ["lsp"]

[[language]]
name = "markdown"
language-servers = ["codewalk", "marksman"]
```

Neovim takes the same command with `vim.lsp.start`. Zed and VS Code only run a language
server from an extension, which doesn't exist yet.

## Configuration

Where it looks is set by an optional `codewalk.toml` at the repository root. This
repository's:

```toml
sources = ["codewalk/**/*.py"]
specs = ["docs/spec/**/*.md"]
docs = ["docs/**/*.md"]
# Who notes written in the browser are from (default: git's user.name, first word)
# author = "matthew"
```

Without one, `sources` is `src/**/*.rs`; `specs` and `docs` are as above.

## How it's built

| Package or module | Does                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| `cli.py`          | The commands, with rich-click                                            |
| `config.py`       | `codewalk.toml`, as a Pydantic model                                     |
| `code/`           | The code: `index.py` parses Rust with tree-sitter into symbols, each with its span, docs and requirement markers, and resolves names; `python.py` does the same for Python; `highlight.py` highlights a file with Pygments, a line at a time, so any range can be cut out |
| `walk/`           | Codewalks: `doc.py` parses one with markdown-it, checks it and exports it; `notes.py` reads and writes threads; `review.py` keeps the review file; `library.py` puts them all together; `brief.py` is what's in hand, for `codewalk context` |
| `spec/`           | The spec: `requirements.py` reads them; `tracey.py` reads tracey's config; `prose.py` sets a spec's prose against its requirements (citations, gaps, drift); `trail.py` follows prose to spec to code; `terms.py` is the glossary |
| `web/`            | The browser: `server.py`, Starlette under uvicorn, with watchfiles and server-sent events for live reload; `render.py`, a codewalk as HTML, every block tagged with its Markdown line; `templates/` in Jinja; `static/`, plain JS and CSS |
| `lsp.py`          | The language server, on pygls                                            |
| `setup/`          | `codewalk init`, and the `AGENTS.md` section and skills it writes        |

tracey holds the code and tests to [the spec](docs/spec/README.md):

```bash
tracey query . status
```

Tests and lint:

```bash
uv run --group dev pytest
```

```bash
uvx ruff check
```
