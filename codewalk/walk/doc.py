"""A codewalk: a Markdown file whose references to the code are checked against it.

Three kinds of reference, each written so the file still reads as plain Markdown:

- **An embedded symbol**, a fenced block with the info string `walk`, one reference per
  line. It's shown as the symbol's code, doc comments and all, with its line numbers:

      ```walk
      BatteryController::on_site_load
      Dispatch::on_short sig
      program_terms > ProgramKind::ErcotErsStrict =>
      impl Hold
      ```

  `sig` after a reference shows only its doc comments and its first line. `>` and some
  text after it shows only part of the symbol: from the first line containing the text,
  through the end of the block that line opens.

- **A symbol inline**, `[[BatteryController::on_site_load]]`, or with a label of its own,
  `[[BatteryController::on_site_load|the battery's site load]]`, or as an ordinary link,
  `[the battery's site load](walk:BatteryController::on_site_load)`.

- **A requirement inline**, `[[r:program.ercot-ers-strict.hold]]`, or as a link,
  `[holds its import](req:program.ercot-ers-strict.hold)`. In a `walk` block,
  `r:program.ercot-ers-strict.hold` shows the requirement with the code that implements
  and verifies it.

- **Proposed code**, not written yet: a block with the info string `walk proposed`, the
  name it will have on its first line and the draft below. Inline, `[[?Name]]`. Neither
  is an error while the name doesn't exist; once it does, the draft is shown against
  what was written, to be settled.

Notes (questions, answers, decisions) are blockquotes; see `notes.py`.

A codewalk may open with YAML front matter (see `FrontMatter`), and its ordinary links
to other codewalks are how codewalks relate to each other.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal, get_args

import yaml
from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from codewalk.code.index import CodeIndex, Symbol, narrow
from codewalk.config import Config
from codewalk.spec import terms
from codewalk.spec.requirements import Requirement, SpecIndex
from codewalk.spec.terms import Definition, Glossary
from codewalk.walk.notes import Note, Thread, threads
from codewalk.walk.review import ReviewState

WIKI = re.compile(r"\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]")


# The stages a PRD goes through, in order
Stage = Literal["problem", "prose", "spec", "code", "work"]
STAGES: tuple[str, ...] = get_args(Stage)


class FrontMatter(BaseModel):
    """What a codewalk says about itself, in YAML at its top.

    All optional; anything else there is left alone, since other tools keep their own keys
    in front matter.
    """

    model_config = ConfigDict(extra="allow")

    # Shown in place of the first heading
    title: str | None = None
    # A sentence or two, for the list of codewalks
    summary: str | None = None
    tags: list[str] = []
    # Other codewalks to read with this one, as paths from this file. Linking to one
    # in the text relates them too
    related: list[str] = []
    # What kind of codewalk: "prd" for one that proposes a change to be made
    kind: str | None = None
    # For a PRD: where it is in its lifecycle; at the problem if it isn't given
    stage: Stage | None = None
    # Where it goes among the others in its folder: lighter first, then those without one,
    # by title
    weight: int | None = None

    @field_validator("tags", "related", mode="before")
    @classmethod
    def _one_or_many(cls, v):
        return [v] if isinstance(v, str) else v


class Ref(BaseModel):
    """One reference a codewalk makes, and what it resolved to."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: str
    # "term" is a `t:` or `f:` reference to a term or fact.
    # "embed" is a line of a `walk` block (a symbol, or with `r:`, a requirement);
    # "proposal" a `walk proposed` block
    kind: Literal["embed", "inline", "req", "proposal", "term"]
    # 1-based line in the codewalk
    line: int
    label: str | None = None
    sig: bool = False
    focus: str | None = None
    symbol: Symbol | None = None
    requirement: Requirement | None = None
    definition: Definition | None = None
    candidates: list[Symbol] = []
    # Why it can't be shown, when it names a symbol but not the part `focus` asks for
    error: str | None = None
    # Proposed: a name that may not exist yet. A proposal's draft code, and its language;
    # for a settled excerpt (`walk settled`), the draft it was written from
    proposed: bool = False
    # A `walk proposed change`: a change to code that exists, proposed until it's settled
    change: bool = False
    settled: bool = False
    draft: str | None = None
    lang: str | None = None

    @property
    def key(self) -> str:
        """What it's reviewed under: the reference as written, focus and all."""
        return f"{self.target} > {self.focus}" if self.focus else self.target

    @property
    def resolved(self) -> bool:
        return self.symbol is not None or self.requirement is not None or self.definition is not None


class Progress(BaseModel):
    """A codewalk's proposals: not written yet, written and waiting to be settled, and settled.

    A PRD starts all proposed and ends all settled.
    """

    proposed: int = 0
    written: int = 0
    settled: int = 0

    @property
    def total(self) -> int:
        return self.proposed + self.written + self.settled

    @property
    def status(self) -> str:
        if not self.total:
            return ""
        if self.proposed == self.total:
            return "proposed"
        if self.settled == self.total:
            return "done"
        return "in progress"


class Problem(BaseModel):
    # "pending" is work in hand, not a fault: a proposal not yet written, or written and
    # waiting to be settled, or a question no one's answered
    severity: Literal["error", "warning", "pending"]
    line: int
    message: str
    ref: str | None = None
    candidates: list[str] = []


# r[impl ref.forms]
def embed_line(line: str) -> tuple[str, str | None, bool] | None:
    """One line of a `walk` block, parsed.

    Parameters
    ----------
    line : str
        The line.

    Returns
    -------
    tuple of (str, str or None, bool) or None
        The reference, its focus (the text after ` > `) and whether it ends `sig`; None for
        a blank line or a `//` comment.
    """
    text = line.strip()
    if not text or text.startswith("//"):
        return None
    sig = text.endswith(" sig")
    if sig:
        text = text[: -len(" sig")].rstrip()
    target, _, focus = text.partition(" > ")
    return target.strip(), focus.strip() or None, sig


def _wikilink(state: StateInline, silent: bool) -> bool:
    if not state.src.startswith("[[", state.pos):
        return False
    m = WIKI.match(state.src, state.pos)
    if not m:
        return False
    if not silent:
        token = state.push("walk_ref", "", 0)
        token.meta = {"target": m.group(1).strip(), "label": (m.group(2) or "").strip() or None}
    state.pos = m.end()
    return True


def markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"])
    md.inline.ruler.before("link", "walk_ref", _wikilink)
    md.use(front_matter_plugin)
    md.use(anchors_plugin, max_level=4, permalink=True, permalinkSymbol="#")
    return md


# r[impl walk.what]
# r[impl prd.check]
def might_be_codewalk(text: str) -> bool:
    """Whether a file makes a reference, or is a PRD, which is checked whether it does or not."""
    refers = "```walk" in text or "[[" in text or any(f"]({s}:" in text for s in ("walk", "req", "term", "fact"))
    return refers or terms.is_prd(text)


class Context:
    """What a codewalk is checked and shown against.

    The project's code, spec and glossary, each indexed, and the review state. There's one
    for a project, shared by every codewalk in it.

    Parameters
    ----------
    root : Path
        The repository's root: every path codewalk deals in is from here.
    config : Config or None
        Where to look; the defaults if None.
    """

    def __init__(self, root: Path, config: Config | None = None):
        self.root = root
        self.config = config or Config()
        self.index = CodeIndex(root, self.config.sources)
        self.spec = SpecIndex(root, self.config.specs)
        self.review = ReviewState(root)
        self.glossary = Glossary(root, [*self.spec.globs, *self.config.docs])

    @property
    def doc_globs(self) -> list[str]:
        return self.config.docs

    def refresh(self) -> bool:
        a = self.index.refresh()
        b = self.spec.refresh()
        c = self.glossary.refresh()
        self.review.load()
        return a or b or c

    def doc_paths(self) -> list[str]:
        return sorted(
            {str(p.relative_to(self.root)) for g in self.doc_globs for p in self.root.glob(g) if p.is_file() and p.suffix == ".md"}
        )

    def spec_paths(self) -> list[str]:
        return sorted({str(p.relative_to(self.root)) for g in self.spec.globs for p in self.root.glob(g) if p.is_file()})

    # r[impl walk.what]
    def codewalks(self) -> list[str]:
        """Markdown files under the docs globs that make at least one reference.

        Spec files aren't codewalks, even when their prose cites requirements: they have
        a view of their own.

        Returns
        -------
        list of str
            Paths from the root, in order.
        """
        specs = set(self.spec_paths())
        return [rel for rel in self.doc_paths() if rel not in specs and might_be_codewalk((self.root / rel).read_text())]

    def editable(self) -> set[str]:
        return set(self.doc_paths()) | {p for p in self.spec_paths() if p.endswith(".md")}


class Walk:
    """One codewalk, parsed, with every reference resolved.

    Parameters
    ----------
    ctx : Context
        The project it's checked against.
    rel : str
        The file, from the root.
    text : str or None
        Its Markdown, if not as saved (while it's being edited).
    """

    def __init__(self, ctx: Context, rel: str, text: str | None = None):
        self.ctx = ctx
        self.rel = rel
        self.text = text if text is not None else (ctx.root / rel).read_text()
        self.md = markdown()
        self.tokens = self.md.parse(self.text)
        self.refs: list[Ref] = []
        # Other Markdown files it links to, as paths from the root
        self.links: list[str] = []
        self.meta = FrontMatter()
        self.meta_error: str | None = None
        self.threads: list[Thread] = [t for _, _, t in threads(self.tokens)]
        self._collect()

    # ---- Parsing --------------------------------------------------------------------

    # r[impl ref.focus]
    def _resolve(self, ref: Ref) -> Ref:
        if ref.target.startswith(("t:", "f:")):
            ref.kind = "term"
            ref.definition = self.ctx.glossary.get(ref.target) or self.own_definition(ref.target)
            return ref
        if ref.target.startswith("r:"):
            if ref.kind == "inline":
                ref.kind = "req"
            ref.requirement = self.ctx.spec.find(ref.target[2:], self.rel)
        else:
            ref.symbol, ref.candidates = self.ctx.index.resolve(ref.target)
            if ref.symbol and ref.focus:
                part = narrow(ref.symbol, ref.focus, self.ctx.index.files)
                if part is None:
                    ref.error = f"`{ref.target}` has no line containing `{ref.focus}`"
                ref.symbol = part
        return ref

    # r[impl check.links]
    def _link(self, href: str) -> None:
        if re.match(r"^[a-z]+:", href) or href.startswith("#"):
            return
        path = href.split("#", 1)[0]
        if not path.endswith(".md"):
            return
        target = os.path.normpath(os.path.join(os.path.dirname(self.rel), path))
        if target not in self.links and target != self.rel:
            self.links.append(target)

    # r[impl ref.forms]
    # r[impl term.cite+2]
    def _collect(self) -> None:
        for tok in self.tokens:
            if tok.type == "front_matter":
                self._front_matter(tok.content)
            elif tok.type == "fence" and tok.info.split()[:2] == ["walk", "proposed"]:
                self.refs.append(self._proposal(tok))
            elif tok.type == "fence" and tok.info.split()[:2] == ["walk", "settled"]:
                if ref := self._settled(tok):
                    self.refs.append(ref)
            elif tok.type == "fence" and tok.info.strip() == "walk":
                start = tok.map[0] + 2 if tok.map else 0
                for i, line in enumerate(tok.content.split("\n")):
                    if parsed := embed_line(line):
                        target, focus, sig = parsed
                        self.refs.append(self._resolve(Ref(target=target, kind="embed", line=start + i, sig=sig, focus=focus)))
            elif tok.type == "inline" and tok.children:
                line = tok.map[0] + 1 if tok.map else 0
                for child in tok.children:
                    if child.type == "walk_ref":
                        target = child.meta["target"]
                        proposed = target.startswith("?")
                        ref = Ref(target=target.lstrip("?"), kind="inline", line=line, label=child.meta["label"], proposed=proposed)
                        self.refs.append(self._resolve(ref))
                    elif child.type == "link_open":
                        href = str(child.attrGet("href") or "")
                        if href.startswith("walk:"):
                            self.refs.append(self._resolve(Ref(target=href[5:], kind="inline", line=line)))
                        elif href.startswith("req:"):
                            self.refs.append(self._resolve(Ref(target="r:" + href[4:], kind="inline", line=line)))
                        elif href.startswith(("term:", "fact:")):
                            target = ("t:" if href.startswith("term:") else "f:") + href.split(":", 1)[1]
                            self.refs.append(self._resolve(Ref(target=target, kind="inline", line=line)))
                        else:
                            self._link(href)
        for rel in self.meta.related:
            self._link(rel)

    # r[impl proposal.draft+2]
    # r[impl proposal.change]
    def _proposal(self, tok) -> Ref:
        """A `walk proposed` block, or `walk proposed change`: the name, then the draft."""
        lines = tok.content.rstrip("\n").split("\n")
        first = next((i for i, l in enumerate(lines) if l.strip()), 0)
        words = tok.info.split()
        change = len(words) > 2 and words[2] == "change"
        lang = words[3 if change else 2] if len(words) > (3 if change else 2) else None
        line = (tok.map[0] + 2 + first) if tok.map else 0
        ref = Ref(
            target=lines[first].strip() if lines else "",
            kind="proposal",
            line=line,
            proposed=True,
            change=change,
            draft="\n".join(lines[first + 1 :]).strip("\n"),
            lang=lang,
        )
        return self._resolve(ref)

    # r[impl proposal.settle]
    def _settled(self, tok) -> Ref | None:
        """A `walk settled` block: a proposal that's been written.

        The code as written is shown, as in a `walk` block, and the draft is kept, to show
        how it differed.

        Parameters
        ----------
        tok : Token
            The fence.

        Returns
        -------
        Ref or None
            The reference, resolved; None if the block names nothing.
        """
        lines = tok.content.rstrip("\n").split("\n")
        first = next((i for i, l in enumerate(lines) if l.strip()), None)
        if first is None or not (parsed := embed_line(lines[first])):
            return None
        target, focus, sig = parsed
        words = tok.info.split()
        ref = Ref(
            target=target,
            kind="embed",
            line=(tok.map[0] + 2 + first) if tok.map else 0,
            focus=focus,
            sig=sig,
            settled=True,
            draft="\n".join(lines[first + 1 :]).strip("\n"),
            lang=words[2] if len(words) > 2 else None,
        )
        return self._resolve(ref)

    def thread_after(self, ref: Ref) -> Thread | None:
        """The thread directly after the block `ref` is in, if there is one."""
        return next((t for t in self.threads if t.about_line is not None and t.about_line <= ref.line < t.line), None)

    # r[impl proposal.agree]
    def agreement(self, ref: Ref) -> Note | None:
        """The last decision in the thread after a proposal: a person agreeing it, or changing it."""
        t = self.thread_after(ref)
        return next((n for n in reversed(t.all()) if n.kind == "decision"), None) if t else None

    # r[impl proposal.progress+2]
    # r[impl proposal.change]
    def progress(self) -> Progress:
        """How far the code it proposes has got: proposed, written, settled."""
        proposals = [r for r in self.refs if r.kind == "proposal"]
        return Progress(
            proposed=sum(1 for r in proposals if not r.symbol or r.change),
            written=sum(1 for r in proposals if r.symbol and not r.change),
            settled=sum(1 for r in self.refs if r.settled),
        )

    def own_definition(self, ref: str) -> Definition | None:
        """In a PRD, a term or fact it defines itself, as `t:id` or `f:id`; else None."""
        if self.meta.kind != "prd":
            return None
        kind, _, did = ref.partition(":")
        return next((d for d in terms.parse(self.rel, self.text) if d.kind[0] == kind and d.id == did), None)

    # r[impl prd.check]
    # r[impl prd.stage-gate]
    def prd_problems(self) -> list[Problem]:
        """A PRD's spec checked against the spec, and anything written ahead of its stage."""
        if self.meta.kind != "prd":
            return []
        from codewalk.walk.prd import spec_changes

        changes = spec_changes(self)
        out = [Problem(severity="error", line=c.line, message=c.error or "") for c in changes if c.how == "error"]
        stage = self.meta.stage or "problem"
        at = STAGES.index(stage)
        ahead = [(c.line, "requirement") for c in changes if c.kind == "requirement" and at < STAGES.index("spec")]
        ahead += [(r.line, "proposal") for r in self.refs if r.kind == "proposal" and at < STAGES.index("code")]
        out += [Problem(severity="warning", line=line, message=f"a {what} at the {stage} stage") for line, what in ahead]
        return out

    def _front_matter(self, content: str) -> None:
        try:
            self.meta = FrontMatter.model_validate(yaml.safe_load(content) or {})
        except (yaml.YAMLError, ValidationError) as e:
            self.meta_error = f"front matter: {str(e).splitlines()[0]}"

    @property
    def title(self) -> str:
        if self.meta.title:
            return self.meta.title
        # The first top-level heading, or failing that the first heading of any level
        headings = [(int(tok.tag[1]), self.tokens[i + 1].content) for i, tok in enumerate(self.tokens) if tok.type == "heading_open"]
        if headings:
            return min(headings, key=lambda h: h[0])[1]
        return Path(self.rel).stem

    @property
    def summary(self) -> str | None:
        """The front matter's summary, or else the first paragraph."""
        if self.meta.summary:
            return self.meta.summary
        for i, tok in enumerate(self.tokens):
            if tok.type == "paragraph_open":
                text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), self.tokens[i + 1].content)
                text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
                return re.sub(r"\s+", " ", text)
        return None

    def headings(self) -> list[tuple[int, str, str]]:
        out = []
        for i, tok in enumerate(self.tokens):
            if tok.type == "heading_open" and tok.tag in ("h2", "h3"):
                out.append((int(tok.tag[1]), self.tokens[i + 1].content, tok.attrGet("id") or ""))
        return out

    @property
    def embeds(self) -> list[Ref]:
        return [r for r in self.refs if r.kind == "embed"]

    def reviewed_count(self) -> tuple[int, int]:
        """How many embedded symbols are reviewed as they stand, of how many.

        Returns
        -------
        reviewed : int
            Those marked reviewed whose code hasn't changed since.
        embedded : int
            Those that resolve.
        """
        shown = [r for r in self.embeds if r.symbol]
        files = self.ctx.index.files
        done = sum(1 for r in shown if (rv := self.ctx.review.get(self.rel, r.key)) and rv.digest == r.symbol.digest(files))
        return done, len(shown)

    # ---- Checking -------------------------------------------------------------------

    # r[impl check.broken]
    # r[impl check.links]
    # r[impl check.strict]
    # r[impl proposal.pending]
    # r[impl term.errors+2]
    # r[impl proposal.draft+2]
    def problems(self) -> list[Problem]:
        out = []
        if self.meta_error:
            out.append(Problem(severity="error", line=1, message=self.meta_error))
        for key, places in self.ctx.glossary.duplicates.items():
            for d in places:
                if d.file == self.rel:
                    others = ", ".join(f"{o.file}:{o.line}" for o in places if o is not d)
                    out.append(Problem(severity="error", line=d.line, message=f"`{key}` is defined again at {others}"))
        for ref in self.refs:
            if ref.kind == "term":
                if not ref.definition:
                    what = "term" if ref.target.startswith("t:") else "fact"
                    out.append(Problem(severity="error", line=ref.line, message=f"no {what} `{ref.target[2:]}`", ref=ref.target))
                continue
            if ref.target.startswith("r:"):
                if not ref.requirement:
                    out.append(Problem(severity="error", line=ref.line, message=f"no requirement `{ref.target[2:]}`", ref=ref.target))
                continue
            if ref.error:
                out.append(Problem(severity="error", line=ref.line, message=ref.error, ref=ref.key))
                continue
            if ref.kind == "proposal" and self.meta.kind != "prd":
                message = f"`{ref.target}` is proposed in a codewalk that isn't a PRD: propose it in one"
                out.append(Problem(severity="warning", line=ref.line, message=message, ref=ref.target))
            if ref.change:
                if ref.symbol:
                    message = f"a change to `{ref.target}` is proposed, not settled yet"
                    out.append(Problem(severity="pending", line=ref.line, message=message, ref=ref.target))
                    continue
            elif ref.proposed:
                if ref.symbol:
                    what = "proposal" if ref.kind == "proposal" else "`?`"
                    out.append(
                        Problem(
                            severity="pending", line=ref.line, message=f"`{ref.target}` is written now: settle the {what}", ref=ref.target
                        )
                    )
                    continue
                ambiguous = len(ref.candidates) > 1 and all(c.name == ref.target.split("::")[-1] for c in ref.candidates)
                if not ambiguous:
                    if ref.kind == "proposal":
                        out.append(
                            Problem(
                                severity="pending", line=ref.line, message=f"`{ref.target}` is proposed, not written yet", ref=ref.target
                            )
                        )
                    continue
            if ref.symbol:
                if ref.kind == "embed":
                    reviewed = self.ctx.review.get(self.rel, ref.key)
                    if reviewed and reviewed.digest != ref.symbol.digest(self.ctx.index.files):
                        out.append(
                            Problem(
                                severity="warning", line=ref.line, message=f"`{ref.key}` has changed since it was reviewed", ref=ref.key
                            )
                        )
                continue
            ambiguous = ref.candidates and all(c.name == ref.target.split("::")[-1] for c in ref.candidates)
            message = f"`{ref.target}` names {len(ref.candidates)} symbols: qualify it" if ambiguous else f"`{ref.target}` names nothing"
            out.append(
                Problem(
                    severity="error",
                    line=ref.line,
                    message=message,
                    ref=ref.target,
                    candidates=[self.ctx.index.shortest_unique(c) for c in ref.candidates],
                )
            )
        for t in self.threads:
            for rq in t.open_requests:
                who = f"@{rq.author}: " if rq.author else ""
                first = rq.text.strip().split("\n")[0][:100]
                out.append(Problem(severity="pending", line=rq.line, message=f"standing request: {who}{first}"))
            for q in t.open_questions:
                who = f"@{q.author}: " if q.author else ""
                first = q.text.strip().split("\n")[0]
                out.append(Problem(severity="pending", line=q.line, message=f"open question: {who}{first[:100]}"))
        for link in self.links:
            if not (self.ctx.root / link).exists():
                line = next((i + 1 for i, l in enumerate(self.text.split("\n")) if os.path.basename(link) in l), 1)
                out.append(Problem(severity="error", line=line, message=f"links to `{link}`, which doesn't exist"))
        return out + self.prd_problems()

    # ---- Exporting to plain Markdown -------------------------------------------------------

    # r[impl export.plain]
    def export(self, out_rel: str) -> str:
        """The codewalk as plain Markdown, for anywhere that won't run this.

        Each embedded symbol becomes a link to it and its code, and each inline one a link.

        Parameters
        ----------
        out_rel : str
            Where it'll be written, from the root, so its links are relative to there.

        Returns
        -------
        str
            The Markdown.
        """
        files = self.ctx.index.files
        base = (self.ctx.root / out_rel).parent

        def link(file: str, line: int) -> str:
            return os.path.relpath(self.ctx.root / file, base) + f"#L{line}"

        embeds = {r.line: r for r in self.embeds}
        proposals = {r.line - 1: r for r in self.refs if r.kind == "proposal"}
        out_lines = []
        lines = self.text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("```walk settled"):
                j = i + 1
                while j < len(lines) and lines[j].strip() != "```":
                    j += 1
                ref = next((embeds[n] for n in range(i + 2, j + 1) if n in embeds), None)
                if ref and (sym := ref.symbol):
                    code = "\n".join(files.lines(sym.file)[sym.start - 1 : sym.end])
                    ind = min((len(l) - len(l.lstrip())) for l in code.split("\n") if l.strip())
                    code = "\n".join(l[ind:] for l in code.split("\n"))
                    out_lines.append(f"[`{sym.file}:{sym.line}`]({link(sym.file, sym.line)})\n\n```{fence_lang(sym.file)}\n{code}\n```")
                i = j + 1
                continue
            if line.strip().startswith("```walk proposed"):
                j = i + 1
                while j < len(lines) and lines[j].strip() != "```":
                    j += 1
                ref = next((r for r in proposals.values() if i < r.line - 1 <= j), None)
                if ref and ref.symbol:
                    out_lines.append(
                        f"[`{ref.symbol.file}:{ref.symbol.line}`]({link(ref.symbol.file, ref.symbol.line)}) (proposed, now written)"
                    )
                elif ref:
                    out_lines.append(f"**Proposed:** `{ref.target}`, not written yet\n\n```{ref.lang or ''}\n{ref.draft}\n```")
                i = j + 1
                continue
            if line.strip() == "```walk":
                j = i + 1
                blocks = []
                while j < len(lines) and lines[j].strip() != "```":
                    if ref := embeds.get(j + 1):
                        if req := ref.requirement:
                            blocks.append(f"> [`{req.id}`]({link(req.file, req.line)}): {req.text}")
                        elif sym := ref.symbol:
                            last = sym.line if ref.sig else sym.end
                            code = "\n".join(files.lines(sym.file)[sym.start - 1 : last])
                            ind = min((len(l) - len(l.lstrip())) for l in code.split("\n") if l.strip())
                            code = "\n".join(l[ind:] for l in code.split("\n"))
                            blocks.append(
                                f"[`{sym.file}:{sym.line}`]({link(sym.file, sym.line)})\n\n```{fence_lang(sym.file)}\n{code}\n```"
                            )
                        else:
                            blocks.append(f"> **Unresolved:** `{ref.key}`")
                    j += 1
                out_lines.append("\n\n".join(blocks))
                i = j + 1
                continue

            def wiki(m):
                target, label = m.group(1).strip(), (m.group(2) or "").strip()
                if target.startswith("r:"):
                    r = self.ctx.spec.find(target[2:], self.rel)
                    return f"[`{label or target[2:]}`]({link(r.file, r.line)})" if r else f"`{target[2:]}`"
                sym, _ = self.ctx.index.resolve(target)
                return f"[`{label or (sym.name if sym else target)}`]({link(sym.file, sym.line)})" if sym else f"`{label or target}`"

            def walk_link(m):
                sym, _ = self.ctx.index.resolve(m.group(2))
                return f"[{m.group(1)}]({link(sym.file, sym.line)})" if sym else m.group(1)

            line = WIKI.sub(wiki, line)
            line = re.sub(r"\[([^\]]+)\]\(walk:([^)\s]+)\)", walk_link, line)
            out_lines.append(line)
            i += 1
        header = f"<!-- Exported from {self.rel} by codewalk: edit that, not this -->\n\n"
        return header + "\n".join(out_lines)


# r[impl prd.stage-set]
def set_front_matter(text: str, key: str, value: str) -> str:
    """`text` with `key: value` in its front matter, replacing the key if it's there.

    Parameters
    ----------
    text : str
        The codewalk's Markdown.
    key : str
        The front matter's key.
    value : str
        Its value, written as it is.

    Returns
    -------
    str
        The Markdown, with front matter added if it had none.
    """
    lines = text.split("\n")
    if lines and lines[0] == "---" and "---" in lines[1:]:
        end = lines.index("---", 1)
        for i in range(1, end):
            if re.match(rf"{re.escape(key)}\s*:", lines[i]):
                lines[i] = f"{key}: {value}"
                return "\n".join(lines)
        return "\n".join(lines[:end] + [f"{key}: {value}"] + lines[end:])
    return "\n".join(["---", f"{key}: {value}", "---", "", *lines])


# r[impl proposal.settle]
# r[impl proposal.change]
def settle(text: str, line: int, target: str) -> str:
    """`text` with the `walk proposed` (or `walk proposed change`) block whose name is on `line` settled.

    It becomes a `walk settled` block, which shows `target`'s code as written and keeps the
    draft, so what was planned and what happened can both be seen.

    Parameters
    ----------
    text : str
        The codewalk's Markdown.
    line : int
        The line the proposal's name is on, 1-based.
    target : str
        The reference to the code as written, put in place of the name.

    Returns
    -------
    str
        The Markdown with the block settled.
    """
    lines = text.split("\n")
    start = next(i for i in range(line - 1, -1, -1) if lines[i].strip().startswith("```walk proposed"))
    lines[start] = re.sub(r"walk proposed(?: change)?", "walk settled", lines[start], count=1)
    lines[line - 1] = target
    return "\n".join(lines)


def fence_lang(file: str) -> str:
    return {".rs": "rust", ".py": "python"}.get(Path(file).suffix, "")
