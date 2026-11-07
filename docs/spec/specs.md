---
weight: 30
---

## Specs and terms

codewalk works beside tracey. Tracey holds the code to the spec: which requirements are
implemented and verified, and where. codewalk shows the spec beside the prose it comes
from, and beside the walkthroughs that use it. Everything about coverage stays with
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
requirement in a walkthrough can show its code.

### Prose beside the spec

A spec file opens with prose, written and agreed by people, and the requirements follow
from it. The prose cites each requirement it gives rise to, as the ID in backticks,
`[[r:id]]`, or a `req:` link (`spec.cite`). The spec view shows each cited requirement
beside the prose that cites it, and says which requirements no prose cites, and which
citations name requirements not written yet (`spec.view`). Reconciling a requirement with
its prose records both as they stand; when either changes after that, the view says
which (`spec.drift`).

From a walkthrough, each block's requirements, whether it proposes, implements, verifies
or cites them, are shown in its margin, and each one leads to its spec at the prose it
comes from (`spec.trail`).

### Terms and facts

A word with a meaning of its own here is a term, `t[word]`, and something relied on about
the world is a fact, `f[id]`, with how it's known: documented, observed or assumed
(`term.define`). Each is defined in the spec it belongs to, under its own heading before
the requirements, so a spec reads complete on its own; those that run through all of
codewalk are in its top-level spec. They're cited like requirements, and a term is also
found wherever its words appear in prose, and linked to where it's defined
(`term.cite`). One defined twice in the spec, or cited and not defined, is an error; a
[[t:prd]] defining one is proposing it, not defining it twice (`term.errors`).
The glossary collects them all, by the spec that defines each, with where each is used
(`term.glossary`).

## Terms

t[term]
A word with a meaning of its own here, defined as `t[word]` in the spec it belongs to.
Its words, singular or plural, are linked to it wherever they appear in prose.

t[fact]
Something about the world we rely on and don't control, defined as `f[id]` with how it's
known: documented, observed or assumed. What rests on it cites it, so when one turns out
wrong, what's affected can be found.

t[prefix]
The name before the brackets of a requirement's marker: `r`, or the name of the spec
it's in, in tracey's config. `t` and `f` are kept for terms and facts.

t[trace]
A comment in the code naming a requirement, `r[impl id]` or `r[verify id]`, on the
symbol it's in or directly above.

t[citation]
Where prose names a requirement, term or fact: a requirement's ID in backticks,
`[[r:id]]`, `[[t:id]]` or `[[f:id]]`, or a `req:`, `term:` or `fact:` link.

t[drift]
A requirement or the prose citing it having changed since the two were last reconciled,
so one may no longer say what the other does. Reconciling records both as they stand.

t[trail]
The path from a block of a walkthrough to the requirements it proposes, implements,
verifies or cites, and from each of those to the prose in its spec it comes from.

t[glossary]
Every term and fact on one page, grouped by the spec that defines each, with where each
is used.

## Facts

f[tracey.prefix] documented
tracey infers a spec's prefix, the `r` in `r[id]`, from the requirement markers in its
files, rather than from the spec's name. (tracey's documentation, on configuration.)

f[tracey.other-markers] assumed
tracey passes over a line `t[id]` or `f[id]` in a spec file, so terms and facts can sit
beside requirements. Probably not so: its documentation says any lowercase alphanumeric
prefix is a requirement marker, inferred from a spec's files ([[f:tracey.prefix]]), so it
likely reads them as requirements of specs called `t` and `f`. Not checked by running it.

f[tracey.versions] documented
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
A walkthrough's margin MUST show, beside each block, the requirements it proposes,
implements, verifies or cites, and each MUST link to its spec at the prose that cites it,
or at the requirement if no prose does.

r[term.define]
A line consisting only of `t[id]` or `f[id]`, optionally followed by documented,
observed or assumed, MUST be read as the definition of a term or fact, with the paragraph
after it as its text.

r[term.cite]
`[[t:id]]`, `[[f:id]]`, and links with the `term:` and `fact:` schemes MUST be read as
citations, and a term's words in prose SHOULD be linked to it the first time in each
paragraph.

r[term.errors+2]
A term or fact defined more than once in the spec, or cited and defined neither in the
spec nor in the PRD citing it, MUST be reported as an error. A PRD's definition of one the
spec defines isn't a second definition.

r[term.glossary]
The glossary page MUST list every term and fact, grouped by the file that defines it,
spec files first in the order the index lists them, each linked to its definition and to
the walkthroughs and spec files that cite or mention it.
