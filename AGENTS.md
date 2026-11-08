# Working on codewalk

codewalk is a local tool for walking through code in Markdown: it checks every name a
codewalk makes against the code, shows the code as it stands, and keeps the
conversation about it in the file. [`README.md`](README.md) says what it does;
[`docs/codewalk.md`](docs/codewalk.md) says how, and
[`docs/data_model.md`](docs/data_model.md) how the pieces relate. Read the codewalk
before changing anything substantial.

## The spec comes first

[`docs/spec/`](docs/spec/README.md) is what codewalk must do: prose saying what we mean,
agreed by people, then the requirements that follow from it, each cited from the prose.
tracey holds the code to it (`.config/tracey/config.styx`).

- A change in behaviour starts in the spec's prose. Change the prose, then the
  requirements to follow, then the code. Don't change the prose to match the code
  without asking: the prose is the people's.
- Mark the code that implements a requirement with `# r[impl id]` (`// r[impl id]` in
  JavaScript) directly above its definition, and the test that verifies it with
  `# r[verify id]`. Before calling it done, the spec view shows no drift you didn't
  mean, and tracey shows no errors:

```bash
tracey query . validate
```

## Layout

| Where             | What                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| `codewalk/code/`  | Indexing Rust and Python into symbols; highlighting                      |
| `codewalk/walk/`  | A codewalk parsed and checked; notes; review state; the library       |
| `codewalk/spec/`  | Requirements, tracey's config, prose against spec, the trail, the glossary |
| `codewalk/web/`   | The server, rendering, templates and static JS and CSS                   |
| `codewalk/cli.py`, `config.py`, `lsp.py`, `setup/` | The commands, the config, the language server, `codewalk init` |
| `tests/`          | One test module for codewalk, and one checking the README's examples     |
| `docs/`           | codewalk's own codewalks, spec and glossary                           |

Imports within the package are absolute (`from codewalk.walk.doc import Walk`).

## Conventions

- **Docstrings are NumPy style**, with Parameters, Returns and Raises sections. A class
  whose `__init__` takes arguments documents them in the class's docstring, since that's
  what `sig` shows.
- **Pydantic models** for data; plain classes for things that hold state and do work.
- **Tests** are named for the behaviour they check, as a sentence
  (`test_a_name_shared_by_several_symbols_is_ambiguous_with_each_as_a_candidate`), and
  work on a small repository of their own in a temporary folder, not on this one. The
  README's examples are the exception: they name codewalk's own code, and
  `tests/test_readme.py` checks they still resolve.
- **The README dogfoods codewalk.** Every example names codewalk's own code; nothing
  from another project.
- **Plain JS and CSS**, no build step. Colours are CSS variables, for light and dark.
- **Prose** (docs, docstrings, comments, notes): plain British English, short sentences,
  no jargon where a plain word will do.

## Checks

```bash
uv run --group dev pytest
```

```bash
uvx ruff check && uvx ruff format --check
```

```bash
uv run codewalk check
```

Run the server from this folder to see a change (`uv run codewalk serve --port 4472`),
and stop it with Ctrl-C when done.

<!-- codewalk:start (written by `codewalk init`; edit freely, init replaces it) -->
## Codewalks, specs and the glossary: codewalk

Codewalks are Markdown files that name the code they talk about rather than pasting
it, and [codewalk](README.md) checks every name resolves and shows each one's
code as it stands. They're how a change is proposed, reviewed and explained, and they
carry the conversation about it from one session to the next. The syntax is in
[`SYNTAX.md`](SYNTAX.md).

**At the start of a session**, read what's in hand, and do any standing requests
(`[!request]`, at the top of a codewalk) before anything else:

```bash
uv run codewalk context
```

It lists standing requests, open questions, code proposed but not written, proposals
written and waiting to be settled, code changed since someone reviewed it, and broken
references.

**Before a change of any size**, write or update a codewalk proposing it: what will
change and why, with the existing code named in `walk` blocks and the new code drafted in
`walk proposed` blocks under the name it will have, with the requirement markers it will
carry. A PRD is such a codewalk, written in stages (the problem, the prose, the spec,
the code, the work), with its spec kept in it until the work: start one with
`uv run codewalk new PATH --title T --prd`, and write only what its `stage` allows, which
`uv run codewalk context` says. A person moves it on from one stage to the next.
Ask what you need to know as `> [!question] @agent: …` in the codewalk, under what
it's about, and stop for an answer if you can't go on without one.

**While making it**, keep the codewalk true: once a proposed name exists, check what
was written against the draft and settle the block (`walk proposed` becomes
`walk settled`, keeping the draft); explain in the prose where they differ. When you've
done a standing request, add `> [!done] @agent: …` to it, saying what you did. Answer
questions in their thread with `> [!answer] @agent: …`; record what was decided with
`[!decision]` if a person decided it.

**Specs.** The prose at the top of a spec says what we mean; the requirements say exactly
what must happen. When the prose changes, change the requirements to follow, and cite
each requirement from the prose that gives rise to it, as its ID in backticks. Cite one
that doesn't exist yet as `[[r:id]]`, and write it. Tracey still checks coverage.

**Terms and facts.** Define a word with a meaning of its own here as `r[term.word]` and
something we rely on about the world as `r[fact.id] documented|observed|assumed`, each on
its own line with its text after, under `## Terms` or `## Facts` in the spec it belongs to
(the top-level spec, for words used throughout). Cite them with
`[[t:word]]` and `[[f:id]]`. Don't mark a fact documented or observed unless it is.

**Never** mark code reviewed (that's a person's to do), resolve a question a person asked
by deciding it yourself, or delete a thread.

**Before calling it done:**

```bash
uv run codewalk check
```
<!-- codewalk:end -->
