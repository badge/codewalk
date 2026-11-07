---
title: "Authoring PRDs"
summary: "A PRD goes from the problem to prose, a spec and the shape of the code, in stages, in one file that reads on its own, with its spec shown against the spec as it stands."
kind: prd
stage: spec
tags: [prd, spec]
related: ["../walkthrough.md"]
---

# Authoring PRDs

A PRD is how we agree a change before making it: the problem, what we'll do about it, the
spec that follows, and the shape of the code. This one says how a PRD should be written
in codewalk, and what codewalk needs to support it.

## The problem

codewalk can start a PRD with `codewalk new PATH --title T --prd`, which writes a
walkthrough from a template with `kind: prd` in its front matter, and it counts a PRD's
progress by its proposals:

```walk
cli::new
FrontMatter::kind
Walk::progress
```

That's all it knows about PRDs, and it gets the order wrong:

- **It starts with code.** The template has sections for the spec and the code, with a
  sample proposal and a sample question, both of which count as work in hand from the
  moment it's written. Progress is measured only in code. Nothing knows the stages a PRD
  goes through, so nothing stops one jumping to code before the spec is agreed: the first
  draft of this PRD did exactly that.
- **A PRD can't hold a spec.** Requirements, terms and facts are read only from the spec's
  files. A requirement written in a PRD isn't read at all, and a term it defines that the
  spec already has is an error, defined twice. So a PRD either describes its changes to
  the spec, leaving the reader to imagine them, or makes them in the spec, so it can only
  be read with the rest of the repository open beside it. Neither reads on its own.
- **codewalk can't read a versioned requirement.** tracey marks a changed requirement by
  bumping its version ([[f:tracey.versions]]), but codewalk doesn't recognise `r[id+2]`
  in a spec or `r[impl id+2]` in code.
- **`codewalk check` doesn't check a spec.** It checks walkthroughs only, so a term cited
  and not defined in a spec file is reported only on that file's page.
- **A change to existing code can't be proposed.** A `walk proposed` block whose name
  exists reads as written at once, so it can only propose new code.
- **The browser can't start a PRD.** It can ask, answer, agree, settle, review and
  reconcile, but there's no way to begin one there.

## What we want

### A PRD reads on its own

Everything a PRD proposes is in it, so someone who knows the codebase can read it and
nothing else, and know what will change and why. Nothing outside it changes while it's
proposed: not the spec, not the code. Once the work is done it may go stale, and that's
fine: by then the spec and the code say what's true, and the PRD is the record of why.

### In stages

A PRD is written in five stages, each broadly agreed before the next is begun in
earnest:

1. **The problem.** Why we want a change: a feature, a fix, whatever it is. It can name the
   code it's about as it stands.
2. **The prose.** What we'll do about it, in words, and the terms and facts the rest of
   the PRD needs, which can be defined while the prose is still being written. Rough
   examples are fine; proposals aren't.
3. **The spec.** The requirements that follow from the prose, going back and forth between
   the two until the spec is something we can work from.
4. **The code.** The shape of the code and of its tests, in outline (below).
5. **The work.** The change itself: the prose and requirements move into the spec, the
   code is written, and the PRD is updated to name the code as written.

Going back is normal: a question about the spec can send the prose back for another look.
A PRD records its stage in its front matter, `stage: prose`, which codewalk shows on the
index, on its page and in `codewalk context` (`prd.stage`), and which the person sets
from its page when they agree a stage (`prd.stage-set`). The stage gates what belongs to
later stages, not earlier ones: while a PRD is at the prose, no requirements or code are
written into it; once it's at the code, the prose and the spec can still be revised
(`prd.stage-gate`). It's a guide to what comes next, not a lock: the prose needn't
be final before the spec is begun, only broadly agreed.

### Its spec, against the spec as it stands

A PRD's requirements are written in it as they'll read in the spec, and read as its own
proposals, not the spec's (`prd.requirements`). That means codewalk has to read a
requirement's version, in the spec and in code (`spec.prefix`, `spec.traces`). Each is
shown against the spec as it stands (`prd.compare`). A requirement whose ID the spec
doesn't have is new. One whose ID it has, with the version bumped, is a change, and is
shown with the old text beside the new. One with an ID the spec has and the same text is
quoted for context, and is shown as such; one with an ID the spec has, changed text and no
new version is an error. A requirement the PRD removes is listed as removed.

Terms and facts work the same way: a PRD's definition of a word the spec already defines is
a proposed change to it, shown against it, not a second definition (`prd.terms`,
`term.errors`). This PRD has one: a
[[t:prd]] is no longer "a walkthrough whose code is all proposed", but a walkthrough with
`kind: prd` that proposes a change in stages, from the problem to the code, and reads on
its own. (It's written here rather than as a definition, since until this is done a
second definition is an error.)

The spec view, the glossary and tracey go on reading only the spec itself, so a PRD's
proposals don't count until they're moved into it, at the work. `codewalk check` checks a
PRD's spec as it checks its references: a changed requirement without a new version, or a
term cited and defined nowhere, is an error (`prd.check`).

### Its code, in outline

At the code stage a PRD shows the shape of the code, as much of it as it takes to agree
it, and no more. Changes to the data model are shown in full. Code that implements a
requirement carries its marker, and is shown in full where it's intricate enough to be
worth agreeing line by line, or by its signature where it's routine. Helpers that
implement nothing aren't proposed. Tests are proposed the same way, by the requirement
each verifies.

New code is proposed in a `walk proposed` block, as now. A change to code that exists is
proposed in a `walk proposed change` block, which shows the draft against the code as it
is, and stays proposed until it's settled (`proposal.change`).

### Wherever it's written

A PRD is Markdown, so it can be written anywhere: in the browser, in an editor, by an agent,
with or without codewalk running. The browser adds what an editor can't: everything shown
in place, and a person's part of the conversation (asking, answering, agreeing, setting
the stage) a click away.

In the browser, a person starts a PRD from the index with **New PRD**: a title and, in
their own words, what they want. codewalk writes the PRD at `docs/prd/` and the title's
slug, at the problem stage, from a template with a section for each stage and no samples
(`prd.template`), with what they asked for as a standing request at the top, and opens it
(`prd.start`). An agent working
in the same folder finds the request with `codewalk context`, and writes into the stage
the PRD is at. codewalk is for local use: the server and the agent on the person's own
machine, in the same folder.

PRDs have nothing to do with branches or worktrees: a PRD is a file, and the process
neither creates nor manages either. Where the work is done is up to whoever does it.

### A changelog to write in

Settled threads go into the changelog at the end, each compacted to a line. Anything else
worth recording about how the PRD got where it is can be written there too, by hand.

## The spec

The requirements that follow from the prose, as they'll read in the spec: new ones, and
changes to existing ones with their versions bumped. Once agreed, the new `prd.*` ones go
in a spec file of their own, and each changed one replaces its earlier version where it
is.

### Stages

r[prd.template]
`codewalk new PATH --title T --prd` MUST write a PRD with `kind: prd` and `stage: problem`
in its front matter and a section for each stage, and with no `walk proposed` block and no
note.

r[prd.stage]
A PRD's stage MUST be read from `stage` in its front matter, one of `problem`, `prose`,
`spec`, `code` and `work`, or `problem` if it has none, and MUST be shown with the PRD on
the index, on its page, and in `codewalk context`.

r[prd.stage-set]
A PRD's page MUST let a person set its stage, writing it into the front matter.

r[prd.stage-gate]
`codewalk check` MUST warn of a requirement written in a PRD before its stage is `spec`,
and of a proposal written in a PRD before its stage is `code`; and `codewalk context` MUST
say, for each PRD, what its stage allows to be written.

### Its spec

r[spec.prefix+2]
A line consisting only of `prefix[id]` or `prefix[id+N]`, where prefix is `r` or the name
of a spec in tracey's config, MUST be read as a requirement, of version N or else 1, with
the paragraph after it as its text. One with a prefix other than `r` MUST be known as
`prefix:id`, and written without the prefix, in a file of the same spec, MUST resolve to
it.

r[spec.traces+2]
A comment containing `prefix[impl id]` or `prefix[verify id]`, with or without `+N` after
the ID, MUST be read as a trace of that requirement, of version N or else 1, on the
smallest symbol around it, or the symbol it's directly above.

r[prd.requirements]
A requirement marker on a line of its own in a PRD MUST be read as a requirement the PRD
proposes, with the paragraph after it as its text, and MUST NOT be read as part of the
spec: not by the spec view, the glossary, the traces or the margin of another walkthrough.

r[prd.compare]
Each requirement a PRD proposes MUST be shown against the spec as it stands: as new if the
spec has no requirement with its ID; as changed, with the spec's text against its own, if
its version is greater than the spec's and it has text; as removed if its version is
greater and it has none; and as quoted if its version and its text are the spec's. One
whose version isn't greater than the spec's and whose text differs from it MUST be
reported as an error.

r[prd.terms]
A term or fact defined in a PRD MUST be read as a definition the PRD proposes: shown as new,
or against the spec's definition of the same ID as changed, and not as part of the spec.

r[term.errors+2]
A term or fact defined more than once in the spec, or cited and defined neither in the
spec nor in the PRD citing it, MUST be reported as an error. A PRD's definition of one the
spec defines isn't a second definition.

r[prd.check]
`codewalk check` MUST check each PRD's requirements and definitions, reporting the errors
`prd.compare` and `term.errors` describe with their file and line, and exiting non-zero on
one, as it does for a broken reference.

### Its code

r[proposal.change]
A `walk proposed change` block MUST be read as a change proposed to the symbol it names,
showing its draft against the symbol's code as it is, and counted as proposed until it's
settled; settling it MUST turn it into a `walk settled` block, keeping the draft. A
change to a name that doesn't resolve MUST be reported as broken.

### Starting one

r[prd.start]
The index MUST offer to start a PRD from a title and what the person wants: it MUST write
the template at `docs/prd/` and the title's slug, with what they want as a `[!request]`
signed as them at the top, and open it, refusing if that file exists. It MUST NOT create
or change a branch or a worktree.

## Terms

t[stage]
Where a PRD is in its lifecycle: the problem, the prose, the spec, the code or the work,
recorded in its front matter as `stage`.

## Facts

f[tracey.versions] documented
A requirement's ID can carry a version, `r[id+2]`; without one it's version 1. When a
requirement's text changes its version is bumped, and code naming an older version,
`r[impl id]`, is stale, and not counted as covered until it's updated and its marker
bumped. (tracey's documentation, on versioning.)

## Questions

> [!question] @claude: How should a PRD say it removes a requirement? I've written it in
> `prd.compare` as the marker with its version bumped and no text after it, `r[id+2]` on
> its own, which says "the next version of this is nothing". The alternative is a word,
> such as `r[id+2] removed`, which is plainer to read but is a new piece of syntax.

> [!question] @claude: `prd.stage-gate` makes a requirement or a proposal written before
> its stage a warning from `codewalk check`, not an error, so a PRD that's gone back a
> stage, or is being written a little ahead, still checks. Is a warning right, or should
> the gate be stricter, or only advice in `codewalk context`?

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07 (to the spec stage): **question** @claude: Is this PRD's prose broadly
  agreed, so it can move to `stage: spec`? → @matthew, in conversation: Yes, we can move
  to the spec stage. Set `stage: spec`, the requirements written in [The spec](#the-spec),
  and the prose made to cite them.
- 2026-11-07 (how much code): **note** @matthew: Don't be too prescriptive about the code:
  a gnarly piece can be shown whole, and boilerplate by its signature. → Written into
  [Its code, in outline](#its-code-in-outline).
- 2026-11-07 (agreeing the prose): **question** @claude: Is the prose agreed, so this PRD
  moves to the spec stage? → **answer** @matthew: Prose should be broadly agreed before
  the spec stage proper, but flexibly: terms and facts can be defined at the prose stage.
  Written into [In stages](#in-stages).
- 2026-11-07: Tidied into a PRD to agree: the lifecycle folded into
  [In stages](#in-stages), the findings from writing it by hand folded into
  [the problem](#the-problem), and the settled threads below compacted into this
  changelog. Set to `stage: prose`.
- 2026-11-07 (worktrees): **question** @claude: One PRD per checkout, or a git worktree
  each? → **decision** @matthew: PRDs are orthogonal to worktrees, and the PRD process
  neither creates nor manages worktrees. (This replaces an earlier decision that each PRD
  should get a worktree.)
- 2026-11-07 (where it's written): **note** @matthew: Started, written and worked wherever
  the user wants: in the browser, or entirely in an IDE, without codewalk running.
- 2026-11-07 (stages): **question** @claude: How does a PRD say which stage it's in? →
  **answer** @matthew: In its front matter; the stage gates later stages' actions, not
  earlier stages'.
- 2026-11-07 (changing existing code): **question** @claude: Should a proposal for a name
  that exists show its draft against the code, and stay proposed until settled? →
  **answer** @matthew: Yes, marked as `walk proposed change`.
- 2026-11-07 (tests): **question** @claude: Should `sources` include `tests/`, so proposed
  tests can settle? → **answer** @matthew: Yes, by default for Python projects.
  `codewalk init` already did; codewalk's own config now does (e387266).
- 2026-11-07 (after merging): **question** @claude: Once a PRD's branch is merged, should
  it record the commit its spec changes were compared against? Withdrawn: it only mattered
  while a PRD changed the spec on a branch.
- 2026-11-07 (telling the agent): **question** @claude: Should `codewalk context --wait`
  return when a person answers, so an agent can wait for them? → **answer** @matthew:
  Keep it simple, and iterate as we need.
- 2026-11-07 (a server per worktree): **question** @claude: One server per worktree, on
  its own port? → **answer** @matthew: codewalk is for local use, much like a live pull
  request: the server on your machine and the agent in the same folder. Don't solve
  remote use.
- 2026-11-07 (where a PRD's spec goes): **question** @claude: A branch with the spec edited
  in place, or a folder of drafts? → **note** @matthew: Neither: a PRD should read on its
  own, so nothing outside it changes while it's proposed, and its requirements are
  compared with the spec as it stands, using tracey's versioning.
- 2026-11-07 (code too soon): **note** @matthew: This PRD jumped the gun: prose first, then
  the spec, then code in outline, as in a lifecycle of five stages. → Set back to the
  prose stage: the spec written in place in `docs/spec/` taken out and what it changed
  there put back, and the drafted spec, code and tests taken out of the PRD (they're at
  711c4b7).
- 2026-11-07 (`[!note]` not shown): **note** @matthew: A `[!note]` typed in the editor
  didn't show when rendered. → Fixed: `note` and `request` had become terms, and linking
  the word broke the marker (e252a17).
- 2026-11-07: **note** @claude: The first PRD, written mostly by hand, to find out how writing one should go. → **note** @matthew: The entire process should run through the UI, in concert with an agent like Claude running in its own application alongside.
