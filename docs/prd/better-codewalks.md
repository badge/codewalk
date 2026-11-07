---
title: "Better codewalks"
summary: "A codewalk explains code and a PRD changes it; words that aren't always terms; and the margin and the code beside the page staying out of the way."
kind: prd
stage: spec
tags: [ui, prd]
related: ["authoring-prds.md", "../walkthrough.md"]
---

# Better codewalks

> [!request] @matthew: A codewalk (let's not call them walkthroughs) _may_ be a PRD, but often it's not: it's just a nice walkthrough of a chunk of code. As a result, it doesn't have proposals (I think). It's reasonable to ask and answer questions about it, so that the codewalk itself is improved, but if something is wrong then it should result in a PRD be created to fix it. In addition, at the top of _codewalk, walked through_ today, I see `proposed: 0/1 settled`. I cannot find that anywhere.
>
> Some other problems with the UI that I'm experiencing:
> - When in edit mode, I cannot toggle Requirements, so if I also open a code file the central column is very squished
> - Requirements scrolling independently on the RHS wasn't meant to be user actionable: I just want them to handle it themselves. If I'm hovering over the requirements column and scroll, it should just scroll the main content column
> - In the codewalk doc, "5. The library: how walkthroughs relate", clicking `Summary` to bring up its code squashes the main view and then I cannot see the section I was just reading, because it's been moved down
> - Sometimes a general term (in another project, `target`) gets rendered as its term, even though its not; do we need a marker to make the UI _not_ show it as a term?
>
> I should say that this is all pretty vanilla/UI stuff, and I'm not concerned about this being the most thoroughly reviewed PRD in the world.

## The problem

**A codewalk and a PRD are confused.** A codewalk (what codewalk has called a walkthrough)
explains code as it is; a PRD proposes a change to it. But any codewalk can hold a
`walk proposed` block, and then shows its progress like a PRD's: *codewalk, walked
through* shows `proposed: 0/1 settled`, from the `Library::uses` proposal at the end of
its last section, which is easy to miss. And when a question about a codewalk shows that
the code is wrong, there's no way from it to the PRD that would fix it.

```walk
Walk::progress
```

**Some words aren't always terms.** Every word the spec defines as a term is linked
wherever it's used, so a word with a meaning of its own in one place and an ordinary one
in another (in another project, `target`) is linked to its definition where it means
nothing of the kind. There's no way to say a word is only a term where it's cited.

```walk
Renderer::text
Glossary::mentions
```

**The margin and the code beside the page get in the way.**

- While editing there's no **Requirements** toggle, so with a file open beside the
  editor, the preview, which keeps its margin, is squeezed into a narrow column.
- The margin scrolls by itself under the pointer, which nobody asked for: scrolling over
  it should scroll the page.
- Opening a name's file beside the page (`Summary`, in *5. The library*) narrows the
  page, everything reflows, and what you were reading has moved down out of sight.

## What we want

### A codewalk, and a PRD

A codewalk explains a part of the code as it stands. Questions about a codewalk are asked and answered
in it, so it gets better. But it doesn't propose: a `walk proposed` block belongs in a PRD,
and one in a codewalk that isn't a PRD is a warning (`proposal.draft+2`). Progress is a
PRD's, so only a PRD shows it (`proposal.progress+2`).

When a question about a codewalk shows something wrong with the code, the thread offers
to start a PRD from it, as the index does, with what was asked filled in from the thread,
and the thread then says where the PRD is, so a reader of the codewalk can follow it
(`prd.from-thread`). The `Library::uses` proposal in *codewalk, walked through* moves to
a PRD of its own.

### The word

"Walkthrough" goes, everywhere, for "codewalk": what the pages and the command line say,
the README, the agent instructions and skills, the spec's prose, terms and requirements,
and the names in the code (`Context.walkthroughs`, `Library.walkthroughs`, the
`--walkthroughs` option of `codewalk init`, and the rest). Files named for it are renamed
too: `docs/spec/walkthroughs.md` and *codewalk, walked through*'s `docs/walkthrough.md`,
whose reviews in `codewalk.review.json`, recorded under its path, move with it. `walk`
stays: it's the block's syntax, and short for codewalk anyway.

A requirement whose only change is that word is rewritten where it is, without its version
bumped. That's against how the spec is meant to change, and done once, knowingly: nothing
holds the code to the spec with tracey yet, so no marker would go stale, and bumping some
thirty requirements for a word would bury the changes that matter. The term
`walkthrough` goes from the top-level spec, replaced by `codewalk` (below).

### Words that aren't always terms

A term can be defined as cited only, `t[target] cited-only` (`term.define+2`): it's linked
where it's cited, `[[t:target]]`, and nowhere else, so its word can be used in its
ordinary sense (`term.cite+2`). That's what `codewalk` needs too, as a term, since it's
also the tool's name: it's defined below as cited only, which codewalk can't read until
this is done, so until then the definition shows as text.

### The margin and the code beside the page

While editing, the preview has the same **Requirements** toggle as reading, remembered
between the two, and hides its margin while a file is open beside it, as reading does
(`ui.edit-margin`). The margin follows the page and can't be scrolled by itself:
scrolling over it scrolls the page (`ui.margin+2`). Opening or closing a file beside the
page keeps what you were reading where it was: the block whose name you clicked, or the
one at the top of the window, stays at the same height (`ui.context-place`).

## The spec

### A codewalk, and a PRD

r[proposal.draft+2]
A `walk proposed` block MUST be read as a proposal: its first line the name the code will
have, the rest its draft. One in a codewalk that isn't a PRD MUST be reported as a
warning.

r[proposal.progress+2]
A PRD's progress MUST be counted as how many of its proposals are not written, written
but not settled, and settled, and shown with it; a codewalk that isn't a PRD MUST NOT show
progress.

r[prd.from-thread]
A thread in a codewalk that isn't a PRD MUST offer to start a PRD from it, as the index
does, with what the person wants filled in from the thread and a link to it; once the PRD
is started, a note MUST be added to the thread, signed as the person, linking to it.

### Words that aren't always terms

r[term.define+2]
A line consisting only of `t[id]` or `f[id]`, optionally followed, for a fact, by
documented, observed or assumed, or, for a term, by `cited-only`, MUST be read as the
definition of a term or fact, with the paragraph after it as its text.

r[term.cite+2]
`[[t:id]]`, `[[f:id]]`, and links with the `term:` and `fact:` schemes MUST be read as
citations, and a term's words in prose SHOULD be linked to it the first time in each
paragraph, unless it's defined `cited-only`, when it MUST be linked only where it's cited.

### The margin and the code beside the page

r[ui.edit-margin]
While editing, the preview MUST offer the same toggle for its margin as reading does,
remembered between the two, and MUST hide its margin while a file is open beside it.

r[ui.margin+2]
Reading a codewalk or spec file, the margin MUST follow the page, keeping the cards for the
prose at the middle of the window beside that prose, and scrolling over the margin MUST
scroll the page. A spec view opened for a requirement MUST show its card beside the prose
citing it.

r[ui.context-place]
Opening or closing a file beside the page MUST leave the block whose name was clicked, or
else the block at the top of the window, at the same height in the window.

## The code

<!-- At the code stage: the data model in full, and the code that implements each
requirement, in full where it's intricate and by its signature where it's routine. -->

## Terms

t[codewalk] cited-only
A Markdown file that explains a part of the code, naming it rather than copying it, and
holds the conversation about it: a PRD is a codewalk that proposes a change. (What
codewalk has called a walkthrough.)

## Facts

## Questions

> [!question] @claude: Is the spec broadly agreed, so this PRD can move to `stage: code`?

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07 (the word): **question** @claude: How far should "codewalk" replace
  "walkthrough"? → **answer** @matthew, in conversation: Everywhere; rewrite the specs
  without bumping the versions, since tracey isn't used on the codebase yet. Written into
  [The word](#the-word).
- 2026-11-07 (a per-use mark): **question** @claude: Is a term defined `cited-only` enough,
  or should a single use of a term's word be markable as plain? → **answer** @matthew, in
  conversation: `cited-only` is enough; leave it as it is.
- 2026-11-07: Started at the problem stage by @matthew, who asked to go straight to the
  spec stage: the problem, the prose and the spec written, and set to `stage: spec`.
