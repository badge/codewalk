---
weight: 10
summary: How codewalk turns Markdown that names code into a page that shows it, checks it and remembers what you've reviewed. A codewalk of codewalk.
tags: [codewalk, tooling, review]
---

# codewalk, walked through

This is a codewalk of codewalk: how it turns a Markdown file that *names* code into a
page that *shows* it, checks it and remembers what you've reviewed. Open it in codewalk
to read it properly:

```bash
codewalk serve
```

Every block of code below is the code as it stands, not a copy. Hover a name to see what
it is; click one to see it in its file. Mark a block **Reviewed** once you've read it, and
if the code changes, its badge tells you, with what changed. Press `e` to edit this from
where you are, with the Markdown and the preview scrolling together.

## Contents

1. [A walkthrough is Markdown](#1-a-walkthrough-is-markdown)
2. [The index: every symbol, from tree-sitter](#2-the-index-every-symbol-from-tree-sitter)
3. [Resolving a name](#3-resolving-a-name)
4. [A walkthrough, parsed and checked](#4-a-walkthrough-parsed-and-checked)
5. [The library: how walkthroughs relate](#5-the-library-how-walkthroughs-relate)
6. [Rendering: code in place](#6-rendering-code-in-place)
7. [Review: what you've read, and what's changed since](#7-review-what-youve-read-and-whats-changed-since)
8. [The server, kept local and live](#8-the-server-kept-local-and-live)
9. [Export: plain Markdown for everywhere else](#9-export-plain-markdown-for-everywhere-else)
10. [Proposals: code not written yet](#10-proposals-code-not-written-yet)
11. [Notes: the dialogue, in the file](#11-notes-the-dialogue-in-the-file)
12. [What's in hand, for the next run](#12-whats-in-hand-for-the-next-run)
13. [Specs: the prose beside its requirements](#13-specs-the-prose-beside-its-requirements)
14. [Terms and facts](#14-terms-and-facts)
15. [In your editor: the language server](#15-in-your-editor-the-language-server)
16. [Setting a project up](#16-setting-a-project-up)
17. [The browser side](#17-the-browser-side)
18. [Gaps, and where it could go](#18-gaps-and-where-it-could-go)

## 1. A walkthrough is Markdown

The whole design rests on one choice: a walkthrough is an ordinary Markdown file, and
everything codewalk adds is written so the file still reads well as plain text, in a
diff, in a merge request or in an editor without codewalk. There are three kinds of
reference.

A name in double brackets, like `[[Walk::problems]]`, is a symbol mentioned in the text.
It's found by the [[WIKI]] pattern, through a rule added to markdown-it's inline parser,
so it's a token like any other and never caught inside a code span:

```walk
WIKI
_wikilink
markdown
```

`[[r:some.requirement]]` is a requirement in the spec, and `[label](walk:Name)` is the
same as a double-bracket name but written as an ordinary link, for when the text wants
to say something other than the name.

A fenced block with the info string `walk` embeds code: one name a line, each shown as
its code. [[embed_line]] reads a line: the name, then optionally `> text` to show only
part of the symbol, and `sig` to show only its first line.

```walk
embed_line
```

That's all the syntax there is. Everything else follows from being able to turn a name
into a place in the code.

## 2. The index: every symbol, from tree-sitter

A [[Symbol]] is one thing a walkthrough can point at. It records three lines, not two:
`start` takes in its doc comments, decorators and requirement markers, `line` is where
the item itself begins, and `end` where it ends. So an excerpt shows a function with its
docs and markers, but its link goes straight to the definition.

```walk
Symbol
```

[[CodeIndex::refresh]] keeps the index current. It looks at each file's modification
time and parses again only the files that changed, which is why the whole of this
repository's `src/` (some 3,800 symbols) is ready in about a tenth of a second.

```walk
CodeIndex::refresh
```

**Rust** is indexed by [[index::index_file]]. Its qualified names come from the module
path, which is the file's path, as Rust has it. Impl blocks get their own entry, so a
walkthrough can show `impl Thing` whole, and their methods are filed under the type:

```walk
index::index_file::walk > elif t == "impl_item":
```

Finding the comments above an item is done by position, in [[_leading]], because
`prev_sibling` crashes the tree-sitter version this uses. A line comment's span ends at
column 0 of the *next* row, which is easy to misread as "no blank line between"; the
tests caught exactly that, when the first item in a file swallowed the file's own `//!`
comment.

```walk
_leading
```

**Python** is indexed by [[python::index_file]], into the same `::` names so a reference
reads the same whichever language it's in. Functions inside functions are indexed too,
which is how this walkthrough can show `Renderer::embed` below. A module's name comes
from its package, as Python has it:

```walk
python::module_path
```

## 3. Resolving a name

A name is any tail of a qualified name, on `::` boundaries, that matches exactly one
symbol. [[CodeIndex::resolve]] returns that symbol, or none and the candidates: every
match if it's ambiguous, the nearest few if nothing matches. Those candidates are what
the editor and `codewalk check` offer as fixes.

```walk
CodeIndex::resolve
```

The nearest are found by [[CodeIndex::nearest]]: names close to the last part, ranked by
how closely the whole reference matches the end of each. When this walkthrough's own
references went stale in a restructure, that ranking is what turned `Walk::render` into
a suggestion of `Renderer::render` rather than some Rust `runner`.

```walk
CodeIndex::nearest
```

Going the other way, [[CodeIndex::shortest_unique]] gives the shortest name to write for
a symbol. A method keeps its type, `Walk::problems` rather than `problems`, because a
name in a walkthrough is read by people before it's resolved by codewalk.

```walk
CodeIndex::shortest_unique
```

`> text` after a name is handled by [[narrow]], which cuts a symbol down to the block
that opens on the first line containing the text: by braces for Rust, by indentation for
Python. The cut-down symbol is still a `Symbol`, so everything downstream, rendering,
review and export, works on it without knowing.

```walk
narrow
```

## 4. A walkthrough, parsed and checked

A [[Walk]] is one walkthrough, parsed once with markdown-it. [[Walk::_collect]] walks
the tokens and makes a [[Ref]] for every reference, with the line it's on, and
[[Walk::_resolve]] resolves each. Along the way it reads the front matter and notes
every ordinary link to another Markdown file.

```walk
Walk::_collect
Walk::_resolve
```

> [!question] @matthew: I think the `kind` and `type`s throughout here are coming straight from `markdown_it`, and so we can't turn them into enums?
>
> Also, I clicked "Ask" on the `_collect` symbol's block, above, but this has appeared below `_resolve`, which is below it. I think that needs resolving.
>
> [!answer] @claude: Half and half. `tok.type` and `tok.tag` are markdown-it's: strings
> it makes up as it parses (`fence`, `paragraph_open`, `h2`), with no enum of its own, so
> wrapping them would mean keeping a copy of its token list in step with it. The `kind`s
> that are codewalk's own are already closed sets, as `Literal`s, which Pydantic checks
> and a type checker narrows: `Ref.kind`, `Problem.severity`, `Note.kind`,
> `Citation.state`. A `StrEnum` would add a name to import and nothing else, so I'd keep
> them as they are.
>
> The Ask was a real bug: a question always went after the whole `walk` block. Asking
> about one reference of several now splits the block under it, so the question sits
> under what it's about (`notes::ask_about`). This one I've left where it is.

Front matter is YAML, read into [[FrontMatter]]. Everything in it is optional, and keys
it doesn't know are kept rather than refused, since other tools keep their own keys in
front matter too (the spec's weights, say).

```walk
FrontMatter
```

[[Walk::problems]] is what `codewalk check` prints and the editor lists. A name that
doesn't resolve is an error, as is a link to a Markdown file that isn't there. Code that
has changed since it was reviewed is a warning: nothing's wrong with the walkthrough,
but the text around it may no longer be true.

```walk
Walk::problems
```

## 5. The library: how walkthroughs relate

Walkthroughs relate by linking to each other: in the text, like this one's link to
[codewalk's data model](data_model.md), or in the front matter's `related`.
[[Library::of]] gathers every walkthrough into a [[Summary]], then turns each link round,
so either end shows it: the data model lists this walkthrough under "Linked from"
without saying anything itself.

```walk
Library::of
Summary
```

The index page groups the summaries by folder, filters them by tag and text (kept in the
URL, so a filtered view can be shared), and draws a small map of the links. Hovering a
card lights up its place on the map, and the other way round.

## 6. Rendering: code in place

[[Renderer::render]] renders with markdown-it, but takes over its fences (so a `walk`
block becomes code), its links (so `walk:` links become symbols, and links to other
walkthroughs open in codewalk) and the double-bracket token. Alongside the HTML it
returns the data the page needs for hover cards: each symbol and requirement the
walkthrough mentions.

It also tags every block with `data-md`, the line of the Markdown it starts on. That
attribute is what lets the editor and the preview scroll together, a click in the
preview find its line, and Edit and Done keep your place.

```walk
Renderer::render
```

Each embedded symbol is drawn by [[Renderer::embed]], which cuts the symbol's lines out
of the highlighted file, strips the indent the symbol had inside its impl or class, and
works out the review state. The markup is a Jinja template,
[`web/templates/figure.html`](../codewalk/web/templates/figure.html): a caption of two rows, the
path (wrapping at each `::` rather than being cut short) with its actions, then the file
and the review badge.

```walk
Renderer::embed
```

The lines come from [[highlight_lines]], which highlights a *whole file* with Pygments
and splits it into lines. Highlighting a fragment on its own goes wrong whenever it
starts inside a string or comment; highlighting the file once (and again only when it
changes) means any range can be cut out correctly, and the side panel showing the whole
file uses the same lines. Requirement markers in comments become links here.

```walk
highlight_lines
```

## 7. Review: what you've read, and what's changed since

Review state is a file in the repository, `codewalk.review.json`, so it's committed and
travels with the code. [[ReviewState::mark]] records, for a walkthrough and a reference,
a digest of the code and the code itself:

```walk
ReviewState::mark
Symbol::digest
```

It's keyed by [[Ref::key]], the reference as written, focus and all, so two excerpts of
the same function are reviewed separately:

```walk
Ref::key
```

Keeping the text, not just the digest, is what makes the diff possible: when the digest
no longer matches, [[diff_rows]] gives the changed lines with a little context, and
collapses the rest.

```walk
diff_rows
```

Marking happens through [[App::review]], one reference or the whole walkthrough at once.
Marking the whole walkthrough also forgets references it no longer makes, so the file
doesn't fill with the dead.

```walk
App::review
```

## 8. The server, kept local and live

The server is Starlette under uvicorn, bound to 127.0.0.1 in [[server::serve]]. It
writes two things only: the review file, and a walkthrough you save from the editor, and
[[App::writable]] refuses any path that isn't a Markdown file under the walkthrough
folders.

```walk
server::serve
App::writable
```

Live reload is [[App::watch]], which follows the folders the globs look in with
watchfiles, so it hears about a change as it happens rather than polling for it. The
review file sits at the root, which is far too big to watch whole (Rust's `target/` is
in it), so the root is watched on its own, without its subfolders.

```walk
App::watch
App::watched
```

Each batch of changed files becomes a [[server::Change]], by [[App::changed]]: whether
the code or spec changed, which walkthroughs did, and whether the review file did.

```walk
App::changed
```

Each page listens on `/events`, a server-sent event stream, with a ping every 15 s so a
dropped connection is noticed. A page whose walkthrough or code changed asks for a fresh
render and swaps it in, keeping its place; an editor with unsaved changes is left alone.

```walk
make_app::events
```

## 9. Export: plain Markdown for everywhere else

Not everywhere runs codewalk. [[Walk::export]] writes a walkthrough out as plain Markdown,
each embedded symbol as a link to its file and line followed by its code, and each name
as a link. It uses the same resolved references the page does, so a focused excerpt
exports as the same part.

```walk
Walk::export
```

So `codewalk export docs/walkthrough.md out.md` gives this walkthrough as it would read
anywhere codewalk isn't, with each excerpt as the code stood when it was exported.

## 10. Proposals: code not written yet

Everything so far is about code that exists. Most of the work, though, is code that
doesn't yet: the change being argued for. A `walk proposed` block holds a draft under the
name it will have, and [[Walk::_proposal]] reads it.

```walk
Walk::_proposal
```

While the name resolves to nothing, the draft is shown as proposed, and `check` lists it
as in hand rather than broken. Once someone writes it, the name resolves, and
[[Renderer::proposal]] shows the code as written with the draft against it, and a
**Settle** button, which [[doc::settle]] carries out: the block becomes a
`walk settled` block, which [[Walk::_settled]] reads. It shows the code as written, like
any excerpt, and keeps the draft, so **as proposed** shows what was planned against
what happened.

```walk
Renderer::proposal
doc::settle
Walk::_settled
```

Inline, `[[?Name]]` marks a name to come in the same way.

**A PRD is a walkthrough with all its code proposed.** `codewalk new --prd` starts one:
the problem, with the existing code named; the outcome; the spec prose it gives rise
to, citing the requirements it adds; the code, drafted in `walk proposed` blocks with
the requirement markers it will carry; the tests, drafted the same way; and questions.
Implementing it settles each proposal in turn, and [[Walk::progress]] counts them,
proposed to written to settled, shown on the page and the index. When it's done, the
PRD has become a walkthrough of what was built, with the plan still there under each
excerpt.

```walk
Walk::progress
```

## 11. Notes: the dialogue, in the file

Questions, answers and decisions are blockquotes in the walkthrough, under what they're
about, so they show in a diff and go wherever the file goes. [[threads]] finds them, and
a [[notes::Thread]] is open while its last question has no answer or decision after it.

```walk
threads
Thread::open
```

From the browser, **Ask** on any excerpt and **Answer**, **Ask more** or **Decide** on a
thread write the note into the Markdown, as you, with [[reply]] and its sibling `ask`.

A **request** is a standing ask, not about one excerpt: like the one at the top of this
walkthrough. It stands until a `[!done]` after it says what was done, and
[[notes::Thread::request_open]] says whether it still stands.

```walk
notes::Thread::request_open
```

A note can have replies of its own, nested under it in the Markdown as a blockquote one
level deeper, so a refinement stays with the note it refines. [[parse_notes]] reads them
recursively, and a question or request anywhere in the tree keeps the thread open.

```walk
parse_notes
```

A settled thread doesn't need to stay in the text. [[notes::resolve]] takes it out:
into the changelog at the end, compacted by [[compact]] to one line (what was asked, and
how it was settled), or away altogether.

```walk
notes::resolve
compact
```

```walk
reply
```

## 12. What's in hand, for the next run

`codewalk context` is the agent's half of the dialogue: what a session should pick up.
[[brief]] gathers, for a walkthrough, its open questions (with the names they're about),
its proposals not yet written and those waiting to be settled, code changed since it was
reviewed, and broken references.

```walk
brief
```

## 13. Specs: the prose beside its requirements

A spec's prose says what we mean, and its requirements say exactly what must happen; the
requirements are written from the prose, often by an agent, and the two have to keep
saying the same thing. So the prose cites the requirements it gives rise to, and
[[cited_ids]] finds them: a requirement's ID in backticks, as these specs already do, or
`[[r:id]]`, or a `req:` link.

```walk
cited_ids
```

[[prose::view]] puts it together: the requirements the file defines, which the prose
cites and from where, which it doesn't, citations of requirements not written yet, and
for each, whether the prose or the requirement has changed since they were last
reconciled. The spec page shows each cited requirement in the margin, level with the
prose that cites it.

```walk
prose::view
```

[[prose::reconcile]] records both sides as they stand, so a later change to either shows
on the other. That's codewalk's whole part in requirements: coverage and validation stay
with tracey. Where codewalk does reach into the code, it's only to find it:
[[CodeIndex::traces]] maps each `r[impl …]` and `r[verify …]` marker to the symbol it's
on, so a requirement can show its code.

```walk
prose::reconcile
CodeIndex::traces
```

### The trail, side by side

A spec's prose gives rise to its requirements, and a walkthrough proposes, then shows,
the code that meets them. The link at each step is already there: the prose cites the
requirement, and the code, proposed or written, carries its marker. [[trail::links]]
finds, for each block of a walkthrough, the requirements it proposes, implements,
verifies or cites.

```walk
trail::links
```

So a walkthrough's margin shows, level with each block, the requirements it bears on,
each with the prose in its spec that gave rise to it: prose, requirement and code read
across one line. **Requirements** (or `m`) puts the margin away. [[trail::uses]] goes the
other way, for a spec's margin: each requirement lists the walkthroughs that propose,
implement or cite it.

```walk
trail::uses
```

## 14. Terms and facts

A term is a word with a meaning of its own here; a fact, something about the world we
rely on and don't control, with how we know it: documented, observed or assumed. Both
are defined the way tracey defines requirements, a marker on its own line and the text
after, and [[Glossary::refresh]] reads them.

```walk
Glossary::refresh
```

Terms are linked wherever they're used, without anyone citing them: [[Renderer::text]]
links the first mention of each in a paragraph, singular or plural, by the pattern
[[Glossary::mentions]] builds.

```walk
Renderer::text
Glossary::mentions
```

The glossary page lists every term and fact, grouped by the spec that defines it, with
where each is used, and a fact that nothing cites stands out.

## 15. In your editor: the language server

`codewalk lsp` brings the same checks, completion, hover and go-to-definition into an
editor. It needs no grammar of its own (the parser already knows each reference's line),
just where on a line each one is, which [[reference_at]] finds. `SYNTAX.md` writes the
syntax down as a grammar, for other tools and for anyone writing it by hand.

```walk
reference_at
lsp::describe
```

## 16. Setting a project up

[[setup::init]] writes a `codewalk.toml`, a section in `AGENTS.md` saying how
walkthroughs, specs and the glossary work, and two skills: `codewalk-propose`, to propose
a change as a walkthrough before writing it, and `codewalk-work`, to carry one forward.
Running it again replaces its section rather than adding another.

```walk
setup::init
```

## 17. The browser side

The page's behaviour is one plain script,
[`web/static/app.js`](../codewalk/web/static/app.js), with no build step and no framework, and
one stylesheet, [`web/static/app.css`](../codewalk/web/static/app.css), in light and dark. It isn't
indexed (codewalk knows Rust and Python), so it's linked rather than embedded. In order:

- **The index.** Filtering by tag and text, the map of links, and the specs.
- **Hover cards.** Each name's signature, docs and requirement markers, from the data
  `Renderer::render` returned, so hovering costs no request.
- **The file in context.** Clicking a name fetches the whole highlighted file, with an
  outline from the index, and scrolls to the symbol.
- **The palette,** on `/`, searching with [[CodeIndex::search]]: words in any order, so
  "target below" finds `TARGET_BELOW_CEILING`.
- **The editor.** A textarea and a live preview, rendered by the server, so the preview
  and the page can't disagree. Completion after `[[` or in a `walk` block. Problems are
  listed with their candidates: click one to put it in.
- **Linked scrolling.** Every block in the preview says which Markdown line it starts on.
  A hidden copy of the textarea, one element a line, says how far down the textarea each
  line sits once wrapped. Together they give pairs of positions, one in each pane;
  scrolling either pane puts the other at the matching point between the pairs either
  side. A click in the preview puts the caret on its line, level with where you clicked;
  moving the caret marks its block in the preview.

## 18. Gaps, and where it could go

Gaps:

- **Rust and Python only.** Another language is a grammar and an `index_file`.
- **A focus is the first line containing its text.** If an earlier line gains the same
  text, the excerpt moves. `codewalk check` won't notice, but the review digest will.
- **Review is shared, not per person.** The file records that *someone* reviewed the code
  as it stands, not who.
- **A digest covers doc comments too,** so a reworded comment shows as a change. That's
  arguably right: it's what the reader read.
- **Changes are diffed against what was reviewed,** not against a commit. That's the
  question a reviewer has ("what's changed since I last read this?"), but it doesn't
  say who changed it or why.
- **The editor is a textarea,** so it has no syntax highlighting of its own.

Where it could go:

- **`codewalk check` in CI,** so a walkthrough can't fall behind the code unnoticed, and
  `--strict` before a release.
- **Notes on an excerpt** from the browser, written back into the Markdown under the
  block, so a review can leave questions where they apply.

### Proposed: from the code back to walkthroughs

The context panel shows a symbol in its file, but not which walkthroughs show it. The
library could say, so the panel (and the language server's hover, in the code itself)
can list them:

```walk proposed python
Library::uses
def uses(self, ctx: Context, sym: Symbol) -> list[tuple[str, int]]:
    """The walkthroughs that show or mention `sym`, with the line of each reference."""
    out = []
    for s in self.walkthroughs:
        for ref in Walk(ctx, s.rel).refs:
            if ref.symbol and ref.symbol.file == sym.file and ref.symbol.start <= sym.line <= ref.symbol.end:
                out.append((s.rel, ref.line))
    return out
```

> [!question] @claude: Parsing every walkthrough on each call is fine for two, but not
> for fifty. Should the library keep an index from symbol to references, rebuilt when a
> walkthrough changes, or is that premature until there are more walkthroughs?
>
> [!question] @matthew: That makes sense. I think it's reasonable to assume:
> - One codewalk instance per project
> - Each project is a git repo
>
> As a result, I would probably create a `.codewalk/` dir in the repo root (add it to `.gitignore` or not? I'm not sure), and store a little sqlite DB in there to track this kind of stuff).
>
> [!answer] @claude: Agreed on both assumptions, and on `.codewalk/` with SQLite (the
> standard library's, so nothing new to install). I'd ignore it in git: everything in it
> is worked out from files that are committed, so it can always be rebuilt, and a binary
> file that changes on every read would conflict in every branch. Review state is
> different, since it's a record of what people did and can't be rebuilt, so
> `codewalk.review.json` stays where it is, committed. `codewalk init` would add
> `.codewalk/` to `.gitignore`. In the DB: one row for each reference (walkthrough, line,
> symbol's file and span, requirement), rewritten for a walkthrough when its mtime moves,
> which is what `uses` reads.
