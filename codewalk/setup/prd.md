---
title: "{title}"
summary: "One sentence: what changes, for whom, and why."
kind: prd
tags: []
related: []
---

# {title}

> [!note] @{author}: A PRD as a walkthrough. Everything it proposes is drafted in
> `walk proposed` blocks; implementing it settles each one, and what's left is a
> walkthrough of what actually happened, with the plan kept beside it.

## The problem

What's wrong or missing now, and who it affects. Name the code involved:

```walk
// the existing code this is about, one name a line
```

## The outcome

What's true once this is done, in terms someone can check.

## What the spec says

The prose this change gives rise to, citing each requirement it adds or changes as
`[[r:new.requirement.id]]` until the requirement is written, and as the ID in backticks
once it is. Define new words as terms and anything we rely on about the world as facts
(`t[word]`, `f[id] assumed`), in the glossary.

## The code

How it will work, step by step, each new or changed piece drafted under the name it
will have, with the requirement markers it will carry:

```walk proposed rust
Type::new_method
// r[impl new.requirement.id]
pub fn new_method(&self) {
    todo!()
}
```

## Testing

What proves it: the tests, drafted like the code, each marked with the requirement it
verifies.

## Questions

> [!question] @{author}: What's still to decide?
