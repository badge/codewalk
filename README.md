# codewalk

Walkthroughs of the code, for people to review it by. A walkthrough is a Markdown file
that **names** the code it talks about rather than pasting it. codewalk checks every name
still resolves, shows each one's code as it stands, with its context a click away, and
remembers what you've reviewed, so it can show you what's changed since.

ancillaries-service's ERCOT ERS strict deep dive is written this way, and so is
[codewalk's own walkthrough](docs/walkthrough.md), which is the best way to see how it
works. [Its data model](docs/data_model.md) shows how the pieces relate.

## Running it

It needs [uv](https://docs.astral.sh/uv/). Install it as a command, from this
repository, editable so it follows your checkout:

```bash
uv tool install --editable .
```

Then, from the root of the repository you want to walk through:

```bash
codewalk serve
```

Then open <http://localhost:4471>. Everything stays local: the server listens on
127.0.0.1 only. The only files it writes are walkthroughs, when you save one in the
browser, and `codewalk.review.json`.

| Command                             | What it does                                                    |
| ----------------------------------- | --------------------------------------------------------------- |
| `codewalk serve [--port 4471]`      | The web view, with editing and live reload                      |
| `codewalk check [WALKTHROUGH...]`   | Every reference resolves; exits 1 if one doesn't                |
| `codewalk check --strict`           | The same, and also fails on code changed since it was reviewed  |
| `codewalk export WALKTHROUGH OUT`   | Plain Markdown, with the code written out and linked            |
| `codewalk review WALKTHROUGH`       | Marks every embedded symbol reviewed as it stands               |
| `codewalk find QUERY`               | Symbols matching QUERY, with the reference to write             |
| `codewalk context [--json]`         | What's in hand, for an agent starting a run                     |
| `codewalk lsp`                      | A language server, for your editor                              |
| `codewalk init [--dry-run]`         | Set a project up: config, an `AGENTS.md` section, two skills     |
| `codewalk new PATH --title T [--prd]` | Start a walkthrough, or a PRD                                  |

## Writing a walkthrough

Any Markdown file under the docs folders that makes a reference is a walkthrough. Names
can point into Rust or Python. There are three kinds of reference, and each still reads
as plain Markdown:

````markdown
Each reading reaches [[BatteryController::on_site_load]], which holds the site to
[[r:program.ercot-ers-strict.hold]]. The fleet sends it on as
[an update](walk:FleetProcessed::updates).

```walk
BatteryController::on_site_load
Dispatch::on_short sig
program_terms > ProgramKind::ErcotErsStrict =>
impl Hold
```
````

| Written                        | Shown as                                                      |
| ------------------------------ | ------------------------------------------------------------- |
| `[[Name]]`, `[[Name\|label]]`  | The name, linked: hover for its signature and docs, click for its file |
| `[label](walk:Name)`           | The same, as an ordinary Markdown link                        |
| `[[r:requirement.id]]`         | The requirement, linked: hover for its text                   |
| A `walk` block                 | Each line's code, with its doc comments, markers and line numbers |

**Names.** A name is any tail of a symbol's path that names only it: `on_short` if
there's one, `Dispatch::on_short` if there are several. Methods, fields and variants
keep their type (`Hold::power_kw`). An impl block is `impl` and its type (`impl Hold`,
`impl ProgramRules for ErcotErsStrict`). To pin one down further:

| Write                      | To mean                                                     |
| -------------------------- | ----------------------------------------------------------- |
| `crate::Battery`           | The one at the crate root, not any `…::Battery`             |
| `fleet.rs#BatteryUpdate`   | The one in that file. Any tail of its path will do          |

**In a `walk` block**, one name per line. `//` starts a comment.

| After the name  | Shows                                                                     |
| --------------- | ------------------------------------------------------------------------- |
| `sig`           | Only the doc comments and the first line                                  |
| `> some text`   | Only part of it: from the first line containing the text, with the comments just above it, through the end of the block that line opens |

A name that's ambiguous or names nothing is an error. `check` and the editor list the
candidates, and the page shows them in place of the code.

**Front matter**, all optional, says what a walkthrough is about. Other keys are left
alone:

```yaml
---
title: Running an ERCOT ERS strict dispatch   # else the first heading
summary: One dispatch, from Voltus's poll to the batteries freed.   # else the first paragraph
tags: [ercot, dispatch]
related: [overview.md]   # paths from this file
---
```

**Walkthroughs relate** by linking to each other, in the text or in `related`. Either
end shows the link: what a walkthrough links to, and what links to it.

**Proposed code.** A change is usually argued for before it's written. Draft it under the
name it will have:

````markdown
```walk proposed rust
Dispatch::rebalance
pub(super) fn rebalance(&mut self, now: DateTime<Utc>) -> Rebalanced { … }
```
````

Until the name exists, it's shown as proposed and `check` lists it as in hand, not
broken. Once it's written, the page shows the code with the draft against it, and
**Settle** turns the block into `walk settled`: the code as written, with the draft kept,
so **as proposed** shows what was planned against what happened. Inline, `[[?Name]]`.

**A PRD** is a walkthrough with all its code proposed (`codewalk new --prd`): the
problem, with the existing code named; the outcome; the spec prose it gives rise to,
citing the requirements it adds; the code and the tests, drafted with the requirement
markers they'll carry; and questions. Implementing it settles each proposal in turn, and
the page and the index show how far it's got. Done, it's a walkthrough of what was
built, with the plan kept under each excerpt. Its front matter says `kind: prd`.

**Notes** are blockquotes, written under what they're about:

```markdown
> [!question] @matthew: Why per battery?
>
> [!answer] @claude: Because …
>
> [!decision] @matthew: Per battery.
```

A thread is open until its last question is answered or decided. A `[!request]` is a
standing ask, for something that applies throughout rather than to one excerpt; put it
at the top. It stands until a `[!done]` after it.

A reply to one note nests under it, as a blockquote inside the thread (`> > [!question]
…`), so a refinement stays with what it refines; a thread is open while anything in it,
at any depth, is. Once it's settled, **To changelog** takes it out of the text and keeps
one line of it in a `## Changelog` at the end (what was asked, how it was settled, how
many notes came between), newest first, and **Remove** takes it out altogether.

Write notes in the Markdown, or from the browser: **Ask** on an excerpt, **Answer**, **Ask more** or
**Decide** on a thread, and **Reply** on any note. Notes from the browser are signed with `author` from
`codewalk.toml`, or the first word of git's `user.name`.

**Terms and facts** are defined like tracey's requirements, a marker on its own line and
the text after; tracey ignores them:

```markdown
t[deadband]
How far above its target a site's import can rise before we act.

f[ercot.ers.settlement-periods] documented
ERCOT judges a dispatch in 15-minute settlement periods.
```

A fact says how we know it: `documented`, `observed` or `assumed` (the default). Cite
them with `[[t:deadband]]`, `[[f:…]]`, or `term:` and `fact:` links. A term is also
linked wherever its words appear in prose (the first time in each paragraph), so any use
of it can be hovered for what it means. ancillaries-service's are in its
`docs/glossary.md`.

[`SYNTAX.md`](SYNTAX.md) has all of it as a grammar.

## Specs

A spec's prose says what we mean; its requirements say exactly what must happen, and
they're written from the prose. The prose cites the requirements it gives rise to, as an
ID in backticks (`` `program.ercot-ers-strict.end` ``), `[[r:id]]` (for one not written
yet), or a `req:` link. `/spec/<file>` shows the prose with each cited requirement in the
margin beside it, and lists:

- requirements no prose cites;
- citations of requirements that don't exist yet;
- drift: the prose or the requirement changed since they were last reconciled, with what
  changed. **They agree** reconciles them, recording both in the review file.

Each requirement shows the code that implements and verifies it, from tracey's markers,
and the walkthroughs that propose, implement or cite it. That's for finding the code;
coverage and validation are tracey's.

**Prose, spec and code, side by side.** A walkthrough's margin shows, level with each
block, the requirements the block proposes, implements, verifies or cites (from the
markers in its code, written or drafted, and its citations), each with the prose in its
spec that gave rise to it. **Requirements**, or `m`, puts the margin away.

## In the browser

- **The index.** Walkthroughs grouped by folder, filtered by tag or text (kept in the
  URL), with a map of how they link.
- **The walkthrough.** Each embedded symbol has a caption showing its kind and path, and
  whether it's been reviewed. Its tags and related walkthroughs are in the sidebar. **Zed** opens it in Zed. **Copy** copies its name. Click
  its path or line to see it in its file.
- **Its file.** The panel on the right shows the whole file, highlighted, with the symbol
  marked, and the file's outline docked on its right, to filter or put away (`o`).
  Requirement markers in the code link to their text.
- **Find a symbol**, with `/`. Enter shows it in its file. Shift+Enter copies the name to
  write.
- **Editing.** Press `e`, or click Edit, to edit from where you're reading, with a live
  preview. The two scroll together (**Linked scrolling** turns it off), a click in the
  preview puts the caret on its line, and the caret's block is marked in the preview.
  **Done** or Esc goes back to reading at the same place. Type `[[`, or start a line in a
  `walk` block, to complete a name. Problems are listed under the editor: click one to
  go to its line, or click a suggestion to use it. Cmd+S or Ctrl+S saves.
- **Live.** A page updates when its walkthrough, the code or the review file changes.
  Edit in your own editor and the page keeps up.
- **The glossary,** at `/glossary`: every term and fact, where it's defined and used.

## Reviewing

**Reviewed**, on an embedded symbol, records its code as it stands in
`codewalk.review.json` at the repository root. Commit that file, so the record travels
with the code. When the code changes, the badge turns to **changed since review**. Click
it to see what changed since you reviewed it, then mark it reviewed again. **Mark all
reviewed** does the whole walkthrough.

## For agents

`codewalk context` is what a session should pick up: open questions (with what they're
about), proposals not written yet, proposals written and waiting to be settled, code
changed since review, and broken references. `codewalk init` sets a project up for it:

- `codewalk.toml`, if there isn't one;
- a section in `AGENTS.md`, between markers, saying how walkthroughs, specs and the
  glossary work (running init again replaces it);
- two skills in `.claude/skills/`: `codewalk-propose`, to propose a change as a
  walkthrough before writing it, and `codewalk-work`, to carry one forward.

## In your editor

`codewalk lsp` is a language server over stdin and stdout: diagnostics as you type,
completion after `[[` and in `walk` blocks, hover, go to definition, and quick fixes for
names with candidates. Point your editor's Markdown at it. In Helix, for example, in
`languages.toml`:

```toml
[language-server.codewalk]
command = "uv"
args = ["tool", "run", "codewalk", "lsp"]

[[language]]
name = "markdown"
language-servers = ["codewalk", "marksman"]
```

Neovim takes the same command with `vim.lsp.start`. Zed and VS Code only run a language
server from an extension, which doesn't exist yet.

## Configuration

Where it looks is set by an optional `codewalk.toml` at the repository root (this
repository's adds codewalk's own source). These are the defaults:

```toml
sources = ["src/**/*.rs"]
specs = ["docs/spec/**/*.md"]
docs = ["docs/**/*.md"]
# Who notes written in the browser are from (default: git's user.name, first word)
# author = "matthew"
```

Specs are Markdown with tracey's markers: `r[id]` on its own line, then the text.

## How it works

| Module         | Does                                                                        |
| -------------- | --------------------------------------------------------------------------- |
| `config.py`    | `codewalk.toml`, as a Pydantic model                                        |
| `index.py`     | Parses Rust with tree-sitter into symbols, each with its span, docs and requirement markers; resolves names. Each file is parsed again only when it changes |
| `python.py`    | The same for Python                                                         |
| `doc.py`       | Parses a walkthrough with markdown-it: references, front matter, links; checks it; exports it |
| `library.py`   | All the walkthroughs together: tags, folders and how they link; the specs   |
| `notes.py`     | Threads of questions, answers and decisions, read and written               |
| `brief.py`     | What's in hand, for `codewalk context`                                      |
| `spec.py`      | A spec's prose against its requirements: citations, gaps, drift             |
| `trail.py`     | Prose to spec to code: the requirements each block of a walkthrough bears on |
| `terms.py`     | Terms and facts                                                             |
| `lsp.py`       | The language server, on pygls                                               |
| `setup/`       | `codewalk init`, and the `AGENTS.md` section and skills it writes           |
| `render.py`    | A walkthrough as HTML, every block tagged with its Markdown line            |
| `highlight.py` | Highlights a file with Pygments, one line at a time, so any range can be cut out |
| `review.py`    | The review file, and diffs                                                  |
| `server.py`    | Starlette under uvicorn; watchfiles and server-sent events for live reload  |
| `cli.py`       | The commands, with rich-click                                               |
| `templates/`   | The pages and the markup for an embedded symbol, in Jinja                   |
| `static/`      | The page's script and styles, plain JS and CSS                              |

Tests and lint:

```bash
uv run --group dev pytest
```

```bash
uvx ruff check
```
