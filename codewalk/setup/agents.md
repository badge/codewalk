## Codewalks, specs and the glossary: codewalk

Codewalks are Markdown files that name the code they talk about rather than pasting
it, and {codewalk_link} checks every name resolves and shows each one's
code as it stands. They're how a change is proposed, reviewed and explained, and they
carry the conversation about it from one session to the next. The syntax is in
{codewalk_syntax}.
{install}
**At the start of a session**, read what's in hand, and do any standing requests
(`[!request]`, at the top of a codewalk) before anything else:

```bash
{codewalk} context
```

It lists standing requests, open questions, code proposed but not written, proposals
written and waiting to be settled, code changed since someone reviewed it, and broken
references.

**Before a change of any size**, write or update a codewalk proposing it: what will
change and why, with the existing code named in `walk` blocks and the new code drafted in
`walk proposed` blocks under the name it will have, with the requirement markers it will
carry. A PRD is such a codewalk, written in stages (the problem, the prose, the spec,
the code, the work), with its spec kept in it until the work: start one with
`{codewalk} new PATH --title T --prd`, and write only what its `stage` allows, which
`{codewalk} context` says. A person moves it on from one stage to the next.
Ask what you need to know as `> [!question] @agent: …` in the codewalk, under what
it's about, and stop for an answer if you can't go on without one.

**While making it**, keep the codewalk true: once a proposed name exists, check what
was written against the draft and settle the block (`walk proposed` becomes
`walk settled`, keeping the draft); explain in the prose where they differ. When you've
done a standing request, add `> [!done] @agent: …` to it, saying what you did. Answer
questions in their thread with `> [!answer] @agent: …`; record what was decided with
`[!decision]` if a person decided it.

**Specs.** The prose at the top of a spec says what we mean; the requirements say exactly
what must happen. When the prose changes, change the requirements to follow, and cite
each requirement from the prose that gives rise to it, as its ID in backticks. Cite one
that doesn't exist yet as `[[r:id]]`, and write it. Tracey still checks coverage.

**Terms and facts.** Define a word with a meaning of its own here as `t[word]` and
something we rely on about the world as `f[id] documented|observed|assumed`, each on its
own line with its text after, under `## Terms` or `## Facts` in the spec it belongs to
(the top-level spec, for words used throughout). Cite them with
`[[t:word]]` and `[[f:id]]`. Don't mark a fact documented or observed unless it is.

**Never** mark code reviewed (that's a person's to do), resolve a question a person asked
by deciding it yourself, or delete a thread.

**Before calling it done:**

```bash
{codewalk} check
```
