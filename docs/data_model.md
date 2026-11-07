---
title: codewalk's data model
summary: The things codewalk knows about (code, spec, walkthroughs, notes, review) and how each refers to the others.
tags: [codewalk, data-model]
related: [walkthrough.md]
---

# codewalk's data model

codewalk knows about five kinds of thing: **code**, the **spec**, **walkthroughs**, the
**notes** in them, and what's been **reviewed**. Each kind has an index, built from files
in the repository and rebuilt when they change. Nothing is stored apart from the files,
except what's been reviewed, which is kept in `codewalk.review.json`.

```text
                         Context
      ┌─────────────┬───────┴──────┬──────────────┬──────────────┐
  CodeIndex      SpecIndex      Glossary      ReviewState     Config
      │              │              │              │
   Symbol ◄─┐   Requirement     Definition      Reviewed
      ▲     │     ▲    ▲            ▲              ▲
      │   Trace ──┘    │            │              │  by walkthrough, then Ref.key
      │                │            │              │
      └──────────── Ref ────────────┘──────────────┘
                     ▲
       Walk ─────────┤──── FrontMatter, Problem, Progress
        │            │
        ├── Thread ── Note ── Note (replies)
        │
        ├── SpecView ── Citation ── Requirement      (a spec file)
        └── Link ── Requirement                      (the trail: prose → spec → code)

  Library ── Summary, SpecSummary                     (the index page)
  Brief ── Item                                       (`codewalk context`)
```

## The project: Context

A [[doc::Context]] holds everything a walkthrough is checked against: the indexes of code,
spec and glossary, and the review state. There's one a project, built from its
[[codewalk::config::Config]].

```walk
codewalk::config::Config
doc::Context sig
```

## Code: Symbol and Trace

The code is indexed by [[CodeIndex]] into [[Symbol]]s: a function, a type, a method,
with where it is and its docs. A [[Trace]] is a requirement's marker in the code,
`r[impl id]`, and the symbol it's in. That's how a requirement finds its code.

```walk
Symbol
Trace
```

## The spec: Requirement

[[SpecIndex]] reads tracey's spec files into [[Requirement]]s, by ID. A requirement in a
spec whose prefix isn't `r` is known by the spec's name too (`v1:slack.client`).

```walk
Requirement
```

## Terms and facts: Definition

The [[Glossary]] holds each [[Definition]], a term or a fact, from `t[id]` and `f[id]`
lines in any Markdown file.

```walk
Definition
```

## Walkthroughs: Walk and Ref

A [[Walk]] is one Markdown file, parsed. Everything it names is a [[Ref]]: a line of a
`walk` block, an inline `[[name]]`, a requirement, a term, or a proposal. Resolving a
ref fills in exactly one of its `symbol`, `requirement` or `definition`, or its `error`.
A ref is the hub of the model: it's where a walkthrough meets each index.

```walk
Ref
FrontMatter
Problem
```

## Notes: Thread and Note

A [[notes::Thread]] is a blockquote of [[Note]]s, in the walkthrough's own Markdown. A note's
replies are notes too, nested under it. A thread is *about* the refs in the block above
it, by line (`about_line`) rather than by holding them.

```walk
Note
notes::Thread sig
```

## Specs against their prose: SpecView and Citation

A spec file is a walk too. Its [[SpecView]] lists the requirements it defines and a
[[Citation]] for each one its prose cites, with whether the two still agree.

```walk
Citation
SpecView
```

## The trail: Link

[[trail::Link]] ties a block of a walkthrough to a requirement, with its role: proposes,
implements, verifies or cites. It's what the margin shows.

```walk
trail::Link
```

## Reviewed

[[ReviewState]] keeps one [[Reviewed]] for each ref that's been reviewed, by walkthrough
and then by the ref's key, with a digest of the code as it was. If the code changes, the
digest doesn't match, and the ref shows as changed.

```walk
Reviewed
```

## Across walkthroughs: Library and Brief

The [[Library]] summarises every walkthrough and spec for the index page, one
[[Summary]] or [[SpecSummary]] each. A [[Brief]] is what `codewalk context` prints for an
agent: what's asked, what's proposed, what's broken.

```walk
Summary sig
Brief
```
