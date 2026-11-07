---
name: codewalk-propose
description: Propose a change as a codewalk, before writing it - the existing code named, the new code drafted, questions asked in place
disable-model-invocation: false
---

Propose the change the user describes as a codewalk, before writing any of it. The
codewalk is where the person and you work it out: they read it in codewalk, with every
piece of code shown in place, and answer your questions in it.

1. **Read what's in hand** with `{codewalk} context`, and the codewalks and specs the
   change touches. If a codewalk already covers this area, extend it rather than
   starting another.
2. **Find the code** the change touches with `{codewalk} find QUERY`, and read it.
3. **Write the codewalk** at `{codewalks}/<slug>.md` (for a PRD, start it with
   `{codewalk} new PATH --title T --prd`, wherever the project keeps PRDs, and write
   only what its `stage` allows: no requirements before the spec stage, no proposals
   before the code stage), with front
   matter (a `summary`, `tags`, and `related` for codewalks it builds on):
   - What the change is for, in a paragraph a person can agree or disagree with.
   - How the code works now, each part named in a `walk` block (`> text` to show only
     part of a symbol), with what matters about it said in prose.
   - What will change: each new or changed symbol in a `walk proposed` block under the
     name it will have, with the draft code and the requirement markers it will carry
     (`// r[impl id]`, `// r[verify id]` on tests), so the margin links each to its
     requirement and its prose. Inline, `[[?Name]]` for a name to come.
   - The requirements it touches or adds, cited as `[[r:id]]`; new ones drafted in the
     prose, to be written into the spec once agreed.
   - Terms it relies on as `[[t:word]]`, and facts as `[[f:id]]`: define any that are
     missing.
4. **Ask** what you can't decide, as `> [!question] @agent: …` directly under what it's
   about. Ask few, specific questions, each one you need answered to go on.
5. **Check** with `{codewalk} check`: every reference resolves, and the proposals and
   questions show as in hand.
6. **Stop**, and tell the person the codewalk is ready to read in codewalk
   (`{codewalk} serve`), with the questions you asked. Don't write the code yet.
