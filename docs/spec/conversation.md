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
one can't (`note.resolve-open`). A settled thread can still be added to, since an answer
is often followed by a decision to go with it (`note.add-settled`).

### Proposals

Code that doesn't exist yet can be proposed: drafted in a `walk proposed` block under the
name it will have (`proposal.draft`). Until the name exists, it's in hand, not broken
(`proposal.pending`). A person agrees a proposal from the browser: a decision, signed as
them, in the thread under it, which starts one if there's none. Until it's written, the
proposal is then agreed, and says so on the page and in `codewalk context`, so the agent
knows it can be written (`proposal.agree`). Once it does, the proposal shows what was written against the
draft, and can be settled: the block becomes `walk settled`, keeping the draft, so what
was planned and what was done stay side by side (`proposal.settle`). A walkthrough's
progress is how much of what it proposes is written and settled (`proposal.progress`).

A change to code that exists is proposed in a `walk proposed change` block, under the name
it has. It shows what there is, then what there will be: the difference from the code as
it is to the draft. It stays proposed until it's settled, since code that exists can't
say whether the change has been made (`proposal.change`).

### What's in hand

At the start of a session, `codewalk context` says what's in hand across every
walkthrough and spec: standing requests, open questions, proposals not written, proposals written
and not settled, code changed since review, and broken references, each with where it is
and what it's about (`context.brief`).

## Terms

t[note]
A paragraph in a blockquote that starts with its kind, `[!question]`, `[!answer]`,
`[!decision]`, `[!note]`, `[!request]` or `[!done]`, and optionally who it's from.

t[thread]
The notes in one blockquote: questions, answers, decisions, requests and what was done,
with replies nested under the note they refine. It's about the block above it, and it's
open while any note in it, at any depth, is open.

t[request]
A note asking for something that applies throughout rather than once. It stays open
until a done after it.

t[proposal]
Code drafted in a `walk proposed` block under the name it will have, before it's
written. Once written, it's settled: the block keeps the draft beside the code.

t[settled]
Finished with: a thread when nothing in it is open, and a proposal when its block is
`walk settled`, keeping the draft beside the code as it was written.

t[in-hand]
Begun and not finished: an open question or request, a proposal not written or not
settled, or code changed since its review. `codewalk context` says what's in hand.

t[changelog]
The `## Changelog` section at the end of a walkthrough, where settled threads go, one
line each, newest first.

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

r[note.add-settled]
A settled thread MUST offer, besides resolving it, to add an answer, a question or a
decision to it.

r[proposal.draft]
A `walk proposed` block MUST be read as a proposal: its first line the name the code will
have, the rest its draft.

r[proposal.pending]
A proposal whose name doesn't resolve MUST be reported as in hand, not as broken.

r[proposal.agree]
Agreeing a proposal from the browser MUST write a `[!decision]` signed as the person into
the thread directly after its block, starting one there if there's none. A proposal not
yet written, with a decision in that thread, MUST be shown as agreed, and `codewalk
context` MUST list it as agreed, with the decision.

r[proposal.settle]
Settling a written proposal MUST turn its block into `walk settled`, keeping the draft,
and a settled block MUST show the code as it is, with the difference from its draft.

r[proposal.change]
A `walk proposed change` block MUST be read as a change proposed to the symbol it names,
showing the difference from the symbol's code as it is to the draft, so what the change
adds shows as added and what it takes out as removed, and counted as proposed until it's
settled; settling it MUST turn it into a `walk settled` block, keeping the draft. A
change to a name that doesn't resolve MUST be reported as broken.

r[proposal.progress]
A walkthrough's progress MUST be counted as how many of its proposals are not written,
written but not settled, and settled.

r[context.brief]
`codewalk context` MUST list, for each walkthrough and spec file with any, its open requests, open
questions, unwritten proposals, written but unsettled proposals, code changed since
review and broken references, each with its line and the names it's about.
