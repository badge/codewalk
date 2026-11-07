---
weight: 30
summary: The words codewalk uses with a meaning of their own, and what it relies on from tools it doesn't control.
---

# Glossary

Words with a meaning of their own in codewalk, and facts it relies on about the tools it
works with. codewalk links each term wherever its words appear in prose, so any use of
one can be hovered for what it means.

## Terms

t[excerpt]
The code a line of a `walk` block shows: a symbol as it stands in its file, all of it,
part of it (`> text`), or its outline (`sig`).

t[thread]
The notes in one blockquote: questions, answers, decisions, requests and what was done,
with replies nested under the note they refine. It's about the block above it.

t[proposal]
Code drafted in a `walk proposed` block under the name it will have, before it's
written. Once written, it's settled: the block keeps the draft beside the code.

t[drift]
A requirement or the prose citing it having changed since the two were last reconciled,
so one may no longer say what the other does.

t[trail]
The path from a block of a walkthrough to the requirements it proposes, implements,
verifies or cites, and from each of those to the prose in its spec it comes from.

## Facts

f[tracey.prefix] documented
tracey infers a spec's prefix, the `r` in `r[id]`, from the requirement markers in its
files, rather than from the spec's name. (tracey's documentation, on configuration.)

f[markdown-it.token-types] observed
markdown-it-py's token types (`fence`, `paragraph_open`) are plain strings it makes up as
it parses, with no enum of its own. Observed in markdown-it-py 3, November 2026.
