"""What's in hand in the walkthroughs, for whoever picks the work up next.

That's open questions, code proposed but not written, proposals written and waiting to be
settled, code changed since someone reviewed it, and references that no longer resolve.

`codewalk context` prints it, as Markdown for an agent to read at the start of a run, or
as JSON. It's the walkthroughs' half of a dialogue that carries across runs: the human
asks and decides in the walkthrough, the agent reads this, does the work, answers in the
walkthrough, and the next run starts from there.
"""

from __future__ import annotations

from pydantic import BaseModel

from codewalk.walk.doc import Context, Stage, Walk


class Item(BaseModel):
    line: int
    text: str
    # What it's about: the names it refers to, or that sit just above it
    about: list[str] = []
    # For a proposal: the decision agreeing it, as `@author: text`
    agreed: str | None = None


class Brief(BaseModel):
    walkthrough: str
    title: str
    # For a PRD, its stage, and so what may be written in it yet
    stage: Stage | None = None
    requests: list[Item] = []
    questions: list[Item] = []
    proposed: list[Item] = []
    written: list[Item] = []
    changed: list[Item] = []
    broken: list[Item] = []

    @property
    def empty(self) -> bool:
        return not self.stage and not (self.requests or self.questions or self.proposed or self.written or self.changed or self.broken)


# r[impl context.brief]
def brief(ctx: Context, rel: str) -> Brief:
    w = Walk(ctx, rel)
    stage = (w.meta.stage or "problem") if w.meta.kind == "prd" else None
    out = Brief(walkthrough=rel, title=w.title, stage=stage)
    for t in w.threads:
        about = [r.key for r in w.refs if r.kind in ("embed", "proposal") and t.about_line is not None and t.about_line <= r.line < t.line]
        for rq in t.open_requests:
            who = f"@{rq.author}: " if rq.author else ""
            out.requests.append(Item(line=rq.line, text=who + rq.text.strip(), about=about))
        for q in t.open_questions:
            who = f"@{q.author}: " if q.author else ""
            out.questions.append(Item(line=q.line, text=who + q.text.strip(), about=about))
    for r in w.refs:
        if r.kind != "proposal":
            continue
        if r.symbol and not r.change:
            out.written.append(Item(line=r.line, text=f"{r.symbol.file}:{r.symbol.line}", about=[r.target]))
        elif len(r.candidates) <= 1 or not all(c.name == r.target.split("::")[-1] for c in r.candidates):
            d = w.agreement(r)
            agreed = ((f"@{d.author}: " if d.author else "") + d.text.strip()) if d else None
            out.proposed.append(Item(line=r.line, text=r.draft or "", about=[r.target], agreed=agreed))
    for p in w.problems():
        if p.severity == "warning":
            out.changed.append(Item(line=p.line, text=p.message, about=[p.ref] if p.ref else []))
        elif p.severity == "error":
            out.broken.append(
                Item(line=p.line, text=p.message + (f" (did you mean {', '.join(p.candidates[:4])}?)" if p.candidates else ""))
            )
    return out


# What a PRD's stage allows to be written in it, for an agent
MAY_WRITE = {
    "problem": "write the problem; no requirements or proposals yet.",
    "prose": "write the prose, and the terms and facts it needs; no requirements or proposals yet.",
    "spec": "write the requirements that follow from the prose; no proposals yet.",
    "code": "propose the shape of the code and its tests, in outline.",
    "work": "move the prose and requirements into the spec, write the code, and settle the proposals.",
}


# r[impl prd.stage]
# r[impl prd.stage-gate]
def as_markdown(briefs: list[Brief]) -> str:
    """For an agent to read: each walkthrough with anything in hand, and what to do.

    Parameters
    ----------
    briefs : list of Brief
        One per walkthrough; those with nothing in hand are left out.

    Returns
    -------
    str
        The Markdown.
    """
    lines = ["# codewalk: what's in hand", ""]
    todo = [b for b in briefs if not b.empty]
    if not todo:
        return "\n".join(lines + ["Nothing: every reference resolves, no questions are open and no proposals are waiting.", ""])
    for b in todo:
        lines += [f"## {b.title}", "", f"`{b.walkthrough}`", ""]
        if b.stage:
            lines += [f"A PRD at the **{b.stage}** stage: {MAY_WRITE[b.stage]}", ""]
        sections = [
            ("Standing requests", "do each, then add `> [!done] @you: ...` to its thread, saying what you did", b.requests),
            ("Open questions", "answer each in place, with `> [!answer] @you: ...` added to its thread", b.questions),
            ("Proposed, not written yet", "write those a person has agreed; revise the others as their threads say", b.proposed),
            ("Proposed and now written", "check it against the draft, then settle the block into an ordinary `walk` block", b.written),
            ("Changed since it was reviewed", "check the text around it is still true; a person marks it reviewed", b.changed),
            ("Broken", "fix the reference", b.broken),
        ]
        for heading, what, items in sections:
            if not items:
                continue
            lines += [f"### {heading} ({len(items)})", "", f"_{what}._", ""]
            for item in items:
                about = f" (`{'`, `'.join(item.about)}`)" if item.about else ""
                body = item.text.strip().replace("\n", "\n  ")
                if heading.startswith("Proposed, not"):
                    agreed = f", agreed ({item.agreed.splitlines()[0]})" if item.agreed else ", not agreed yet"
                    lines.append(f"- line {item.line}{about}{agreed}:\n\n  ```\n  {body}\n  ```")
                else:
                    lines.append(f"- line {item.line}{about}: {body}")
            lines.append("")
    return "\n".join(lines)
