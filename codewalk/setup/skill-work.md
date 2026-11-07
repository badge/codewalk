---
name: codewalk-work
description: Work through a codewalk - answer its questions, write what it proposes, settle the proposals, keep it true
disable-model-invocation: false
---

Carry a codewalk forward: the person has read it, answered or asked in it, and now
you do the work it describes. The codewalk is the record of what was agreed; keep it
true as you go.

1. **Read what's in hand** with `{codewalk} context` (or `{codewalk} context
   CODEWALK`). Read the codewalk, and every thread in it.
2. **Answer** each open question you can, in its thread: `> [!answer] @agent: …`. A
   `[!decision]` from a person settles a question; follow it. If a decision is still
   needed, stop and say so.
3. **Write the code** each agreed `walk proposed` block proposes (`{codewalk} context`
   says which: a person agrees one with a decision in the thread under it), as the
   threads say, following the project's own process (its spec, tests and checks). Don't
   write one that isn't agreed; if it's ready, ask for it to be.
4. **Settle each proposal** once its name exists: compare what you wrote with the draft,
   say in the prose where and why they differ, and settle it (`walk proposed` becomes
   `walk settled`, keeping the draft, so what was planned stays beside what was built).
   Do any standing requests (`[!request]`) too, and add `[!done]` to each saying what you
   did.
5. **Update the specs** the codewalk cites: write requirements it drafted, cite each
   from the prose that gives rise to it, and keep the prose and requirements agreeing.
6. **Check** with `{codewalk} check`, then `{codewalk} context` to see what's left.
7. **Report** what you did, what's left in hand, and what the person should review. Don't
   mark anything reviewed: that's for the person, in codewalk.
