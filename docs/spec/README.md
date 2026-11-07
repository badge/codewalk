---
weight: 0
---

# codewalk

codewalk is for reading code with someone: a person, or an agent, now or in a later
session. A codewalk is a Markdown file that names the code it's about rather than
copying it, so it can't quietly go out of date. codewalk checks that every name still
means something, shows the code as it stands, and remembers what's been reviewed, so a
change shows up where it matters.

Each file here starts with prose saying what we mean, and then the requirements that
follow from it, each cited from the prose that gives rise to it. The prose is written and
agreed by people. Where the prose and a requirement disagree, the requirement wins, and
the two are changed together; codewalk's own spec view shows where they've drifted.

Each file also defines the words it uses with a meaning of their own, and the facts about
other tools it relies on, so it reads complete without anything else open. The words that
run through all of codewalk are defined here, below; the glossary collects every one.

- [Codewalks](codewalks.md): naming code, showing it, checking it, reviewing it.
- [The conversation](conversation.md): notes, proposals, and what's in hand.
- [PRDs](prds.md): agreeing a change before making it, in stages, in a file of its own.
- [Specs and terms](specs.md): prose beside its requirements, and a glossary.
- [The browser](browser.md): reading, editing, and moving between them.

> [!question] @claude: This is a first draft of the prose, from codewalk as it stands,
> with the requirements written from it. Is this what we mean? Change the prose where it
> isn't, and the spec view will show which requirements need to follow.

## Terms

t[codewalk]
A Markdown file under the docs folders that names code rather than copying it, making at
least one reference to it, and holds the conversation about that code.

t[spec]
The Markdown that tracey's config names as specs: in each file, prose saying what we
mean, and then the requirements that follow from it.

t[requirement]
What must happen, exactly: a marker on a line of its own, `r[id]`, and then a paragraph
using the key words of BCP 14. tracey holds the code to it; codewalk shows it beside the
prose it comes from.

t[prose]
The part of a spec file before its requirements, written and agreed by people, citing
each requirement it gives rise to.

t[symbol]
A function, type, method, class or other named piece of the code, as the index finds it
in the sources, known by its qualified name.

## Meta

r[spec.keywords]
The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT" and "MAY" are to be interpreted
as described in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in all
capitals.
