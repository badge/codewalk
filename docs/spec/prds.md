---
weight: 25
---

## PRDs

A PRD is how a change of any size is proposed before it's made: what's wrong, what will
be true once it's done, what the spec will say, and the code that will say it. It's
written to be argued with, so it's where the questions are asked and answered, and once
the change is made it stays, as the record of what was planned beside what was built.

A PRD is two things: a walkthrough, with `kind: prd`, that says why and proposes the code;
and the change it makes to the spec, made in the spec itself, on a branch of its own.

### Where a PRD lives

Most changes aren't standalone: they change what the spec already says as much as they
add to it. So a PRD doesn't keep a draft of the spec somewhere else, to be copied in once
it's agreed. It's written on a branch, and the spec on that branch is edited where it
lives: prose first, then the requirements that follow from it. A new area of the spec
gets a new file; a change to an existing one is made in that file. The spec on the
branch is always the spec as it will be, so it's read and reviewed the same way as the
spec on the base, and two PRDs that disagree about it meet as a conflict when the second
is merged, which is when they should.

The walkthrough goes in `docs/prd/`, where it stays once the branch is merged. It's
started with `codewalk new PATH --title T --prd`, which names the branch it will be merged
into, its base, in its front matter (`prd.new`).

### Writing one

1. **The problem**, naming the code it's about as it stands, and **the outcome**: what's
   true once it's done, in terms someone could check.
2. **The spec.** The prose, changed or written where it lives, and then the requirements
   that follow, each cited from the prose. A new word gets a term, and anything relied on
   about another tool, a fact, in the spec it belongs to.
3. **The code.** Each new piece drafted in a `walk proposed` block under the name it will
   have, with the requirement markers it will carry, so the margin ties it to its
   requirement and the requirement to its prose. Tests the same way.
4. **Questions,** asked where they arise, and answered there, until the PRD is agreed.
5. **The work.** Writing the code settles each proposal; tracey says when every
   requirement is implemented and verified; then the branch is merged.

### Seeing what it changes

Reading the spec on the branch says what it will be; a reviewer also needs what's
different. A PRD's changes to the spec are worked out against where its branch left its
base (`prd.base`): each spec file that's new, removed or changed, and in each, whether the
prose changed, and which requirements, terms and facts were added, changed or removed,
with their text before and after. `codewalk changes` lists them (`prd.changes`), and the
PRD's page shows them, each linked to where it is in the spec (`prd.view`).

## Terms

t[prd]
A walkthrough with `kind: prd` that proposes a change before it's made, written on a
branch with the change it makes to the spec. Its progress is how much of the code it
proposes is settled.

t[base]
The branch a PRD will be merged into, named in its front matter. What the PRD changes in
the spec is worked out against the commit where its branch left the base.

## Requirements

r[prd.new]
`codewalk new PATH --title T --prd` MUST write the PRD template at PATH, with `kind: prd`
and `base` in its front matter: the branch given by `--base`, or else the repository's
default branch.

r[prd.base]
A PRD's changes to the spec MUST be worked out against the merge base of its `base` and
the current commit, with the spec files as they are in the working tree.

r[prd.changes]
`codewalk changes PRD` MUST list each spec file that's new, removed or changed since the
PRD's base, and in each, whether its prose changed, and each requirement, term and fact
added, changed or removed, with its text before and after.

r[prd.view]
A PRD's page MUST show its changes to the spec as `codewalk changes` lists them, each
requirement, term and fact linked to where it is in the spec, and each removed one
shown with its text as it was.
