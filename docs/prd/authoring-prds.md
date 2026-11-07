---
title: "Authoring PRDs"
summary: "How a PRD is written: a problem, then prose, then a spec, then the shape of the code, all in the one file, read on its own and compared with the spec as it stands."
kind: prd
tags: [prd, spec]
related: ["../walkthrough.md"]
---

# Authoring PRDs

> [!question] (BTW I am typing this in the edit view, but I cannot see it in the rendered view when it is a `[!note]`, as I can when it is a question, so really it's a note but I'm typing it as a question.) Re the spec, prose, etc.: IMO the value of a PRD is greatest when it can be read in isolation, assuming reasonable familiarity with the codebase. For that reason, I think it's a mistake to start editing prose and the spec while a PRD is still in a proposed state. Instead, everything should be kept here. That means that proposed requirements should be diffed against those that exist already, but [Tracey already supports this](https://tracey.bearcove.eu/guide/writing-specs/#versioning). Obviously we'll need some reasonable way to check whether requirements are actually new or updates, and we'll have to start with fresh prose, but a PRD really needs to be "here's a problem, here's how we're going to solve it", not ", but you also need to look around the other updated files in this repo for a reasonable diff.". Now, I am happy with a PRD going stale once it's been completed, that's to be expected.
>
> [!answer] @claude: Agreed, and this PRD now works that way: nothing outside this file
> changes while it's proposed. I've taken out the spec I'd written in `docs/spec/prds.md`
> and put back what I'd changed in [the conversation](../spec/conversation.md) and
> [the browser](../spec/browser.md); the prose below starts fresh. Telling new
> requirements from changed ones falls out of tracey's versioning
> ([[f:tracey.versions]]): a requirement in a PRD whose ID the spec already has, with its
> version bumped, is a change, shown against the text as it stands; an ID the spec
> doesn't have is new. The catch is that codewalk can't read a versioned ID yet, in a
> spec or in code, so that's part of this. The `[!note]` not showing was my bug: `note`
> and `request` had become terms, and linking the word broke the marker. It's fixed, so
> notes show now.

> [!question] This is another question that is really a note. IMO this PRD has jumped the gun somewhat, and I'm not sure whether we should start an entirely new PRD (because there's value in what's here), but, stressing again that a PRD should be a complete view of the world, I think the first stage of a PRD is to write the prose from which we create a spec. All the code that's here today is premature because we haven't yet nailed down the spec, and we haven't nailed down the spec because we're still talking about the process. So a new PRD should start with a problem statement (I'm fine with it referencing code that already exists, that's not a problem, so `## The problem` right below here is fine). But then `## The code`---I don't think that should event exist yet. Otherwise I'm going to review code and we'll immediately realise a misunderstanding about the spec and have to start again. Now, obviously this is going to be an iterative process, and a certain amount of that is inevitable, but we should start at a high level. Continuing on from _that_ idea, a PRD does not need to be an exhaustive review of every single piece of code that we're going to write--if there're data model changes then I absolutely want to see those, but code that doesn't impl some requirement (like `changes::at`), what is that even doing there? And even if code _does_ impl some requirement I'm not sure that anything more than the signature needs to be there anyway. (I feel less strongly about that.) See the new lifecycle section below.
>
> [!answer] @claude: Agreed. I've kept this PRD rather than starting another, and set it
> back to the second stage of your lifecycle: the problem, then the prose, with the terms
> and facts it needs. The spec, code and tests I'd drafted are gone from it; they're in
> the history, at 711c4b7, if any of it's wanted later. What writing it showed stays, as
> evidence for the problem, and the questions it raised that still matter are under
> [Questions](#questions).

## The lifecycle of a PRD

1. A PRD begins because we want to make some change to the codebase to add a feature, fix a bug, or whatever.
2. We begin with a problem statement, and then we define the solution scope in prose. At this early stage
   we also begin to document facts and terms that are useful to the rest of the PRD. We do this before we
   write the spec and certainly any code (besides perhaps some very rough examples that aren't even proposals)
3. Once we have the prose agreed, we try to write a spec from it. In all probablity this will mean jumping
   back and forth between the prose and the spec until we feel like we've got a reasonable spec from which we
   can begin to work.
4. Only after this do we start fleshing out both the structure of the code and the tests that will support it.
   A PRD does not need to, and indeed should _not_, provide the exhaustive detail of the plan for each code
   fragment we're going to need in the codebase.
5. Once it's written proper, we start work on the actual codebase, and the PRD can be updated
   with references to the actual symbols in the code using the tools that `codewalk` provides.

It's inevitable that at each stage past (1) we will loop back and iterate, but starting with a full PRD
of proposed code doesn't make sense.

Additionally, besides the standardised changelog actions we have in the questions and answers, we can
just add stuff to the changelog as we see fit.

## The problem

codewalk can start a PRD, `codewalk new PATH --title T --prd`, which writes a walkthrough
from a template with `kind: prd`, and counts a PRD's progress by its proposals:

```walk
cli::new
FrontMatter::kind
Walk::progress
```

That's all it knows about PRDs, and it gets the order wrong. The template has a section
for the spec and one for the code, with a sample proposal, so a PRD starts with code in
it, and its progress is measured only in code. Nothing in codewalk knows the stages a PRD
goes through, so nothing stops it jumping to the code, as this one did.

Nor is there anywhere for a PRD's spec to go. Requirements, terms and facts are read only
from the spec's files: a requirement written in a PRD isn't read at all, and a term
defined in a PRD with the same name as one in the spec is an error, defined twice. So a
PRD can either describe its changes to the spec, which leaves the reader to imagine them,
or make them in the spec, which means reading the PRD with the rest of the repository open
beside it. Neither is a PRD you can read on its own.

And codewalk can't read a requirement with a version ([[f:tracey.versions]]): `r[id+2]` in
a spec, or `r[impl id+2]` in code, isn't recognised, so the way tracey marks a requirement
as changed is invisible to it.

## What we want

### A PRD reads on its own

Everything a PRD proposes is in it: the problem, the prose that says what we'll do, the
spec that follows from the prose, and the shape of the code. Someone who knows the
codebase can read it and nothing else, and know what will change and why. Nothing outside
it changes while it's proposed: not the spec, not the code. Once the work is done it may
go stale, and that's fine: by then the spec and the code say what's true, and the PRD says
why.

### In stages

A PRD goes through the stages in [the lifecycle](#the-lifecycle-of-a-prd): the problem; the
prose, with the terms and facts it needs; the spec; the code; and the work. Each is agreed
before the next is started in earnest, though it's normal to go back. codewalk should know
which stage a PRD is in, show it, and make it plain to an agent what belongs in the PRD
yet: no code before the spec is agreed.

### Its spec, against the spec as it stands

A PRD's requirements are written in it as they'll read in the spec, and codewalk shows each
against the spec as it stands: new, if the spec has no such ID; changed, if it has, with
the version bumped and the old text beside the new; and unchanged text under an ID the
spec has is either a mistake or a requirement quoted for context, and should say which.
Terms and facts the same way: a PRD's definition of a word the spec already defines is a
proposed change to it, shown against it, not a second definition. The spec view and the
glossary, and tracey, go on reading only the spec itself, so a PRD's proposals don't count
until they're moved into it.

### Its code, in outline

Once the spec is agreed, a PRD shows the shape of the code: changes to the data model in
full, and for code that implements a requirement, its signature and the marker it will
carry; not every helper. Proposing a change to code that exists shows the draft against it.

### Started, written and worked in the browser

A person starts a PRD in the browser, with a title and what they want, which goes in as a
standing request; the agent, in its own application in the same folder, picks it up with
`codewalk context`. They work through it in the browser together, stage by stage. codewalk
is for local use: the server and the agent on the person's own machine, in the same
checkout.

While a PRD is proposed, only its own file changes, so it can be written in the checkout
the person is in. The work, once the PRD is agreed, is done on a branch of its own, in a
git worktree of its own: there the prose and requirements move into the spec, the code is
written, and the proposals are settled.

> [!note] I'd rephrase this is a "Started, written and worked wherever the user wants". My problem was that I _couldn't_ do what I wanted to from a browser, but equally if I want to write a PRD entirely in my IDE (so that I don't need to have a `codewalk` instance running) then that's fine too.

### A changelog to write in

Settled threads go into the changelog at the end, compacted to a line; anything else worth
recording about how the PRD got here can be added to it too, by hand.

## Terms

t[stage]
Where a PRD is in its lifecycle: the problem, the prose, the spec, the code, or the work.

## Facts

f[tracey.versions] documented
A requirement's ID can carry a version, `r[id+2]`; without one it's version 1. When a
requirement's text changes its version is bumped, and code naming an older version,
`r[impl id]`, is stale, and not counted as covered until it's updated and its marker
bumped. (tracey's documentation, on versioning.)

## Questions

> [!question] @claude: How does a PRD say which stage it's in? I'd put it in the front
> matter, `stage: prose`, set by the person in the browser when they agree a stage, and
> shown on the index and in `codewalk context`, which would tell the agent what may be
> written yet. Or is a stage better read from what's there (no requirements yet: prose)?
>
> [!answer] @matthew: Yes, asterisk: the asterisk being that the stage gates later stages' actions, but not earlier stages', as discussed).

> [!question] @claude: The branch is what I've written the spec for, in
> the PRDs spec (since taken out). The case for the folder is that it's cheaper to
> start: you can sketch a PRD without a branch. But the PRD's walkthrough alone, citing
> requirements that don't exist yet as `[[r:id]]`, already covers sketching, and the
> spec view shows such citations as missing rather than failing. Does the branch match
> how you want to work, given how you use branches and review?
>
> [!answer] @claude: Neither, per your note at the top: a proposed PRD changes nothing
> but itself, so it needs no branch; the branch, in its own worktree, comes with the work.

> [!question] @claude: Starting a PRD switches the checkout to its branch, and the agent
> works in the same checkout, so it's then on the PRD's branch too, which is what we want.
> But it means one PRD at a time per checkout, and starting one is refused while anything
> is uncommitted, including the agent's work on another. Is one at a time right for now,
> or should each PRD get a `git worktree` of its own, with `codewalk serve` able to show
> several?
>
> [!decision] @matthew: Each PRD should get its own git worktree, that makes sense.
>
> [!note] @claude: Still so, but later: with the spec kept in the PRD, the worktree is
> for the work, once the PRD is agreed, not for writing the PRD.
>
> [!answer] @matthew: Actually I think it should be "whichever", but I wouldn't mandate it and I certainly wouldn't do it automatically from the browser. We're not looking to create a new IDE here, but a means to facilitate discussion.
>
> [!decision] @matthew: PRDs are orthogonal to worktrees, and the PRD process neither creates nor manages worktrees.

> [!question] @claude: A server for each worktree, on its own port, means nothing in the
> server changes: it's one checkout, as now. The cost is several processes, and a PRD's
> address changing each time its server starts. The alternative is one server holding a
> [[Context]] for each worktree, under `/prd/<name>/`, which keeps one address but means
> every link and request in the pages, all written from the root now, has to carry the
> prefix. I've proposed the first. Is several ports all right?
>
> [!answer] @matthew: Here's a long-winded answer. Generally, I don't use Claude Code tied to a GitHub repo as we're doing here, and much of the work I do precludes it (where we work on multiple repos at once across services, infra, databases, tool crates and packages, etc).
>
> In addition, running `codewalk context` is going to do exactly nothing, in spite of my saving this file, until I've committed and pushed it up to GitHub.
>
> Furthermore, and probably most importantly, Claude Code running autonomously on its own server to which I have no access and can't review code is exactly the kind of thing that `codewalk` is _not_ built to solve. It's meant for a much more code review and iteration process. Essentially I'd think of it like a live GitHub PR, where instead of commits and comments being separate (or at least difficult to understand what's going on), the codewalk is the story of the code.
>
> In summary, I don't think we should try to solve this problem, except to say that `codewalk` is really designed for local use: run the server on your local machine, have CC attached to the dir, and iterate together. This reduces pain and maximises throughput, which is exactly what we're after.
>
> Obviously we're currently running this remotely (and now that I think of it, what does it mean to have 'a server for each worktree' in this context????), but I'm going to move to local dev ASAP.
>
> [!answer] @claude: Agreed: a server per worktree is gone, and codewalk is for local use.
> Here, it would have meant ports inside this container that only I can reach, which is
> to say nothing useful. Once a PRD's work is in a worktree, you'd run `codewalk serve`
> there, or we look at it again then.

> [!question] @claude: Nothing tells the agent the person has done something: after
> answering in the browser, they say "carry on" in the agent's application, and the agent
> reads `codewalk context`. That's simple and keeps the person in charge of when the agent
> works. Should codewalk do more, say `codewalk context --wait`, which returns once a
> person's note changes what's in hand, so an agent can sit waiting for the next answer?
>
> [!answer] @matthew: Let's KISS and iterate as we need.

> [!question] @claude: Once the branch is merged, its base has its changes, so the merge
> base is the branch's own last commit and the list is empty. That's right while the PRD
> is open, but afterwards it's the record of what it changed. Should merging (or settling
> the last proposal) write the merge base into the front matter as `base_commit`, so the
> list keeps working against that commit, or is the git history enough by then?
>
> [!answer] @matthew: I am so confused by this question.
>
> [!answer] @claude: Withdrawn: it assumed a PRD changed the spec on its branch, so its
> changes had to be found by comparing commits, and once merged there'd be nothing left to
> compare. With the spec kept in the PRD and compared with the spec as it stands, there's
> no commit to remember.

> [!question] @claude: Some of this changes code that exists: [[cli::new]] gains
> `--base`, [[SpecIndex::refresh]] and [[Glossary::refresh]] call the new `parse`
> functions, and the template gains `base`. A `walk proposed` block can't say that: its
> name resolves at once, so it reads as written, not proposed. I've described those
> changes in prose instead. Should a proposal for a name that exists show its draft as a
> diff against the code as it is, and count as proposed until the code matches the draft
> or it's settled?
>
> [!answer] @matthew: > Should a proposal for a name that exists show its draft as a diff against the code as it is, and count as proposed until the code matches the draft or it's settled?
>
> Yes, exactly that, that makes sense to me.
>
> [!question] @claude: One thing to settle first: once a name exists, a new proposal
> that's been written also differs from its draft, as most do, so codewalk can't tell
> "written, a bit differently" from "a change not made yet". The block could say which:
> `walk proposed change` for a change to code that exists, proposed until it's settled.
> Does that work?
>
> [!answer] @matthew: Yes, that makes sense.

> [!question] @claude: These won't settle. The tests aren't indexed (`sources` is
> `codewalk/**/*.py`), so a proposed test's name never resolves, and the PRD can't reach
> all settled. Should `sources` include `tests/**/*.py`? Test names are long and unique,
> so they won't make other names ambiguous, but every walkthrough would then be able to
> show tests, which may be what we want anyway.
>
> [!answer] @matthew: Yes, `sources` should include `tests/` by default for Python projects.
>
> [!done] @claude: `codewalk init` already writes `**/*.py` for a Python project, which
> includes `tests/`; codewalk's own `codewalk.toml` now has `tests/**/*.py` too.

## What writing it showed

Writing this by hand, rather than through the skills, turned up where the process and
the tool fall short:

- **The process wasn't written down,** and the first attempt at it, editing the spec in
  place on a branch, made a PRD that couldn't be read on its own. The lifecycle above is
  the second.
- **The template starts with code,** a sample `walk proposed` block (`Type::new_method`, in
  Rust) and a sample question, which both count as in hand straight away, so
  `codewalk context` reports a fresh PRD as two items behind.
- **A PRD can't hold a spec:** requirements in it aren't read, and its terms clash with the
  spec's.
- **Versioned requirements aren't read** (`r[id+2]`, `r[impl id+2]`).
- **The browser couldn't start a PRD,** nor agree a proposal, nor add to a settled thread;
  the last two it now can (`proposal.agree`, `note.add-settled`).
- **A note whose kind is a term vanished:** `[!note]` and `[!request]` showed as empty once
  `note` and `request` were terms. Fixed.
- **Changing existing code can't be proposed,** above.
- **`codewalk check` doesn't check the spec.** It checks walkthroughs only, so a term cited
  and not defined in a spec file, or defined twice across two, is reported only on the
  spec's page.
- **A question's summary loses its links.** `codewalk context` shows a question about
  `[[cli::new]]` as "code that exists: [] gains", dropping the name it's about.

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07: Set back to the prose stage, after @matthew's notes: the spec written in
  place in `docs/spec/` taken out and what it changed there put back; the drafted spec,
  code and tests taken out of the PRD (they're at 711c4b7).
- 2026-11-07: **note** @claude: The first PRD, written mostly by hand, to find out how writing one should go. → **note** @matthew: The entire process should run through the UI, in concert with an agent like Claude running in its own application alongside.
