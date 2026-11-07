---
title: "Better codewalks"
summary: "A codewalk explains code and a PRD changes it; words that aren't always terms; and the margin and the code beside the page staying out of the way."
kind: prd
stage: work
tags: [ui, prd]
related: ["authoring-prds.md", "../codewalk.md"]
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
>
> [!done] @claude: All of it, as this PRD says: a codewalk explains and a PRD proposes, with a thread able to start a PRD; the `proposed: 0/1 settled` was the `Library::uses` proposal, now a PRD of its own; the editor's Requirements toggle; a margin that passes the wheel to the page; opening and closing code keeping your place; terms defined `cited-only`; and "walkthrough" is "codewalk" everywhere but the PRDs.

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

> [!note] @claude: As built, every block below is settled. Where the code departs from
> the outline:
>
> - **The rename** was one commit of its own, before the rest. Reviewed excerpts whose
>   code it renamed show as changed since review, since they did change.
> - **`App::start_prd`** checks the thread is there before starting the PRD, so a bad one
>   writes nothing, and refuses it with a 409, like the other refusals.
> - **`cited-only` on a fact** isn't read as a definition at all, since only a term can be
>   cited only.
> - **Older proposal tests** put a proposal in a codewalk that isn't a PRD, so they ignore
>   the warning that now brings, and a new test checks it.
> - **Keeping your place** remembers the block whose name was clicked until the next click
>   in the page or a scroll, so closing the file keeps the same block still, not just the
>   one at the top of the window. Checked in a browser: the block stays to the pixel,
>   opening and closing.
> - **The editor** gets the toggle for a spec file too, which said it had no margin.
> - **`Library::uses`** moved to a PRD of its own,
>   [From the code back to codewalks](from-the-code-back-to-codewalks.md), at the prose
>   stage, with what its thread decided.

### The word

A rename, done as one change before the rest: "walkthrough" for "codewalk" in every file
but the PRDs, which are records of what was said, in each of its forms (`walkthroughs`,
`Walkthrough`, `walkthrough's`), then the two files renamed, every link to them, and
their keys in `codewalk.review.json`. Nothing about it is worth proposing as code; the
tests say whether it's whole.

### A codewalk, and a PRD

[[Walk::problems]] warns of a proposal in a codewalk whose `kind` isn't `prd`
(`proposal.draft+2`), and the pages show a codewalk's progress only if it's a PRD
(`proposal.progress+2`): progress is still counted for any codewalk, so nothing in the
data model changes.

A thread in a codewalk that isn't a PRD has a **Start a PRD** button, which opens the same
form as the index, with what's asked filled in from the thread's first note. Starting it
goes to the server with where it came from, which links the two:

```walk settled python
App::start_prd
# r[impl prd.start]
# r[impl prd.from-thread]
# r[impl serve.local]
def start_prd(self, title: str, ask: str, source: str | None = None, thread: int | None = None) -> dict:
    """Start a PRD from the index, or from a thread in a codewalk, and say where to open it.

    From a thread, the PRD's request says which codewalk it came from, and a note added to
    the thread says where the PRD is.
    """
    origin = (source, next(t for t in Walk(self.ctx, source).threads if t.line == thread)) if source and thread else None
    if origin:
        ask += f"\n\nFrom [{Walk(self.ctx, source).title}]({os.path.relpath(source, prd.FOLDER)})."
    try:
        rel = prd.start(self.ctx, title, ask)
    except FileExistsError as e:
        raise ValueError(f"there's a PRD at {e} already") from e
    if origin:
        path = self.writable(source)
        note = f"Taken up in a PRD: [{title}]({os.path.relpath(rel, os.path.dirname(source))})."
        path.write_text(notes.reply(path.read_text(), origin[1], "note", self.ctx.config.who(self.ctx.root), note))
    return {"started": rel, "href": f"/walk/{rel}"}
```

### Words that aren't always terms

A definition says whether its term is cited only:

```walk settled python
Definition
class Definition(BaseModel):
    kind: Literal["term", "fact"]
    id: str
    # How a fact is known; None for a term
    status: Literal["documented", "observed", "assumed"] | None = None
    # A term linked only where it's cited, `t[id] cited-only`, since its word is often used
    # in its ordinary sense
    cited_only: bool = False
    file: str
    line: int
    text: str

    @property
    def words(self) -> str:
        """A term as it's written in prose."""
        return self.id.replace("-", " ")
```

```walk settled python
DEF_LINE
DEF_LINE = re.compile(r"^(t|f)\[([a-z0-9][a-z0-9.\-]*)\](?:[ \t]+(documented|observed|assumed|cited-only))?[ \t]*$")
```

`terms::parse` reads `cited-only` for a term only, and the pattern that finds a term's
words in prose leaves cited-only terms out:

```walk settled python
Glossary::mentions
def mentions(self) -> re.Pattern | None:
    """A pattern for every term as it's written in prose, but those cited only.

    Longest first, singular or plural, whole words only, ignoring case.

    Returns
    -------
    re.Pattern or None
        None if no terms are to be found in prose.
    """
    if self._pattern is None:
        words = sorted((d.words for d in self.terms.values() if not d.cited_only), key=len, reverse=True)
        alts = "|".join(re.escape(w).replace(r"\ ", r"[ \-]") for w in words)
        self._pattern = re.compile(rf"\b({alts})(?:s|es)?\b", re.IGNORECASE) if words else None
    return self._pattern
```

### The margin and the code beside the page

All three are in `app.js` and `app.css`, which codewalk doesn't index: the editor's header
gets the **Requirements** toggle, using the same remembered setting as reading, and the
editor hides the preview's margin while a file is open beside it (`ui.edit-margin`); the
margin stops scrolling under the pointer and passes the wheel to the page
(`ui.margin+2`); and opening or closing a file beside the page measures the block that was
clicked, or the one at the top of the window, before the layout changes, and scrolls by
however far it moved (`ui.context-place`). Like `ui.place`, the last two are checked in a
browser, not by the tests.

### Tests

```walk settled python
test_a_proposal_in_a_codewalk_that_isnt_a_prd_is_a_warning
# r[verify proposal.draft+2]
def test_a_proposal_in_a_codewalk_that_isnt_a_prd_is_a_warning(repo): ...
```

```walk settled python
test_only_a_prd_shows_its_progress
# r[verify proposal.progress+2]
def test_only_a_prd_shows_its_progress(client, repo): ...
```

```walk settled python
test_a_prd_started_from_a_thread_and_the_thread_link_to_each_other
# r[verify prd.from-thread]
def test_a_prd_started_from_a_thread_and_the_thread_link_to_each_other(client, repo): ...
```

```walk settled python
test_a_cited_only_term_is_linked_only_where_its_cited
# r[verify term.define+2]
# r[verify term.cite+2]
def test_a_cited_only_term_is_linked_only_where_its_cited(repo): ...
```

```walk settled python
test_the_editor_can_put_the_margin_away
# r[verify ui.edit-margin]
def test_the_editor_can_put_the_margin_away(client, repo): ...
```

## Terms

t[codewalk] cited-only
A Markdown file that explains a part of the code, naming it rather than copying it, and
holds the conversation about it: a PRD is a codewalk that proposes a change. (What
codewalk has called a walkthrough.)

## Facts

## Questions

> [!question] @claude: The rename showed a gap in how a PRD is checked. Once a PRD's work
> is done, its requirements are quoted from the spec, and any later change to one of them
> makes `codewalk check` fail on the finished PRD: *Authoring PRDs* did, over a word, until
> I brought its copy into line. A finished PRD is a record, so I'd stop comparing its spec
> with the spec once it's at the work stage and its proposals are all settled, and show it
> as it was. Should a finished PRD be marked as such (a stage after the work, `done`, say),
> or is "at the work stage, all settled" enough?

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07 (the work): The prose and requirements moved into the spec, "walkthrough"
  renamed "codewalk" everywhere but the PRDs, the code and its tests written, and every
  proposal settled, with where the code departs from its outline in a note under
  [The code](#the-code). Set to `stage: work`.
- 2026-11-07 (to the code): **question** @claude: Is the spec broadly agreed? → @matthew,
  in conversation: Yes, and go on to the work too. Set `stage: code`, with the outline in
  [The code](#the-code).
- 2026-11-07 (the word): **question** @claude: How far should "codewalk" replace
  "walkthrough"? → **answer** @matthew, in conversation: Everywhere; rewrite the specs
  without bumping the versions, since tracey isn't used on the codebase yet. Written into
  [The word](#the-word).
- 2026-11-07 (a per-use mark): **question** @claude: Is a term defined `cited-only` enough,
  or should a single use of a term's word be markable as plain? → **answer** @matthew, in
  conversation: `cited-only` is enough; leave it as it is.
- 2026-11-07: Started at the problem stage by @matthew, who asked to go straight to the
  spec stage: the problem, the prose and the spec written, and set to `stage: spec`.
