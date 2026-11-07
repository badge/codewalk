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

from codewalk.walk.doc import Context, Walk


class Item(BaseModel):
    line: int
    text: str
    # What it's about: the names it refers to, or that sit just above it
    about: list[str] = []


class Brief(BaseModel):
    walkthrough: str
    title: str
    requests: list[Item] = []
    questions: list[Item] = []
    proposed: list[Item] = []
    written: list[Item] = []
    changed: list[Item] = []
    broken: list[Item] = []

    @property
    def empty(self) -> bool:
        return not (self.requests or self.questions or self.proposed or self.written or self.changed or self.broken)


# r[impl context.brief]
def brief(ctx: Context, rel: str) -> Brief:
    w = Walk(ctx, rel)
    out = Brief(walkthrough=rel, title=w.title)
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
        if r.symbol:
            out.written.append(Item(line=r.line, text=f"{r.symbol.file}:{r.symbol.line}", about=[r.target]))
        elif len(r.candidates) <= 1 or not all(c.name == r.target.split("::")[-1] for c in r.candidates):
            out.proposed.append(Item(line=r.line, text=r.draft or "", about=[r.target]))
    for p in w.problems():
        if p.severity == "warning":
            out.changed.append(Item(line=p.line, text=p.message, about=[p.ref] if p.ref else []))
        elif p.severity == "error":
            out.broken.append(
                Item(line=p.line, text=p.message + (f" (did you mean {', '.join(p.candidates[:4])}?)" if p.candidates else ""))
            )
    return out


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
        sections = [
            ("Standing requests", "do each, then add `> [!done] @you: ...` to its thread, saying what you did", b.requests),
            ("Open questions", "answer each in place, with `> [!answer] @you: ...` added to its thread", b.questions),
            ("Proposed, not written yet", "write it, or revise the proposal", b.proposed),
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
                    lines.append(f"- line {item.line}{about}:\n\n  ```\n  {body}\n  ```")
                else:
                    lines.append(f"- line {item.line}{about}: {body}")
            lines.append("")
    return "\n".join(lines)
