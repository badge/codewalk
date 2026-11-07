---
weight: 20
---

## The conversation

A walkthrough is also where the conversation about the code happens, so that it's still
there in the next session, beside what it's about, and not lost in a chat.

### Notes

A note is a blockquote that starts with its kind and, optionally, who it's from:
`> [!question] @matthew: …` (`note.syntax`). The kinds are question, answer, decision,
note, request and done. Notes in one blockquote are a thread, about the block above it.
A question stays open until an answer or decision after it, and a request, a standing
ask for something that applies throughout, until a done (`note.open`). A reply to one
note nests under it, a blockquote deeper, so a refinement stays with what it refines;
anything open at any depth keeps the thread open (`note.replies`).

Notes can be written in the Markdown or from the browser, where they're signed as the
author in the config or from git (`note.write`). Asking about one excerpt of several in a
block puts the question directly under that excerpt (`note.ask-here`). A settled thread
can leave the text: into a changelog at the end of the walkthrough, compacted to a line
of what was asked and how it was settled, or removed altogether (`note.resolve`). An open
one can't (`note.resolve-open`).

### Proposals

Code that doesn't exist yet can be proposed: drafted in a `walk proposed` block under the
name it will have (`proposal.draft`). Until the name exists, it's in hand, not broken
(`proposal.pending`). Once it does, the proposal shows what was written against the
draft, and can be settled: the block becomes `walk settled`, keeping the draft, so what
was planned and what was done stay side by side (`proposal.settle`). A PRD is a
walkthrough whose code is all proposed, so its progress is how much is settled
(`proposal.progress`).

### What's in hand

At the start of a session, `codewalk context` says what's in hand across every
walkthrough and spec: standing requests, open questions, proposals not written, proposals written
and not settled, code changed since review, and broken references, each with where it is
and what it's about (`context.brief`).

## Requirements

r[note.syntax]
A paragraph in a blockquote starting `[!kind]`, where kind is question, answer, decision,
note, request or done, optionally followed by `@author` and a colon, MUST be read as a
note. A blockquote whose first paragraph isn't one MUST NOT be read as a thread.

r[note.open]
A question MUST be open until a later note in its thread at its level, or a reply to it,
is an answer or decision. A request MUST be open until such a note is done.

r[note.replies]
A blockquote nested in a thread, directly after a note, MUST be read as replies to that
note, and a thread MUST be open while any note in it, at any depth, is open.

r[note.write]
A note written from the browser MUST be written into the Markdown, signed with the
config's `author`, or else the first word of git's `user.name` in lower case.

r[note.ask-here]
A question asked about one reference in a `walk` block MUST be written directly after
that reference, splitting the block in two if more of it follows.

r[note.resolve]
A settled thread MUST be removable, either altogether or into a `## Changelog` section at
the end of the walkthrough, newest first, as one line giving its date, what it was about,
its first note's first sentence, the settling note's first sentence and how many notes
came between.

r[note.resolve-open]
Resolving a thread that's open MUST be refused.

r[proposal.draft]
A `walk proposed` block MUST be read as a proposal: its first line the name the code will
have, the rest its draft.

r[proposal.pending]
A proposal whose name doesn't resolve MUST be reported as in hand, not as broken.

r[proposal.settle]
Settling a written proposal MUST turn its block into `walk settled`, keeping the draft,
and a settled block MUST show the code as it is, with the difference from its draft.

r[proposal.progress]
A walkthrough's progress MUST be counted as how many of its proposals are not written,
written but not settled, and settled.

r[context.brief]
`codewalk context` MUST list, for each walkthrough and spec file with any, its open requests, open
questions, unwritten proposals, written but unsettled proposals, code changed since
review and broken references, each with its line and the names it's about.
