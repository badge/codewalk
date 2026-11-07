---
weight: 25
---

## PRDs

A PRD is how we agree a change before making it: the problem, what we'll do about it, the
spec that follows, and the shape of the code. It's a codewalk, with `kind: prd` in its
front matter.

### It reads on its own

Everything a PRD proposes is in it, so someone who knows the codebase can read it and
nothing else, and know what will change and why. Nothing outside it changes while it's
proposed: not the spec, not the code. Once the work is done it may go stale, and that's
fine: by then the spec and the code say what's true, and the PRD is the record of why.

### In stages

A PRD is written in five stages, each broadly agreed before the next is begun in earnest:

1. **The problem.** Why we want a change: a feature, a fix, whatever it is. It can name the
   code it's about as it stands.
2. **The prose.** What we'll do about it, in words, and the terms and facts the rest of
   the PRD needs, which can be defined while the prose is still being written. Rough
   examples are fine; proposals aren't.
3. **The spec.** The requirements that follow from the prose, going back and forth between
   the two until the spec is something we can work from.
4. **The code.** The shape of the code and of its tests, in outline.
5. **The work.** The change itself: the prose and requirements move into the spec, the
   code is written, and the PRD is updated to name the code as written.

Going back is normal: a question about the spec can send the prose back for another look.
A PRD records its stage in its front matter, `stage: prose`, which codewalk shows on the
index, on its page and in `codewalk context` (`prd.stage`), and which the person sets
from its page when they agree a stage (`prd.stage-set`). The stage gates what belongs to
later stages, not earlier ones: while a PRD is at the prose, no requirements or code are
written into it; once it's at the code, the prose and the spec can still be revised
(`prd.stage-gate`). It's a guide to what comes next, not a lock: the prose needn't be
final before the spec is begun, only broadly agreed.

### Its spec, against the spec as it stands

A PRD's requirements are written in it as they'll read in the spec, and read as its own
proposals, not the spec's (`prd.requirements`). Each is shown against the spec as it
stands (`prd.compare`). A requirement whose ID the spec doesn't have is new. One whose ID
it has, with the version bumped, is a change, and is shown with the old text beside the
new. One with an ID the spec has and the same text is quoted for context, and is shown as
such; one with an ID the spec has, changed text and no new version is an error. A
requirement the PRD removes is written as its marker with the version bumped and the word
`removed` after it, `r[id+2] removed`, and is listed as removed.

Terms and facts work the same way: a PRD's definition of a word the spec already defines is
a proposed change to it, shown against it, not a second definition (`prd.terms`).

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
each verifies. New code is proposed in a `walk proposed` block; a change to code that
exists in a `walk proposed change` block.

### Wherever it's written

A PRD is Markdown, so it can be written anywhere: in the browser, in an editor, by an
agent, with or without codewalk running. The browser adds what an editor can't:
everything shown in place, and a person's part of the conversation (asking, answering,
agreeing, setting the stage) a click away.

`codewalk new PATH --title T --prd` starts one from a template with a section for each
stage and no samples (`prd.template`). In the browser, a person starts one from the index
with **New PRD**: a title and, in their own words, what they want. codewalk writes the
PRD at `docs/prd/` and the title's slug, with what they asked for as a standing request at
the top, and opens it (`prd.start`). An agent working in the same folder finds the
request with `codewalk context`, and writes into the stage the PRD is at. codewalk is for
local use: the server and the agent on the person's own machine, in the same folder.

PRDs have nothing to do with branches or worktrees: a PRD is a file, and the process
neither creates nor manages either. Where the work is done is up to whoever does it.

### A changelog to write in

Settled threads go into the changelog at the end, each compacted to a line. Anything else
worth recording about how the PRD got where it is can be written there too, by hand.

## Terms

t[prd]
A codewalk with `kind: prd` that proposes a change in stages, from the problem to the
code, and reads on its own.

t[stage]
Where a PRD is in its lifecycle: the problem, the prose, the spec, the code or the work,
recorded in its front matter as `stage`.

## Requirements

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

r[prd.requirements]
A requirement marker on a line of its own in a PRD MUST be read as a requirement the PRD
proposes, with the paragraph after it as its text, and one followed by the word `removed`,
`r[id+N] removed`, as a requirement it removes. Neither MUST be read as part of the spec:
not by the spec view, the glossary, the traces or the margin of another codewalk.

r[prd.compare]
Each requirement a PRD proposes MUST be shown against the spec as it stands: as new if the
spec has no requirement with its ID; as changed, with the spec's text against its own, if
its version is greater than the spec's; as removed, with the spec's text, if it's written
`removed`; and as quoted if its version and its text are the spec's. One whose version
isn't greater than the spec's and whose text differs from it, or that removes a
requirement the spec doesn't have, MUST be reported as an error.

r[prd.terms]
A term or fact defined in a PRD MUST be read as a definition the PRD proposes: shown as new,
or against the spec's definition of the same ID as changed, and not as part of the spec.

r[prd.check]
`codewalk check` MUST check each PRD's requirements and definitions, reporting the errors
`prd.compare` and `term.errors` describe with their file and line, and exiting non-zero on
one, as it does for a broken reference.

r[prd.start]
The index MUST offer to start a PRD from a title and what the person wants: it MUST write
the template at `docs/prd/` and the title's slug, with what they want as a `[!request]`
signed as them at the top, and open it, refusing if that file exists. It MUST NOT create
or change a branch or a worktree.
