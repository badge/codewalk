"""Notes: questions, answers, decisions and requests, kept in the walkthrough itself.

A thread is a blockquote whose paragraphs start with a kind, and optionally who wrote it:

    > [!question] @matthew: Why is replanning per battery, not per group?
    >
    > [!answer] @claude: Because a battery's site is what it can see and act on…
    >
    > [!decision] @matthew: Per battery. Revisit if groups ever share a battery.

A paragraph without a kind carries on the note above it. It's about whatever comes just
before it: the excerpt or paragraph it sits under.

A note can have replies of its own, in a blockquote nested under it, for refining it
without losing which note the refinement is about:

    > [!request] @matthew: Use NumPy-style docstrings throughout.
    >
    > [!done] @claude: Converted every module's.
    >
    > > [!question] @matthew: The CLI's too?
    > >
    > > [!answer] @claude: No: click shows those as `--help`.

A question is **open** until an answer or a decision follows it, at its own level or in
its replies; a **request** (a standing ask, for something that applies throughout) stands
until a `[!done]` does. A thread is open while any question or request in it is, at any
depth.

A thread that's settled can be **resolved**: moved to the walkthrough's changelog,
compacted to one line (what was asked, and how it was settled), or removed outright.

Notes live in the Markdown, not beside it, so they show in a diff, go wherever the file
goes, and are there for the next person, or the next agent, to read. That's what makes a
walkthrough a dialogue that carries across runs.
"""

from __future__ import annotations

import re
from typing import Literal

from markdown_it.token import Token
from pydantic import BaseModel

KINDS = ("question", "answer", "decision", "note", "request", "done")
NOTE = re.compile(r"^\[!(question|answer|decision|note|request|done)\][ \t]*(?:@([\w.\-]+):?)?[ \t]*", re.IGNORECASE)
CHANGELOG = "## Changelog"

Kind = Literal["question", "answer", "decision", "note", "request", "done"]
SETTLES = {"question": ("answer", "decision"), "request": ("done",)}


class Note(BaseModel):
    kind: Kind
    author: str | None
    # The Markdown of its body, kind and author taken off
    text: str
    # Its first and last lines, 1-based, its replies included
    line: int
    end: int
    # 0 for a note in the thread itself, 1 for a reply to one, and so on
    depth: int = 0
    replies: list[Note] = []

    def walk(self):
        """This note, then its replies, depth first."""
        yield self
        for r in self.replies:
            yield from r.walk()


def _unsettled(notes: list[Note], kind: str) -> list[Note]:
    """The notes of `kind` (questions or requests) nothing has settled yet, at any depth.

    A note is settled by one of the kinds that settle it coming after it at its own level,
    or among its own replies.
    """
    out = []
    for i, n in enumerate(notes):
        if n.kind == kind:
            later = [m.kind for m in notes[i + 1 :]] + [m.kind for m in n.replies]
            if not any(k in SETTLES[kind] for k in later):
                out.append(n)
        out += _unsettled(n.replies, kind)
    return out


class Thread(BaseModel):
    # First line of the blockquote, 1-based, and the line after it, 0-based: so
    # `lines[line - 1 : end]` is the thread
    line: int
    end: int
    notes: list[Note]
    # What it's about: the line of the block just before it, if any
    about_line: int | None = None

    def all(self) -> list[Note]:
        return [m for n in self.notes for m in n.walk()]

    @property
    def open_questions(self) -> list[Note]:
        return _unsettled(self.notes, "question")

    @property
    def open_requests(self) -> list[Note]:
        return _unsettled(self.notes, "request")

    @property
    def open(self) -> bool:
        return bool(self.open_questions)

    @property
    def request_open(self) -> bool:
        return bool(self.open_requests)

    @property
    def settled(self) -> bool:
        """Nothing in it waits on anyone: it can be resolved."""
        return not self.open_questions and not self.open_requests

    @property
    def request(self) -> Note | None:
        return next((n for n in reversed(self.all()) if n.kind == "request"), None)

    @property
    def question(self) -> Note | None:
        return next((n for n in reversed(self.all()) if n.kind == "question"), None)

    def find(self, line: int) -> Note | None:
        return next((n for n in self.all() if n.line == line), None)


def threads(tokens: list[Token]) -> list[tuple[int, int, Thread]]:
    """Every thread in a parsed walkthrough.

    Parameters
    ----------
    tokens : list of Token
        The walkthrough, parsed.

    Returns
    -------
    list of tuple of (int, int, Thread)
        For each, the index of its blockquote_open token, the index of its
        blockquote_close, and the thread.
    """
    out = []
    last_block_line: int | None = None
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "blockquote_open" and tok.level == 0:
            close = _close(tokens, i)
            notes = parse_notes(tokens, i, close, 0)
            if notes:
                first = tok.map
                thread = Thread(line=first[0] + 1 if first else 0, end=first[1] if first else 0, notes=notes)
                thread.about_line = last_block_line
                out.append((i, close, thread))
            i = close + 1
            continue
        if tok.level == 0 and tok.map and tok.nesting in (0, 1) and tok.type not in ("front_matter",):
            last_block_line = tok.map[0] + 1
        i += 1
    return out


def _close(tokens: list[Token], i: int) -> int:
    depth = 0
    for j in range(i, len(tokens)):
        if tokens[j].type == "blockquote_open":
            depth += 1
        elif tokens[j].type == "blockquote_close":
            depth -= 1
            if depth == 0:
                return j
    return len(tokens) - 1


def blocks(tokens: list[Token], start: int, close: int) -> list[tuple[int, int]]:
    """The blocks directly inside the container from `start` to `close`, as (first, last)
    token indices."""
    out = []
    j = start + 1
    while j < close:
        tok = tokens[j]
        if tok.nesting == 1:
            depth, k = 0, j
            while k < close:
                depth += tokens[k].nesting
                if depth == 0:
                    break
                k += 1
            out.append((j, k))
            j = k + 1
        else:
            out.append((j, j))
            j += 1
    return out


def parse_notes(tokens: list[Token], start: int, close: int, depth: int) -> list[Note] | None:
    """The notes in the blockquote from `start` to `close`, or None if it isn't a thread
    (an ordinary quote, whose first paragraph has no kind)."""
    notes: list[Note] = []
    for a, b in blocks(tokens, start, close):
        tok = tokens[a]
        end = tok.map[1] if tok.map else 0
        if tok.type == "blockquote_open":
            replies = parse_notes(tokens, a, b, depth + 1)
            if replies and notes:
                notes[-1].replies += replies
                notes[-1].end = max(notes[-1].end, end)
            elif notes:
                notes[-1].end = max(notes[-1].end, end)
            continue
        inline = tokens[a + 1] if tok.type == "paragraph_open" else None
        m = NOTE.match(inline.content) if inline is not None else None
        if m:
            line = tok.map[0] + 1 if tok.map else 0
            notes.append(Note(kind=m.group(1).lower(), author=m.group(2), text=inline.content[m.end() :], line=line, end=end, depth=depth))
        elif notes:
            if inline is not None:
                notes[-1].text += "\n\n" + inline.content
            notes[-1].end = max(notes[-1].end, end)
        else:
            return None
    return notes or None


# ---- Writing notes into the Markdown --------------------------------------------------------


def _quote(kind: str, author: str | None, body: str, depth: int = 0) -> list[str]:
    head = f"[!{kind}]" + (f" @{author}:" if author else "")
    lines = body.strip().split("\n")
    prefix = "> " * (depth + 1)
    return [f"{prefix}{head} {lines[0]}".rstrip()] + [f"{prefix}{l}".rstrip() for l in lines[1:]]


def ask(text: str, after_line: int, author: str | None, body: str) -> str:
    """`text` with a new question thread after line `after_line`, set off by blank lines.

    Parameters
    ----------
    text : str
        The walkthrough's Markdown.
    after_line : int
        The line to put it after, 1-based.
    author : str or None
        Who's asking.
    body : str
        The question.

    Returns
    -------
    str
        The Markdown with the thread in.
    """
    lines = text.split("\n")
    at = min(after_line, len(lines))
    block = ["", *_quote("question", author, body), ""]
    if at < len(lines) and lines[at].strip() == "":
        block = block[:-1]
    return "\n".join(lines[:at] + block + lines[at:])


def ask_about(text: str, line: int, author: str | None, body: str) -> str:
    """`text` with a new question about the reference on line `line` of a `walk` block.

    The question goes straight after that reference: if more of the block follows, the
    block is split in two there, so the question sits under what it's about.

    Parameters
    ----------
    text : str
        The walkthrough's Markdown.
    line : int
        The reference's line, 1-based.
    author : str or None
        Who's asking.
    body : str
        The question.

    Returns
    -------
    str
        The Markdown with the thread in.
    """
    lines = text.split("\n")
    i = line - 1
    opens = [j for j in range(i, -1, -1) if lines[j].lstrip().startswith("```")]
    closes = [k for k in range(i + 1, len(lines)) if lines[k].strip().startswith("```")]
    if not opens or not closes:
        return ask(text, line, author, body)
    fence, close = lines[opens[0]].strip(), closes[0]
    if not any(lines[k].strip() for k in range(i + 1, close)):
        return ask(text, close + 1, author, body)
    return "\n".join([*lines[: i + 1], "```", "", *_quote("question", author, body), "", fence, *lines[i + 1 :]])


def reply(text: str, thread: Thread, kind: Kind, author: str | None, body: str) -> str:
    """`text` with a note added to the end of `thread`.

    Parameters
    ----------
    text : str
        The walkthrough's Markdown.
    thread : Thread
        The thread, as parsed from `text`.
    kind : Kind
        The note's kind.
    author : str or None
        Who wrote it.
    body : str
        The note.

    Returns
    -------
    str
        The Markdown with the note in.
    """
    lines = text.split("\n")
    end = thread.end  # the line after the blockquote, 0-based, so the insertion point
    while end > thread.line and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[:end] + [">", *_quote(kind, author, body)] + lines[end:])


def reply_to(text: str, note: Note, kind: Kind, author: str | None, body: str) -> str:
    """`text` with a reply to one note, nested under it, after any replies it has.

    Parameters
    ----------
    text : str
        The walkthrough's Markdown.
    note : Note
        The note replied to, as parsed from `text`.
    kind, author, body
        As for `reply`.

    Returns
    -------
    str
        The Markdown with the reply in.
    """
    lines = text.split("\n")
    end = note.end
    while end > note.line and not lines[end - 1].strip().strip(">").strip():
        end -= 1
    separator = ("> " * (note.depth + 1)).rstrip()
    return "\n".join(lines[:end] + [separator, *_quote(kind, author, body, note.depth + 1)] + lines[end:])


def _sentence(text: str, limit: int = 160) -> str:
    """The first sentence of a note, on one line."""
    flat = re.sub(r"\s+", " ", text.strip())
    first = re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def compact(thread: Thread, date: str, about: list[str] | None = None) -> str:
    """A settled thread as one changelog line: what was asked, and how it was settled.

    Parameters
    ----------
    thread : Thread
        The thread.
    date : str
        When it was resolved, as ``YYYY-MM-DD``.
    about : list of str, optional
        The names it was about, if it sat under an excerpt.

    Returns
    -------
    str
        A Markdown list item. Any notes between the first and the one that settled it are
        counted, not kept.
    """
    notes = thread.all()
    first = notes[0]
    last = next((n for n in reversed(notes) if n.kind in ("done", "decision", "answer")), notes[-1])

    def said(n: Note) -> str:
        who = f" @{n.author}" if n.author else ""
        return f"**{n.kind}**{who}: {_sentence(n.text)}"

    line = f"- {date}"
    if about:
        line += " (" + ", ".join(f"`{a}`" for a in about) + ")"
    line += f": {said(first)}"
    if last is not first:
        line += f" → {said(last)}"
    between = len(notes) - (2 if last is not first else 1)
    if between > 0:
        line += f" ({between} more note{'s' if between > 1 else ''})"
    return line


def resolve(text: str, thread: Thread, mode: Literal["changelog", "remove"], date: str, about: list[str] | None = None) -> str:
    """`text` with a settled thread taken out: compacted into the changelog, or removed.

    Parameters
    ----------
    text : str
        The walkthrough's Markdown.
    thread : Thread
        The thread, as parsed from `text`.
    mode : {"changelog", "remove"}
        Whether to keep a line of it in the changelog, a `## Changelog` section at the end
        (made if there isn't one), newest first.
    date : str
        Today, as ``YYYY-MM-DD``.
    about : list of str, optional
        The names it was about.

    Returns
    -------
    str
        The Markdown without the thread.

    Raises
    ------
    ValueError
        If a question or request in it is still open.
    """
    if not thread.settled:
        raise ValueError("it's still open: answer or do what it asks first")
    lines = text.split("\n")
    start, end = thread.line - 1, thread.end
    # Take the thread and one blank line around it
    if start > 0 and not lines[start - 1].strip() and end < len(lines) and not lines[end].strip():
        start -= 1
    lines = lines[:start] + lines[end:]
    if mode == "changelog":
        entry = compact(thread, date, about)
        if CHANGELOG in lines:
            head = lines.index(CHANGELOG)
            stop = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("#")), len(lines))
            first = next((i for i in range(head + 1, stop) if lines[i].startswith("- ")), None)
            if first is not None:
                lines = lines[:first] + [entry] + lines[first:]
            else:
                at = stop
                while at > head + 1 and not lines[at - 1].strip():
                    at -= 1
                lines = lines[:at] + ["", entry] + lines[at:]
        else:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ["", CHANGELOG, "", "What was asked here and how it was settled, newest first.", "", entry, ""]
    return "\n".join(lines)
