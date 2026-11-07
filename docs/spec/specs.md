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
since two specs can share an ID (`spec.prefix`). The code names a requirement in a
comment, `r[impl id]` or `r[verify id]`, and codewalk finds the symbol each is on
(`spec.traces`), so a requirement in a walkthrough can show its code.

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
(`term.define`). They're cited like requirements, and a term is also found wherever its
words appear in prose (`term.cite`). One defined twice, or cited and not defined, is an
error (`term.errors`).

## Requirements

r[spec.files]
The spec MUST be the files matched by the `include` globs of each spec in
`.config/tracey/config.styx`, and by the `specs` globs in `codewalk.toml`.

r[spec.prefix]
A line consisting only of `prefix[id]`, where prefix is `r` or the name of a spec in
tracey's config, MUST be read as a requirement, with the paragraph after it as its text.
One with a prefix other than `r` MUST be known as `prefix:id`, and written without the
prefix, in a file of the same spec, MUST resolve to it.

r[spec.traces]
A comment containing `prefix[impl id]` or `prefix[verify id]` MUST be read as a trace of
that requirement, on the smallest symbol around it, or the symbol it's directly above.

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

r[term.errors]
A term or fact defined more than once, or cited and not defined, MUST be reported as an
error.
