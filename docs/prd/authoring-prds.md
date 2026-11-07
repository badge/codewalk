---
title: "Authoring PRDs"
summary: "A PRD goes from the problem to prose, a spec and the shape of the code, in stages, in one file that reads on its own, with its spec shown against the spec as it stands."
kind: prd
stage: work
tags: [prd, spec]
related: ["../codewalk.md"]
---

# Authoring PRDs

A PRD is how we agree a change before making it: the problem, what we'll do about it, the
spec that follows, and the shape of the code. This one says how a PRD should be written
in codewalk, and what codewalk needs to support it.

## The problem

codewalk can start a PRD with `codewalk new PATH --title T --prd`, which writes a
walkthrough from a template with `kind: prd` in its front matter, and it counts a PRD's
progress by its proposals:

```walk
cli::new
FrontMatter::kind
Walk::progress
```

That's all it knows about PRDs, and it gets the order wrong:

- **It starts with code.** The template has sections for the spec and the code, with a
  sample proposal and a sample question, both of which count as work in hand from the
  moment it's written. Progress is measured only in code. Nothing knows the stages a PRD
  goes through, so nothing stops one jumping to code before the spec is agreed: the first
  draft of this PRD did exactly that.
- **A PRD can't hold a spec.** Requirements, terms and facts are read only from the spec's
  files. A requirement written in a PRD isn't read at all, and a term it defines that the
  spec already has is an error, defined twice. So a PRD either describes its changes to
  the spec, leaving the reader to imagine them, or makes them in the spec, so it can only
  be read with the rest of the repository open beside it. Neither reads on its own.
- **codewalk can't read a versioned requirement.** tracey marks a changed requirement by
  bumping its version ([[f:tracey.versions]]), but codewalk doesn't recognise `r[id+2]`
  in a spec or `r[impl id+2]` in code.
- **`codewalk check` doesn't check a spec.** It checks walkthroughs only, so a term cited
  and not defined in a spec file is reported only on that file's page.
- **A change to existing code can't be proposed.** A `walk proposed` block whose name
  exists reads as written at once, so it can only propose new code.
- **The browser can't start a PRD.** It can ask, answer, agree, settle, review and
  reconcile, but there's no way to begin one there.

## What we want

### A PRD reads on its own

Everything a PRD proposes is in it, so someone who knows the codebase can read it and
nothing else, and know what will change and why. Nothing outside it changes while it's
proposed: not the spec, not the code. Once the work is done it may go stale, and that's
fine: by then the spec and the code say what's true, and the PRD is the record of why.

### In stages

A PRD is written in five stages, each broadly agreed before the next is begun in
earnest:

1. **The problem.** Why we want a change: a feature, a fix, whatever it is. It can name the
   code it's about as it stands.
2. **The prose.** What we'll do about it, in words, and the terms and facts the rest of
   the PRD needs, which can be defined while the prose is still being written. Rough
   examples are fine; proposals aren't.
3. **The spec.** The requirements that follow from the prose, going back and forth between
   the two until the spec is something we can work from.
4. **The code.** The shape of the code and of its tests, in outline (below).
5. **The work.** The change itself: the prose and requirements move into the spec, the
   code is written, and the PRD is updated to name the code as written.

Going back is normal: a question about the spec can send the prose back for another look.
A PRD records its stage in its front matter, `stage: prose`, which codewalk shows on the
index, on its page and in `codewalk context` (`prd.stage`), and which the person sets
from its page when they agree a stage (`prd.stage-set`). The stage gates what belongs to
later stages, not earlier ones: while a PRD is at the prose, no requirements or code are
written into it; once it's at the code, the prose and the spec can still be revised
(`prd.stage-gate`). It's a guide to what comes next, not a lock: the prose needn't
be final before the spec is begun, only broadly agreed.

### Its spec, against the spec as it stands

A PRD's requirements are written in it as they'll read in the spec, and read as its own
proposals, not the spec's (`prd.requirements`). That means codewalk has to read a
requirement's version, in the spec and in code (`spec.prefix`, `spec.traces`). Each is
shown against the spec as it stands (`prd.compare`). A requirement whose ID the spec
doesn't have is new. One whose ID it has, with the version bumped, is a change, and is
shown with the old text beside the new. One with an ID the spec has and the same text is
quoted for context, and is shown as such; one with an ID the spec has, changed text and no
new version is an error. A requirement the PRD removes is written as its marker with the
version bumped and the word `removed` after it, `r[id+2] removed`, and is listed as
removed.

Terms and facts work the same way: a PRD's definition of a word the spec already defines is
a proposed change to it, shown against it, not a second definition (`prd.terms`,
`term.errors`). This PRD has one: a
[[t:prd]] is no longer "a walkthrough whose code is all proposed", but a walkthrough with
`kind: prd` that proposes a change in stages, from the problem to the code, and reads on
its own. (It's written here rather than as a definition, since until this is done a
second definition is an error.)

The spec view, the glossary and tracey go on reading only the spec itself, so a PRD's
proposals don't count until they're moved into it, at the work. `codewalk check` checks a
PRD's spec as it checks its references: a changed requirement without a new version, or a
term cited and defined nowhere, is an error (`prd.check`).

### Its code, in outline

At the code stage a PRD shows the shape of the code, as much of it as it takes to agree
it, and no more. Changes to the data model are shown in full. Code that implements a
requirement carries its marker, and is shown in full where it's intricate enough to be
worth agreeing line by line, or by its signature where it's routine. Helpers that
implement nothing aren't proposed. Tests are proposed the same way, by the requirement
each verifies.

New code is proposed in a `walk proposed` block, as now. A change to code that exists is
proposed in a `walk proposed change` block, which shows the draft against the code as it
is, and stays proposed until it's settled (`proposal.change`).

### Wherever it's written

A PRD is Markdown, so it can be written anywhere: in the browser, in an editor, by an agent,
with or without codewalk running. The browser adds what an editor can't: everything shown
in place, and a person's part of the conversation (asking, answering, agreeing, setting
the stage) a click away.

In the browser, a person starts a PRD from the index with **New PRD**: a title and, in
their own words, what they want. codewalk writes the PRD at `docs/prd/` and the title's
slug, at the problem stage, from a template with a section for each stage and no samples
(`prd.template`), with what they asked for as a standing request at the top, and opens it
(`prd.start`). An agent working
in the same folder finds the request with `codewalk context`, and writes into the stage
the PRD is at. codewalk is for local use: the server and the agent on the person's own
machine, in the same folder.

PRDs have nothing to do with branches or worktrees: a PRD is a file, and the process
neither creates nor manages either. Where the work is done is up to whoever does it.

### A changelog to write in

Settled threads go into the changelog at the end, each compacted to a line. Anything else
worth recording about how the PRD got where it is can be written there too, by hand.

## The spec

The requirements that follow from the prose, as they'll read in the spec: new ones, and
changes to existing ones with their versions bumped. Once agreed, the new `prd.*` ones go
in a spec file of their own, and each changed one replaces its earlier version where it
is.

### Stages

r[prd.template]
`codewalk new PATH --title T --prd` MUST write a PRD with `kind: prd` and `stage: problem`
in its front matter and a section for each stage, and with no `walk proposed` block and no
note.

r[prd.stage]
A PRD's stage MUST be read from `stage` in its front matter, one of `problem`, `prose`,
`spec`, `code` and `work`, or `problem` if it has none, and MUST be shown with the PRD on
the index, on its page, and in `codewalk context`.

r[prd.stage-set]
A PRD's page MUST let a person set its stage, writing it into the front matter.

r[prd.stage-gate]
`codewalk check` MUST warn of a requirement written in a PRD before its stage is `spec`,
and of a proposal written in a PRD before its stage is `code`; and `codewalk context` MUST
say, for each PRD, what its stage allows to be written.

### Its spec

r[spec.prefix+2]
A line consisting only of `prefix[id]` or `prefix[id+N]`, where prefix is `r` or the name
of a spec in tracey's config, MUST be read as a requirement, of version N or else 1, with
the paragraph after it as its text. One with a prefix other than `r` MUST be known as
`prefix:id`, and written without the prefix, in a file of the same spec, MUST resolve to
it.

r[spec.traces+2]
A comment containing `prefix[impl id]` or `prefix[verify id]`, with or without `+N` after
the ID, MUST be read as a trace of that requirement, of version N or else 1, on the
smallest symbol around it, or the symbol it's directly above.

r[prd.requirements]
A requirement marker on a line of its own in a PRD MUST be read as a requirement the PRD
proposes, with the paragraph after it as its text, and one followed by the word `removed`,
`r[id+N] removed`, as a requirement it removes. Neither MUST be read as part of the spec:
not by the spec view, the glossary, the traces or the margin of another codewalk.

r[prd.compare]
Each requirement a PRD proposes MUST be shown against the spec as it stands: as new if the
spec has no requirement with its ID; as changed, with the spec's text against its own, if
its version is greater than the spec's; as removed, with the spec's text, if it's written
`removed`; and as quoted if its version and its text are the spec's. One whose version
isn't greater than the spec's and whose text differs from it, or that removes a
requirement the spec doesn't have, MUST be reported as an error.

r[prd.terms]
A term or fact defined in a PRD MUST be read as a definition the PRD proposes: shown as new,
or against the spec's definition of the same ID as changed, and not as part of the spec.

r[term.errors+2]
A term or fact defined more than once in the spec, or cited and defined neither in the
spec nor in the PRD citing it, MUST be reported as an error. A PRD's definition of one the
spec defines isn't a second definition.

r[prd.check]
`codewalk check` MUST check each PRD's requirements and definitions, reporting the errors
`prd.compare` and `term.errors` describe with their file and line, and exiting non-zero on
one, as it does for a broken reference.

### Its code

r[proposal.change]
A `walk proposed change` block MUST be read as a change proposed to the symbol it names,
showing the difference from the symbol's code as it is to the draft, so what the change
adds shows as added and what it takes out as removed, and counted as proposed until it's
settled; settling it MUST turn it into a `walk settled` block, keeping the draft. A
change to a name that doesn't resolve MUST be reported as broken.

### Starting one

r[prd.start]
The index MUST offer to start a PRD from a title and what the person wants: it MUST write
the template at `docs/prd/` and the title's slug, with what they want as a `[!request]`
signed as them at the top, and open it, refusing if that file exists. It MUST NOT create
or change a branch or a worktree.

## The code

The shape of the change, in the order of the spec: the data model in full, and the code
that implements each requirement, in full where it's intricate and by its signature where
it's routine. Changes to code that exists are in `walk proposed change` blocks, which
codewalk can't read yet (`proposal.change` is part of this): for now each shows as written,
compared the way a written proposal is, from the draft to the code, so what the change
adds shows as removed. Once `proposal.change` is done it's shown from the code to the
draft, so the additions show as added.

### The data model

Each change to a class that exists is proposed as the whole class, so it's shown where it
is, linked to its file, with the draft against it: the new fields are the added lines.

A requirement carries its version, and one read from a PRD can be a removal:

```walk settled python
Requirement
class Requirement(BaseModel):
    id: str
    file: str
    line: int
    text: str
    # From `r[id+N]`; 1 without a suffix
    version: int = 1
    # Only in a PRD: `r[id+N] removed`, a requirement it takes out of the spec
    removed: bool = False
```

A trace carries the version it names:

```walk settled python
Symbol
class Symbol(BaseModel):
    """One thing a walkthrough can point at."""

    qualified: str
    kind: str
    file: str
    # 1-based, inclusive. `start` takes in its doc comments, attributes and markers
    start: int
    line: int
    end: int
    signature: str
    doc: str
    # Requirement markers on it, `impl` or `verify`, with their IDs and the versions they
    # name, 1 without a suffix
    markers: list[tuple[str, str, int]] = []
    # The rest of its documentation after the summary: for Python, a NumPy-style
    # docstring's extended summary and sections (Parameters, Returns, …)
    details: str = ""
    # What `sig` shows, as runs of lines (1-based, inclusive), if more than its doc
    # comments and first line: for Python, a def's header and docstring; a class's, with
    # its fields and its `__init__`'s header and docstring
    outline: list[tuple[int, int]] = []

    @property
    def name(self) -> str:
        return self.qualified.rsplit("::", 1)[-1]

    @property
    def segments(self) -> list[str]:
        return self.qualified.split("::")

    def text(self, files: SourceFiles) -> str:
        return "\n".join(files.lines(self.file)[self.start - 1 : self.end])

    def digest(self, files: SourceFiles) -> str:
        return hashlib.sha256(self.text(files).encode()).hexdigest()[:12]
```

A PRD has a stage. The stages are a type of their own, in `codewalk/walk/doc.py` beside
[[FrontMatter]], which reads it:

```walk settled python
doc::Stage
# The stages a PRD goes through, in order
Stage = Literal["problem", "prose", "spec", "code", "work"]
```

```walk settled python
FrontMatter
class FrontMatter(BaseModel):
    """What a walkthrough says about itself, in YAML at its top.

    All optional; anything else there is left alone, since other tools keep their own keys
    in front matter.
    """

    model_config = ConfigDict(extra="allow")

    # Shown in place of the first heading
    title: str | None = None
    # A sentence or two, for the list of walkthroughs
    summary: str | None = None
    tags: list[str] = []
    # Other walkthroughs to read with this one, as paths from this file. Linking to one
    # in the text relates them too
    related: list[str] = []
    # What kind of walkthrough: "prd" for one that proposes a change to be made
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
```

The index's summary of a walkthrough, and `codewalk context`'s, carry it:

```walk settled python
Summary
class Summary(BaseModel):
    """One walkthrough, as the index shows it."""

    rel: str
    # From its front matter: where it goes in its folder
    weight: int | None = None
    title: str
    summary: str | None
    tags: list[str]
    # Its folder, which is how the index groups walkthroughs
    folder: str
    # Other walkthroughs it links to, and that link to it, as paths from the root
    links_to: list[str]
    linked_from: list[str] = []
    references: int
    embedded: int
    reviewed: int
    broken: int
    changed: int
    # "prd", say, from its front matter
    kind: str | None = None
    # For a PRD, its stage, from its front matter
    stage: Stage | None = None
    # Its proposals: not written yet, written, settled
    proposed: int = 0
    written: int = 0
    settled: int = 0

    @property
    def plan(self) -> int:
        return self.proposed + self.written + self.settled

    @property
    def plan_status(self) -> str:
        if not self.plan:
            return ""
        return "proposed" if self.proposed == self.plan else "done" if self.settled == self.plan else "in progress"

    @property
    def reviewed_pct(self) -> int:
        return int(100 * self.reviewed / self.embedded) if self.embedded else 100
```

```walk settled python
Brief
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
        return not (self.requests or self.questions or self.proposed or self.written or self.changed or self.broken)
```

What a PRD proposes for the spec, each requirement, term or fact against the spec as it
stands, is a new model, in a new module for PRDs, `codewalk/walk/prd.py`, beside the
walkthroughs it reads ([[Walk]]):

```walk settled python
prd::SpecChange
class SpecChange(BaseModel):
    """A requirement, term or fact a PRD proposes, as it stands against the spec."""

    kind: Literal["requirement", "term", "fact"]
    id: str
    # Its line in the PRD
    line: int
    # The version it's written with; 1 for a term or fact
    version: int = 1
    how: Literal["new", "changed", "removed", "quoted", "error"]
    # Its text in the PRD, and the spec's, if the spec has it
    text: str = ""
    was: str | None = None
    # Why it's an error
    error: str | None = None
```

A proposal can be a change to code that exists:

```walk settled python
Ref
class Ref(BaseModel):
    """One reference a walkthrough makes, and what it resolved to."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    target: str
    # "term" is a `t:` or `f:` reference to a term or fact.
    # "embed" is a line of a `walk` block (a symbol, or with `r:`, a requirement);
    # "proposal" a `walk proposed` block
    kind: Literal["embed", "inline", "req", "proposal", "term"]
    # 1-based line in the walkthrough
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
```

### Reading versions

The two patterns take an optional `+N` after the ID, and the requirement line an optional
`removed`, which only a PRD's reading of it accepts:

```walk settled python
requirements::REQ
REQ = re.compile(rf"^([a-z][a-z0-9]*)\[({tracey.ID})(?:\+([1-9][0-9]*))?\](?:[ \t]+(removed))?\s*$")
```

```walk settled python
tracey::MARKER
# A requirement's marker in code: a prefix, then `[impl id]` or `[verify id]`, with the
# version it names after the ID, `+N`, if it isn't 1
MARKER = re.compile(rf"\b([a-z][a-z0-9]*)\[(impl|verify)\s+({ID})(?:\+([1-9][0-9]*))?\]")
```

Reading a file's requirements becomes a function of its text, in
`codewalk/spec/requirements.py` beside [[SpecIndex]], which [[SpecIndex::refresh]] calls
for the spec and a PRD for its own; the terms the same, in `codewalk/spec/terms.py` beside
[[Glossary]], for [[Glossary::refresh]]:

```walk settled python
requirements::parse
# r[impl spec.prefix+2]
def parse(rel: str, text: str, prefixes: set[str], removals: bool = False) -> list[Requirement]:
    """The requirements in one file's text, in order, each with its version.

    Parameters
    ----------
    rel : str
        The file, from the root.
    text : str
        Its Markdown.
    prefixes : set of str
        The prefixes a requirement line can have, from `tracey::prefixes`.
    removals : bool
        Whether to read `r[id+N] removed` as a removal: in a PRD, and nowhere else.

    Returns
    -------
    list of Requirement
    """
```

```walk settled python
terms::parse
# r[impl term.define]
def parse(rel: str, text: str) -> list[Definition]:
    """The terms and facts defined in one file's text, in order."""
```

The index reads each marker's version into [[Symbol::markers]] (`spec.traces+2`); tracey
already says which are stale, so codewalk only carries the version through.

### A PRD's spec

A PRD's own requirements, terms and facts are read from it, and compared with the spec's.
[[Glossary::refresh]] skips a file whose front matter says `kind: prd`, so a PRD's
definitions never join the spec's (`prd.terms`); the spec index never read PRDs anyway.
The comparison is the heart of this, so in full; it goes in `codewalk/walk/prd.py`, with
[[?prd::SpecChange]]:

```walk settled python
prd::spec_changes
# r[impl prd.requirements]
# r[impl prd.compare]
# r[impl prd.terms]
def spec_changes(w: Walk) -> list[SpecChange]:
    """What a PRD proposes for the spec, each against the spec as it stands.

    Parameters
    ----------
    w : Walk
        The PRD.

    Returns
    -------
    list of SpecChange
        In the order they're written in it.
    """
    ctx = w.ctx
    out = []
    for r in requirements.parse(w.rel, w.text, ctx.spec.prefixes, removals=True):
        now = ctx.spec.find(r.id)
        if now is None:
            how, error = ("error", f"removes `{r.id}`, which the spec doesn't have") if r.removed else ("new", None)
        elif r.version <= now.version:
            same = r.version == now.version and r.text == now.text and not r.removed
            how, error = ("quoted", None) if same else ("error", f"changes `{r.id}` without a new version: the spec's is {now.version}")
        else:
            how, error = ("removed" if r.removed else "changed"), None
        was = now.text if now else None
        out.append(SpecChange(kind="requirement", id=r.id, line=r.line, version=r.version, how=how, text=r.text, was=was, error=error))
    for d in terms.parse(w.rel, w.text):
        now = ctx.glossary.get(f"{d.kind[0]}:{d.id}")
        how = "new" if now is None else "quoted" if now.text == d.text else "changed"
        out.append(SpecChange(kind=d.kind, id=d.id, line=d.line, how=how, text=d.text, was=now.text if now else None))
    return sorted(out, key=lambda c: c.line)
```

Its errors, and anything written ahead of its stage, are among the PRD's problems, so
`codewalk check` and the PRD's page both report them. A new method of [[Walk]], which
[[Walk::problems]] calls:

```walk settled python
Walk::prd_problems
# r[impl prd.check]
# r[impl prd.stage-gate]
def prd_problems(self) -> list[Problem]:
    """A PRD's spec checked against the spec, and anything written ahead of its stage."""
    if self.meta.kind != "prd":
        return []
    changes = spec_changes(self)
    out = [Problem(severity="error", line=c.line, message=c.error) for c in changes if c.how == "error"]
    stage = self.meta.stage or "problem"
    ahead = [
        (c.line, "requirement") for c in changes if c.kind == "requirement" and STAGES.index(stage) < STAGES.index("spec")
    ] + [(r.line, "proposal") for r in self.refs if r.kind == "proposal" and STAGES.index(stage) < STAGES.index("code")]
    out += [Problem(severity="warning", line=line, message=f"a {what} at the {stage} stage") for line, what in ahead]
    return out
```

A term cited in a PRD and defined in it isn't undefined (`term.errors+2`): resolving a
`[[t:…]]` looks in the PRD's own definitions after the glossary. The PRD's page shows each
requirement, term and fact where it's written, marked new, changed, removed, quoted or in
error, with the spec's text against it where there is one.

### Stages

The stage is read from the front matter, `STAGES` being the stages in order
(`get_args(Stage)`), and shown on the index, on the PRD's page and in `codewalk context`,
whose Markdown says, for each PRD, what may be written yet (`prd.stage`,
`prd.stage-gate`). The PRD's page has a control to set it, a new method of [[App]], the
server, beside [[App::settle]] and [[App::agree]]:

```walk settled python
App::set_stage
# r[impl prd.stage-set]
def set_stage(self, rel: str, stage: Stage) -> dict:
    """Set a PRD's stage in its front matter, from its page."""
```

### Proposing a change

```walk settled python
Walk::_proposal
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
```

```walk settled python
Walk::progress
# r[impl proposal.progress]
# r[impl proposal.change]
def progress(self) -> Progress:
    """How far the code it proposes has got: proposed, written, settled."""
    proposals = [r for r in self.refs if r.kind == "proposal"]
    return Progress(
        proposed=sum(1 for r in proposals if not r.symbol or r.change),
        written=sum(1 for r in proposals if r.symbol and not r.change),
        settled=sum(1 for r in self.refs if r.settled),
    )
```

A change whose name doesn't resolve is broken, not in hand. The block shows the difference
the other way round from a written proposal: a written proposal is shown from its draft to
the code (what was planned, then what was written), but a change from the code to its
draft (what there is, then what there will be), so [[Renderer::proposal]] swaps the two
for a change. It's offered **Settle** from the start, and [[doc::settle]] turns
`walk proposed change` into `walk settled` as it does `walk proposed`. `codewalk context`
lists a change under "proposed, not written yet" until it's settled.

### Starting one

The template, `codewalk/setup/prd.md`, in full:

````markdown
---
title: "{title}"
summary: ""
kind: prd
stage: problem
tags: []
related: []
---

# {title}

## The problem

<!-- Why we want a change. Name the code it's about as it stands, in `walk` blocks. -->

## What we want

<!-- At the prose stage: what we'll do about it, in words. -->

## The spec

<!-- At the spec stage: the requirements that follow, as they'll read in the spec. A
change to one is written with its version bumped, `r[id+2]`; a removal as
`r[id+2] removed`. -->

## The code

<!-- At the code stage: the data model in full, and the code that implements each
requirement, in full where it's intricate and by its signature where it's routine. -->

## Terms

## Facts

## Questions

## Changelog

What was asked here and how it was settled, newest first.
````

[[cli::new]] writes it, at `stage: problem` (`prd.template`). The index starts one with
the same template, adding what was asked, through a new function in
`codewalk/walk/prd.py`, a new method of [[App]], and a new function in `codewalk/walk/notes.py`
beside [[notes::ask]]:

```walk settled python
prd::start

- 2026-11-07: **note** @claude: As built, every block below is settled: each shows the code as it was written, with the draft kept beside it.
# r[impl prd.start]
def start(ctx: Context, title: str, ask: str) -> str:
    """Start a PRD at `docs/prd/` and the title's slug, with what was asked as a request.

    Parameters
    ----------
    ctx : Context
        The project.
    title : str
        Its title.
    ask : str
        What the person wants, in their own words.

    Returns
    -------
    str
        The PRD's path, from the root.

    Raises
    ------
    FileExistsError
        If there's a PRD there already.
    """
```

```walk settled python
App::start_prd
# r[impl prd.start]
def start_prd(self, title: str, ask: str) -> dict:
    """Start a PRD from the index, and say where to open it."""
```

```walk settled python
notes::request
def request(text: str, author: str | None, body: str) -> str:
    """`text` with a standing request under its first heading, where it's read first."""
```

### Tests

One or more for each requirement, in `tests/test_codewalk.py`:

```walk settled python
test_a_versioned_requirement_and_its_traces_are_read_with_their_versions
# r[verify spec.prefix+2]
# r[verify spec.traces+2]
def test_a_versioned_requirement_and_its_traces_are_read_with_their_versions(repo): ...
```

```walk settled python
test_a_prds_requirements_and_terms_are_its_own_not_the_specs
# r[verify prd.requirements]
# r[verify prd.terms]
def test_a_prds_requirements_and_terms_are_its_own_not_the_specs(repo): ...
```

```walk settled python
test_a_prds_requirements_are_new_changed_removed_quoted_or_in_error_against_the_spec
# r[verify prd.compare]
def test_a_prds_requirements_are_new_changed_removed_quoted_or_in_error_against_the_spec(repo): ...
```

```walk settled python
test_a_term_a_prd_redefines_or_defines_and_cites_is_not_an_error
# r[verify term.errors+2]
def test_a_term_a_prd_redefines_or_defines_and_cites_is_not_an_error(repo): ...
```

```walk settled python
test_check_fails_on_a_prd_that_changes_a_requirement_without_a_new_version
# r[verify prd.check]
def test_check_fails_on_a_prd_that_changes_a_requirement_without_a_new_version(repo): ...
```

```walk settled python
test_a_prds_stage_is_read_from_its_front_matter_and_shown
# r[verify prd.stage]
def test_a_prds_stage_is_read_from_its_front_matter_and_shown(client, repo): ...
```

```walk settled python
test_setting_a_prds_stage_from_its_page_writes_its_front_matter
# r[verify prd.stage-set]
def test_setting_a_prds_stage_from_its_page_writes_its_front_matter(client, repo): ...
```

```walk settled python
test_work_written_ahead_of_a_prds_stage_is_a_warning
# r[verify prd.stage-gate]
def test_work_written_ahead_of_a_prds_stage_is_a_warning(repo): ...
```

```walk settled python
test_a_new_prd_has_a_section_for_each_stage_and_nothing_in_hand
# r[verify prd.template]
def test_a_new_prd_has_a_section_for_each_stage_and_nothing_in_hand(repo): ...
```

```walk settled python
test_a_proposed_change_shows_its_draft_against_the_code_until_settled
# r[verify proposal.change]
def test_a_proposed_change_shows_its_draft_against_the_code_until_settled(repo): ...
```

```walk settled python
test_starting_a_prd_from_the_index_writes_it_with_what_was_asked
# r[verify prd.start]
def test_starting_a_prd_from_the_index_writes_it_with_what_was_asked(client, repo): ...
```

## Terms

t[stage]
Where a PRD is in its lifecycle: the problem, the prose, the spec, the code or the work,
recorded in its front matter as `stage`.

## Facts

f[tracey.versions] documented
A requirement's ID can carry a version, `r[id+2]`; without one it's version 1. When a
requirement's text changes its version is bumped, and code naming an older version,
`r[impl id]`, is stale, and not counted as covered until it's updated and its marker
bumped. (tracey's documentation, on versioning.)

## Questions

## Changelog

What was asked here and how it was settled, newest first.

- 2026-11-07 (the work): The prose and requirements moved into the spec
  ([PRDs](../spec/prds.md), with `spec.prefix+2`, `spec.traces+2` and `term.errors+2` in
  [Specs and terms](../spec/specs.md) and `proposal.change` in
  [the conversation](../spec/conversation.md)); the code and its tests written, and every
  proposal settled, with where the code departs from its outline in a note under
  [The code](#the-code).
- 2026-11-07 (to the work): **question** @claude: Is the outline of the code agreed? →
  @matthew, in conversation: Yes. Set `stage: work`: the prose and requirements moved into
  [the spec](../spec/prds.md), and the code written.
- 2026-11-07 (`--strict`): **question** @claude: Should stage warnings count under
  `codewalk check --strict`? → **answer** @matthew, in conversation: Yes.
- 2026-11-07 (to the code stage): **question** @claude: Is the spec broadly agreed, so this
  PRD can move to `stage: code`? → @matthew, in conversation: Yes. Set `stage: code`, and
  the outline of the code and tests written in [The code](#the-code).
- 2026-11-07 (the stage gate): **question** @claude: Should a requirement or proposal
  written before its stage be a warning from `codewalk check`, an error, or only advice?
  → **answer** @matthew, in conversation: A warning is appropriate. `prd.stage-gate` as
  written.
- 2026-11-07 (removing a requirement): **question** @claude: Should a PRD remove a
  requirement with its version bumped and no text, `r[id+2]`, or with a word,
  `r[id+2] removed`? → **answer** @matthew, in conversation: `r[id+2] removed`, which is
  plainer. Written into the prose, `prd.requirements` and `prd.compare`.
- 2026-11-07 (to the spec stage): **question** @claude: Is this PRD's prose broadly
  agreed, so it can move to `stage: spec`? → @matthew, in conversation: Yes, we can move
  to the spec stage. Set `stage: spec`, the requirements written in [The spec](#the-spec),
  and the prose made to cite them.
- 2026-11-07 (how much code): **note** @matthew: Don't be too prescriptive about the code:
  a gnarly piece can be shown whole, and boilerplate by its signature. → Written into
  [Its code, in outline](#its-code-in-outline).
- 2026-11-07 (agreeing the prose): **question** @claude: Is the prose agreed, so this PRD
  moves to the spec stage? → **answer** @matthew: Prose should be broadly agreed before
  the spec stage proper, but flexibly: terms and facts can be defined at the prose stage.
  Written into [In stages](#in-stages).
- 2026-11-07: Tidied into a PRD to agree: the lifecycle folded into
  [In stages](#in-stages), the findings from writing it by hand folded into
  [the problem](#the-problem), and the settled threads below compacted into this
  changelog. Set to `stage: prose`.
- 2026-11-07 (worktrees): **question** @claude: One PRD per checkout, or a git worktree
  each? → **decision** @matthew: PRDs are orthogonal to worktrees, and the PRD process
  neither creates nor manages worktrees. (This replaces an earlier decision that each PRD
  should get a worktree.)
- 2026-11-07 (where it's written): **note** @matthew: Started, written and worked wherever
  the user wants: in the browser, or entirely in an IDE, without codewalk running.
- 2026-11-07 (stages): **question** @claude: How does a PRD say which stage it's in? →
  **answer** @matthew: In its front matter; the stage gates later stages' actions, not
  earlier stages'.
- 2026-11-07 (changing existing code): **question** @claude: Should a proposal for a name
  that exists show its draft against the code, and stay proposed until settled? →
  **answer** @matthew: Yes, marked as `walk proposed change`.
- 2026-11-07 (tests): **question** @claude: Should `sources` include `tests/`, so proposed
  tests can settle? → **answer** @matthew: Yes, by default for Python projects.
  `codewalk init` already did; codewalk's own config now does (e387266).
- 2026-11-07 (after merging): **question** @claude: Once a PRD's branch is merged, should
  it record the commit its spec changes were compared against? Withdrawn: it only mattered
  while a PRD changed the spec on a branch.
- 2026-11-07 (telling the agent): **question** @claude: Should `codewalk context --wait`
  return when a person answers, so an agent can wait for them? → **answer** @matthew:
  Keep it simple, and iterate as we need.
- 2026-11-07 (a server per worktree): **question** @claude: One server per worktree, on
  its own port? → **answer** @matthew: codewalk is for local use, much like a live pull
  request: the server on your machine and the agent in the same folder. Don't solve
  remote use.
- 2026-11-07 (where a PRD's spec goes): **question** @claude: A branch with the spec edited
  in place, or a folder of drafts? → **note** @matthew: Neither: a PRD should read on its
  own, so nothing outside it changes while it's proposed, and its requirements are
  compared with the spec as it stands, using tracey's versioning.
- 2026-11-07 (code too soon): **note** @matthew: This PRD jumped the gun: prose first, then
  the spec, then code in outline, as in a lifecycle of five stages. → Set back to the
  prose stage: the spec written in place in `docs/spec/` taken out and what it changed
  there put back, and the drafted spec, code and tests taken out of the PRD (they're at
  711c4b7).
- 2026-11-07 (`[!note]` not shown): **note** @matthew: A `[!note]` typed in the editor
  didn't show when rendered. → Fixed: `note` and `request` had become terms, and linking
  the word broke the marker (e252a17).
- 2026-11-07: **note** @claude: The first PRD, written mostly by hand, to find out how writing one should go. → **note** @matthew: The entire process should run through the UI, in concert with an agent like Claude running in its own application alongside.
