---
weight: 30
---

## Specs and terms

codewalk works beside tracey. Tracey holds the code to the spec: which requirements are
implemented and verified, and where. codewalk shows the spec beside the prose it comes
from, and beside the codewalks that use it. Everything about coverage stays with
tracey.

### Requirements

The spec is the Markdown that tracey's config names as specs, and any more in
`codewalk.toml` (`spec.files`). A requirement is a line of its own, `r[id]`, or with the
name of a spec in tracey's config as its prefix; one with a spec's name is known by both,
since two specs can share an ID (`spec.prefix`). A requirement whose text changes has its
version bumped, `r[id+2]`, so code written against the old text can be found
([[f:tracey.versions]]). The code names a requirement in a comment, `r[impl id]` or
`r[verify id]`, with the version it was written against if it isn't the first,
`r[impl id+2]`, and codewalk finds the symbol each is on (`spec.traces`), so a
requirement in a codewalk can show its code.

### Prose beside the spec

A spec file opens with prose, written and agreed by people, and the requirements follow
from it. The prose cites each requirement it gives rise to, as the ID in backticks,
`[[r:id]]`, or a `req:` link (`spec.cite`). The spec view shows each cited requirement
beside the prose that cites it, and says which requirements no prose cites, and which
citations name requirements not written yet (`spec.view`). Reconciling a requirement with
its prose records both as they stand; when either changes after that, the view says
which (`spec.drift`).

From a codewalk, each block's requirements, whether it proposes, implements, verifies
or cites them, are shown in its margin, and each one leads to its spec at the prose it
comes from (`spec.trail`).

### Terms and facts

A word with a meaning of its own here is a term, and something relied on about the world
is a fact, with how it's known: documented, observed or assumed. Each is written as a
requirement is, with an ID under `term.` or `fact.`: `r[term.word]`, or
`r[fact.id] observed`. A term whose word is often used in its ordinary sense is defined
as cited only, `r[term.word] cited-only` (`glossary.define`). Tracey allows one prefix
in a spec ([[f:tracey.one-prefix]]), so a marker of their own would stop it reading the
spec at all; written this way, tracey reads them as requirements, never implemented, and
codewalk doesn't. Each is defined in the spec it belongs to, under its own heading before
the requirements, so a spec reads complete on its own; those that run through all of
codewalk are in its top-level spec. They're cited like requirements, and a term is also
found wherever its words appear in prose, and linked to where it's defined, unless it's
cited only, when it's linked only where it's cited (`glossary.cite`). One defined twice in the spec, or cited and not defined, is an error; a
[[t:prd]] defining one is proposing it, not defining it twice (`glossary.errors`).
The glossary collects them all, by the spec that defines each, with where each is used
(`glossary.page`).

## Terms

r[term.term]
A word with a meaning of its own here, defined as `r[term.word]` in the spec it belongs to.
Its words, singular or plural, are linked to it wherever they appear in prose.

r[term.fact]
Something about the world we rely on and don't control, defined as `r[fact.id]` with how it's
known: documented, observed or assumed. What rests on it cites it, so when one turns out
wrong, what's affected can be found.

r[term.prefix]
The name before the brackets of a requirement's marker: `r`, or the name of the spec
it's in, in tracey's config. `t` and `f` are kept for citing terms and facts.

r[term.trace]
A comment in the code naming a requirement, `r[impl id]` or `r[verify id]`, on the
symbol it's in or directly above.

r[term.citation]
Where prose names a requirement, term or fact: a requirement's ID in backticks,
`[[r:id]]`, `[[t:id]]` or `[[f:id]]`, or a `req:`, `term:` or `fact:` link.

r[term.drift]
A requirement or the prose citing it having changed since the two were last reconciled,
so one may no longer say what the other does. Reconciling records both as they stand.

r[term.trail]
The path from a block of a codewalk to the requirements it proposes, implements,
verifies or cites, and from each of those to the prose in its spec it comes from.

r[term.glossary]
Every term and fact on one page, grouped by the spec that defines each, with where each
is used.

## Facts

r[fact.tracey.prefix] documented
tracey infers a spec's prefix, the `r` in `r[id]`, from the requirement markers in its
files, rather than from the spec's name. (tracey's documentation, on configuration.)

r[fact.tracey.one-prefix] observed
tracey refuses a spec whose files use more than one prefix, and then reads no spec at
all: a spec with `r[…]`, `t[…]` and `f[…]` lines stops the whole config loading
([[f:tracey.prefix]]). Seen with tracey 2.0.0-rc.0.

r[fact.tracey.versions] documented
A requirement's ID can carry a version, `r[id+2]`; without one it's version 1. When a
requirement's text changes its version is bumped, and code naming an older version,
`r[impl id]`, is stale, and not counted as covered until it's updated and its marker
bumped. (tracey's documentation, on versioning.)

## Requirements

r[spec.files]
The spec MUST be the files matched by the `include` globs of each spec in
`.config/tracey/config.styx`, and by the `specs` globs in `codewalk.toml`.

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

r[spec.cite]
A spec file's prose MUST be taken to cite a requirement where it has the requirement's
ID in backticks, `[[r:id]]`, or a link with the `req:` scheme.

r[spec.view]
The spec view MUST show each cited requirement beside the first block of prose citing it,
and MUST list the requirements the file defines that no prose cites, and the citations of
requirements that don't exist.

r[spec.drift]
Reconciling a requirement MUST record digests of it and of the prose citing it, and the
spec view MUST then show whether the prose, the requirement or both have changed since.

r[spec.trail]
A codewalk's margin MUST show, beside each block, the requirements it proposes,
implements, verifies or cites, and each MUST link to its spec at the prose that cites it,
or at the requirement if no prose does.

r[glossary.define]
A line consisting only of `prefix[term.id]` or `prefix[fact.id]`, where prefix is a
requirement's, optionally followed, for a fact, by documented, observed or assumed, or,
for a term, by `cited-only`, MUST be read as the definition of the term or fact `id`,
with the paragraph after it as its text, and not as a requirement.

r[glossary.cite]
`[[t:id]]`, `[[f:id]]`, and links with the `term:` and `fact:` schemes MUST be read as
citations, and a term's words in prose SHOULD be linked to it the first time in each
paragraph, unless it's defined `cited-only`, when it MUST be linked only where it's cited.

r[glossary.errors]
A term or fact defined more than once in the spec, or cited and defined neither in the
spec nor in the PRD citing it, MUST be reported as an error. A PRD's definition of one the
spec defines isn't a second definition.

r[glossary.page]
The glossary page MUST list every term and fact, grouped by the file that defines it,
spec files first in the order the index lists them, each linked to its definition and to
the codewalks and spec files that cite or mention it.
