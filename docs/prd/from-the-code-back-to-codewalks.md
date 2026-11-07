---
title: "From the code back to codewalks"
summary: "The context panel, and the language server's hover, say which codewalks show a symbol, from an index kept in `.codewalk/`."
kind: prd
stage: prose
tags: [library]
related: ["../codewalk.md"]
---

# From the code back to codewalks

## The problem

A codewalk names code, and codewalk shows that code from the codewalk. Nothing goes the
other way: the context panel shows a symbol in its file, but not which codewalks show it,
and nor does the language server's hover in the code itself. The library knows every
codewalk, but only as a list of summaries:

```walk
Library
```

Finding which codewalks show a symbol means parsing every codewalk, which is fine for two
and not for fifty.

## What we want

The context panel, and the language server's hover, list the codewalks that show or
mention a symbol, each with the line of its reference, so a reader can go from the code to
what's been written about it.

The answer comes from an index rather than parsing every codewalk each time. There's one
codewalk instance for each project, and each project is a git repository, so the index
lives at the repository's root, in `.codewalk/`, as a SQLite database (the standard
library's, so nothing new to install): one row for each reference, with its codewalk, its
line, the symbol's file and span, and any requirement, rewritten for a codewalk when its
file changes. Everything in it can be worked out again from files that are committed, so
`.codewalk/` is ignored by git, and `codewalk init` adds it to `.gitignore`. Review state
isn't like that: it's a record of what people did, and can't be worked out again, so
`codewalk.review.json` stays where it is, committed.

A rough idea of the question the library answers, from the first draft, which parsed every
codewalk:

```python
def uses(self, ctx: Context, sym: Symbol) -> list[tuple[str, int]]:
    """The codewalks that show or mention `sym`, with the line of each reference."""
    out = []
    for s in self.codewalks:
        for ref in Walk(ctx, s.rel).refs:
            if ref.symbol and ref.symbol.file == sym.file and ref.symbol.start <= sym.line <= ref.symbol.end:
                out.append((s.rel, ref.line))
    return out
```

## The spec

## The code

## Terms

## Facts

## Questions

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07: Moved here from the end of [codewalk, walked through](../codewalk.md), where
  it was a proposal, since a codewalk explains code and a PRD proposes it (Better
  codewalks). Its thread there was settled before the move: @claude asked whether parsing
  every codewalk on each call was fine, and @matthew and @claude agreed one instance per
  git repository, and an index in `.codewalk/` with SQLite, ignored by git; that's in
  [What we want](#what-we-want).
