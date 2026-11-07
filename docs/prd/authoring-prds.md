---
title: "Authoring PRDs"
summary: "A PRD is started in the browser and written there with an agent alongside, on a branch of its own, with the spec changed where it lives and what it changes shown against its base."
kind: prd
base: main
tags: [prd, spec]
related: ["../walkthrough.md"]
---

# Authoring PRDs

> [!note] @claude: The first PRD, written mostly by hand, to find out how writing one
> should go. It's a PRD about PRDs: the process it settles on is the one it was written
> with, and what was awkward along the way is at the end, under
> [what writing it showed](#what-writing-it-showed).
>
> [!note] @matthew: The entire process should run through the UI, in concert with an
> agent like Claude running in its own application alongside. So we should be able to
> start a PRD from the UI.

## The problem

codewalk can already start a PRD. `codewalk new PATH --title T --prd` writes a walkthrough
from a template, with `kind: prd` in its front matter, and its progress is counted from
its proposals:

```walk
cli::new
FrontMatter::kind
Walk::progress
```

That's for someone at a terminal. The process is meant to run in the browser, with a
person reading, asking and deciding there and an agent beside it in its own application
doing the writing, and the browser can read, answer, settle, review and reconcile, but it
can't start a PRD: the index has no way to.

Nor does codewalk say where the PRD's change to the spec goes. Few changes are
standalone: most change what the spec already says as much as they add to it. The
template's "What the spec says" section has the prose drafted inside the PRD, and the
requirements cited as `[[r:new.id]]` until someone writes them into the spec, so until
then the spec and the PRD say different things, and the change to existing prose is
described rather than made.

There are two ways to fix that:

1. **A folder of drafts.** The PRD gets a folder of its own, with copies of the spec files
   it changes, edited there until it's agreed, then copied over. It's easy to start, but
   everything it touches is defined twice while it's open (a term defined twice is an
   error, and of two requirements with one ID codewalk silently keeps the last), the
   copies drift from the spec as other work lands, and moving them over is a merge done
   by hand.
2. **A branch.** The PRD is written on a branch, and the spec on that branch is changed
   where it lives. Nothing is defined twice, the spec view and tracey work on it
   unchanged, and git does the merging. What's lost is a view of *what the PRD changes*:
   on the branch, the spec just is what it will be.

This PRD takes the second, and adds the missing view, and starts the branch for you when
you start the PRD in the browser.

> [!question] @claude: The branch is what I've written the spec for, in
> [the PRDs spec](../spec/prds.md). The case for the folder is that it's cheaper to
> start: you can sketch a PRD without a branch. But the PRD's walkthrough alone, citing
> requirements that don't exist yet as `[[r:id]]`, already covers sketching, and the
> spec view shows such citations as missing rather than failing. Does the branch match
> how you want to work, given how you use branches and review?

## The outcome

- A person starts a PRD from the index, with **New PRD**: a title and what they want.
  codewalk starts its branch, writes the walkthrough with what they want as a standing
  request, and opens it; the agent, asked to carry on, finds the request in
  `codewalk context` and writes the first draft, which appears on the page as it's saved.
- [[t:prd]]s are written on a branch, with the spec changed in place: the
  [process](../spec/prds.md#writing-one) is in the spec, so an agent asked to write one
  follows it.
- A PRD names its [[t:base]], and `codewalk changes docs/prd/x.md` lists what it changes in
  the spec against where its branch left the base: files added, removed or changed, and in
  each whether the prose changed, and each requirement, term and fact added, changed or
  removed.
- A PRD's page shows the same, linked to the spec, so it's read beside the proposals.

## What the spec says

The spec for this is a new file, [docs/spec/prds.md](../spec/prds.md), written first,
prose and then requirements, on this branch. It also changes an existing file, as most
PRDs will: the definition of a PRD moves out of
[the conversation](../spec/conversation.md) into the new file, and the sentence there
about a PRD's progress is reworded around the walkthrough rather than the PRD. The
requirements:

- [[r:prd.new]]: starting one, from the index or the command line, writes the template,
  with its base and no placeholders.
- [[r:prd.branch]]: starting one from the index starts its branch, and won't with
  uncommitted work in the way.
- [[r:prd.ask]]: what the person asked for goes in as a standing request.
- [[r:prd.base]]: changes are worked out against the merge base.
- [[r:prd.changes]]: `codewalk changes` lists them.
- [[r:prd.view]]: and the PRD's page shows them.

And one change to an existing requirement: [[r:serve.local]] said the server writes only
walkthroughs and the review file. It now says it writes specs too (it always has, from the
editor), and that the only change it makes to git is starting a PRD's branch.

## The code

### Starting one

One function starts a PRD, for the index and for `codewalk new --prd` alike. From the
browser it's given what the person wants, and then it also starts the branch, refusing
rather than carrying uncommitted work onto it:

```walk proposed python
prd::start
# r[impl prd.new]
# r[impl prd.branch]
# r[impl prd.ask]
def start(ctx: Context, title: str, ask: str | None = None, base: str | None = None, path: str | None = None) -> str:
    """Start a PRD: its walkthrough and, from the browser, its branch and what was asked.

    Parameters
    ----------
    ctx : Context
        The project.
    title : str
        Its title.
    ask : str or None
        What the person wants, in their words. Given from the browser, which starts the
        PRD's branch too; None from the command line, which leaves the branch to whoever
        ran it.
    base : str or None
        The branch it will be merged into; else the repository's default branch.
    path : str or None
        Where to write it, from the root; else `docs/prd/` and the title's slug.

    Returns
    -------
    str
        The walkthrough's path, from the root.

    Raises
    ------
    FileExistsError
        If the walkthrough, or the branch it would start, exists already.
    RuntimeError
        If it would start a branch and the working tree has uncommitted changes.
    """
    base = base or default_branch(ctx.root)
    rel = path or f"docs/prd/{slug(title)}.md"
    if (ctx.root / rel).exists():
        raise FileExistsError(rel)
    author = ctx.config.who(ctx.root) or "you"
    if ask is not None:
        branch = f"prd/{slug(title)}"
        if git(ctx.root, "status", "--porcelain"):
            raise RuntimeError("there are uncommitted changes: commit or stash them, then start it")
        if git(ctx.root, "branch", "--list", branch):
            raise FileExistsError(f"the branch {branch}")
        git(ctx.root, "switch", "--create", branch, base, check=True)
    text = TEMPLATE.read_text()
    for key, value in {"title": title, "author": author, "base": base}.items():
        text = text.replace("{" + key + "}", value)
    if ask:
        text = notes.request(text, author, ask)
    (ctx.root / rel).parent.mkdir(parents=True, exist_ok=True)
    (ctx.root / rel).write_text(text)
    return rel
```

[[cli::new]] calls it with `--base` and its path; the browser calls it through the
server, which reloads its view of the project, since the branch it's on just changed:

```walk proposed python
App::start_prd
# r[impl serve.local]
def start_prd(self, title: str, ask: str, base: str | None = None) -> dict:
    """Start a PRD from the index, and say where to open it."""
    rel = prd.start(self.ctx, title, ask=ask, base=base)
    self.ctx.refresh()
    return {"started": rel, "href": f"/walk/{rel}"}
```

The route, `POST /api/prd`, answers a refusal with 409 and its reason, which the form shows
where you typed. The form is on the index, beside its heading: a title, what you want
(several lines), and the base, filled in with the default branch. Starting it opens the
PRD, where the request sits at the top until the agent's first draft arrives around it.

Three small pieces:

```walk proposed python
prd::slug
def slug(title: str) -> str:
    """A title as a file or branch name: lower case, words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
```

```walk proposed python
prd::git
def git(root: Path, *args: str, check: bool = False) -> str:
    """What a git command prints, run at `root`."""
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=root, check=check).stdout.strip()
```

```walk proposed python
notes::request
def request(text: str, author: str | None, body: str) -> str:
    """`text` with a standing request under its first heading, where it's read first."""
    lines = text.split("\n")
    at = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
    return "\n".join(lines[:at] + ["", *_quote("request", author, body)] + lines[at:])
```

The template loses its sample `walk proposed` block and sample question, which counted as
work in hand from the moment it was written, for HTML comments saying what goes in each
section, and gains `base: "{base}"` in its front matter, which [[FrontMatter]] reads:

```walk proposed python
FrontMatter::base
    # For a PRD: the branch it will be merged into. What it changes in the spec is worked
    # out against where its branch left this one
    base: str | None = None
```

```walk proposed python
config::default_branch
def default_branch(root: Path) -> str:
    """The branch `origin/HEAD` points at, else `main`."""
    out = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], capture_output=True, text=True, cwd=root)
    return out.stdout.strip().removeprefix("origin/") or "main"
```

### Reading the spec as it was

The requirements and terms are read from files, in two loops that each open a file and
parse it in place:

```walk
SpecIndex::refresh
Glossary::refresh sig
```

To read a spec file as it was at another commit, the parsing has to work on text. Each
loop's body becomes a function of a file's path and its text, which `refresh` calls, and
so can the comparison:

```walk proposed python
requirements::parse
# r[impl spec.prefix]
def parse(rel: str, text: str, prefixes: set[str]) -> list[Requirement]:
    """The requirements in one spec file's text, in order.

    Parameters
    ----------
    rel : str
        The file, from the root.
    text : str
        Its Markdown.
    prefixes : set of str
        The prefixes a requirement line can have, from `tracey::prefixes`.

    Returns
    -------
    list of Requirement
        Each with the paragraph after its marker as its text.
    """
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = REQ.match(line)
        if not m or m.group(1) not in prefixes:
            continue
        body = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip() or REQ.match(nxt):
                break
            body.append(nxt.strip())
        out.append(Requirement(id=tracey.key(m.group(1), m.group(2)), file=rel, line=i + 1, text=" ".join(body)))
    return out
```

```walk proposed python
terms::parse
# r[impl term.define]
def parse(rel: str, text: str) -> list[Definition]:
    """The terms and facts defined in one file's text, in order."""
    out = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not (m := DEF_LINE.match(line)):
            continue
        body = []
        for nxt in lines[i + 1 :]:
            if not nxt.strip() or DEF_LINE.match(nxt) or nxt.startswith("r["):
                break
            body.append(nxt.strip())
        kind = "term" if m.group(1) == "t" else "fact"
        status = (m.group(3) or "assumed") if kind == "fact" else None
        out.append(Definition(kind=kind, id=m.group(2), status=status, file=rel, line=i + 1, text=" ".join(body)))
    return out
```

### Where the branch left its base

What's compared against isn't the base as it is now, which moves as other work is merged,
but the commit where this branch left it, so a PRD shows only its own changes:

```walk proposed python
changes::merge_base
# r[impl prd.base]
def merge_base(root: Path, base: str) -> str | None:
    """The commit where the current branch left `base`; None if git can't say."""
    out = subprocess.run(["git", "merge-base", base, "HEAD"], capture_output=True, text=True, cwd=root)
    return out.stdout.strip() or None
```

### What changed

For each spec file, as it is in the working tree and as it was at the merge base, the
requirements, terms and facts are compared by ID, and the prose, everything that isn't a
definition, by its paragraphs with their whitespace evened out, so rewrapping a paragraph
isn't a change:

```walk proposed python
changes::SpecChange
class SpecChange(BaseModel):
    """A requirement, term or fact a PRD adds, changes or removes."""

    kind: Literal["requirement", "term", "fact"]
    id: str
    how: Literal["added", "changed", "removed"]
    before: str | None = None
    after: str | None = None
```

```walk proposed python
changes::FileChanges
class FileChanges(BaseModel):
    """One spec file a PRD adds, removes or changes, and what in it."""

    rel: str
    how: Literal["added", "changed", "removed"]
    # Whether anything but the definitions changed
    prose: bool
    changes: list[SpecChange]
```

```walk proposed python
changes::spec_changes
# r[impl prd.changes]
def spec_changes(ctx: Context, base: str) -> list[FileChanges]:
    """Each spec file that differs from where the current branch left `base`, and how.

    Parameters
    ----------
    ctx : Context
        The project, as it is in the working tree.
    base : str
        The branch the changes are to be merged into.

    Returns
    -------
    list of FileChanges
        By path; none if git can't find where the branch left `base`.
    """
    rev = merge_base(ctx.root, base)
    if rev is None:
        return []
    now = set(ctx.spec_paths())
    out = []
    for rel in sorted(now | removed(ctx.root, rev, ctx.spec.globs)):
        before = at(ctx.root, rev, rel)
        after = (ctx.root / rel).read_text() if rel in now else None
        if before == after:
            continue
        old, new = defined(rel, before or "", ctx.spec.prefixes), defined(rel, after or "", ctx.spec.prefixes)
        changes = [
            SpecChange(
                kind=kind,
                id=did,
                how="added" if (kind, did) not in old else "removed" if (kind, did) not in new else "changed",
                before=old.get((kind, did)),
                after=new.get((kind, did)),
            )
            for kind, did in sorted(old.keys() | new.keys())
            if old.get((kind, did)) != new.get((kind, did))
        ]
        how = "added" if before is None else "removed" if after is None else "changed"
        out.append(FileChanges(rel=rel, how=how, prose=prose_of(before or "") != prose_of(after or ""), changes=changes))
    return out
```

With three helpers: a file's text at a commit, the spec files deleted since it (git's
pathspecs take the spec's globs as they are), and what a text defines:

```walk proposed python
changes::at
def at(root: Path, rev: str, rel: str) -> str | None:
    """`rel` as it was at `rev`; None if it wasn't there."""
    out = subprocess.run(["git", "show", f"{rev}:{rel}"], capture_output=True, text=True, cwd=root)
    return out.stdout if out.returncode == 0 else None
```

```walk proposed python
changes::removed
def removed(root: Path, rev: str, globs: list[str]) -> set[str]:
    """The spec files there at `rev` that the working tree doesn't have."""
    spec = [f":(glob){g}" for g in globs]
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=D", rev, "--", *spec], capture_output=True, text=True, cwd=root)
    return set(out.stdout.split())
```

```walk proposed python
changes::defined
def defined(rel: str, text: str, prefixes: set[str]) -> dict[tuple[str, str], str]:
    """Each requirement, term and fact in `text`, by kind and ID, to its text."""
    out = {("requirement", r.id): r.text for r in requirements.parse(rel, text, prefixes)}
    out |= {(d.kind, d.id): d.text for d in terms.parse(rel, text)}
    return out
```

```walk proposed python
changes::prose_of
def prose_of(text: str) -> list[str]:
    """A spec file's paragraphs that aren't definitions, with their whitespace evened out."""
    paras = (" ".join(p.split()) for p in re.split(r"\n\s*\n", text))
    return [p for p in paras if p and not MARKER.match(p)]
```

`MARKER` is the start of any definition, `r[id]`, `t[id]` or `f[id]` or a spec's own
prefix: the same pattern as `REQ_LINE`, which the spec view uses to tell prose from
requirements, so it moves to `tracey` and both use it.

### Showing it

On the command line, for an agent or before a review:

```walk proposed python
cli::changes
@main.command()
@click.argument("prd")
def changes(prd: str) -> None:
    """What a PRD changes in the spec, against where its branch left its base."""
    from codewalk.spec.changes import spec_changes

    ctx = context()
    w = Walk(ctx, prd)
    if w.meta.kind != "prd" or not w.meta.base:
        raise click.ClickException(f"{prd} isn't a PRD with a base")
    for f in spec_changes(ctx, w.meta.base):
        console.print(f"[bold]{f.rel}[/] {f.how}" + (", prose changed" if f.prose else ""))
        for c in f.changes:
            console.print(f"  {c.how:8} {c.kind} {c.id}")
```

And on the PRD's page, in the contents column under its headings, the way a spec's
uncited requirements are listed there, so the changes are beside the proposals that make
them. [[App::walk_page]] passes them to the template:

```walk proposed python
App::prd_changes
# r[impl prd.view]
def prd_changes(self, w: Walk) -> list[dict]:
    """A PRD's changes to the spec, for its page, each linked to where it is in the spec."""
    if w.meta.kind != "prd" or not w.meta.base:
        return []
    out = []
    for f in spec_changes(self.ctx, w.meta.base):
        rows = [
            {**c.model_dump(), "href": None if c.how == "removed" else f"/spec/{f.rel}#{c.kind[0]}-{_slug(c.id)}"}
            for c in f.changes
        ]
        out.append({**f.model_dump(exclude={"changes"}), "changes": rows})
    return out
```

## Testing

Each test starts a git repository in the test's folder, commits the spec as the base, and
changes it on a branch:

```walk proposed python
test_a_prds_spec_changes_are_against_where_its_branch_left_its_base
# r[verify prd.base]
# r[verify prd.changes]
def test_a_prds_spec_changes_are_against_where_its_branch_left_its_base(repo):
    from codewalk.spec.changes import spec_changes

    git(repo, "init", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "the base")
    git(repo, "checkout", "-b", "prd")
    spec = repo / "docs/spec/spec.md"
    spec.write_text(SPEC.replace("told what to do.", "told what to do, once.") + "\nr[battery.stop]\nA battery can be stopped.\n")
    (repo / "docs/spec/new.md").write_text("# New\n\nt[site]\nA place with a meter.\n")
    # Work merged into the base since doesn't count
    git(repo, "checkout", "main")
    (repo / "docs/spec/later.md").write_text("# Later\n\nr[later.thing]\nLanded on main.\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "elsewhere")
    git(repo, "checkout", "prd")

    added, changed = spec_changes(ctx(repo), "main")
    assert (added.rel, added.how, [c.id for c in added.changes]) == ("docs/spec/new.md", "added", ["site"])
    assert (changed.how, changed.prose) == ("changed", False)
    assert [(c.id, c.how) for c in changed.changes] == [("battery.command", "changed"), ("battery.stop", "added")]
```

```walk proposed python
test_starting_a_prd_from_the_index_starts_its_branch_with_what_was_asked
# r[verify prd.branch]
# r[verify prd.ask]
def test_starting_a_prd_from_the_index_starts_its_branch_with_what_was_asked(repo, client):
    git(repo, "init", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "the base")
    r = client.post("/api/prd", json={"title": "Stop a battery", "ask": "Batteries need stopping."})
    assert r.json() == {"started": "docs/prd/stop-a-battery.md", "href": "/walk/docs/prd/stop-a-battery.md"}
    assert git(repo, "branch", "--show-current") == "prd/stop-a-battery"
    w = Walk(ctx(repo), "docs/prd/stop-a-battery.md")
    assert [(t.notes[0].kind, t.open) for t in w.threads] == [("request", True)]
    assert w.progress().proposed == 0
    # Again, with the branch there and work uncommitted: refused, and nothing written
    (repo / "docs/spec/spec.md").write_text(SPEC + "\nMore.\n")
    assert client.post("/api/prd", json={"title": "Other", "ask": "Something."}).status_code == 409
    assert not (repo / "docs/prd/other.md").exists() and git(repo, "branch", "--show-current") == "prd/stop-a-battery"
```

```walk proposed python
test_a_prd_names_its_base
# r[verify prd.new]
def test_a_prd_names_its_base(repo, monkeypatch):
    from click.testing import CliRunner

    from codewalk.cli import main

    monkeypatch.chdir(repo)
    git(repo, "init", "-b", "main")
    CliRunner().invoke(main, ["new", "docs/prd/x.md", "--title", "X", "--prd", "--base", "trunk"])
    meta = Walk(ctx(repo), "docs/prd/x.md").meta
    assert (meta.kind, meta.base) == ("prd", "trunk")
```

```walk proposed python
test_a_prds_page_shows_its_spec_changes
# r[verify prd.view]
def test_a_prds_page_shows_its_spec_changes(repo):
    ...  # as the first test, then the page links `battery.stop` to /spec/docs/spec/spec.md#r-battery-stop
```

> [!question] @claude: These won't settle. The tests aren't indexed (`sources` is
> `codewalk/**/*.py`), so a proposed test's name never resolves, and the PRD can't reach
> all settled. Should `sources` include `tests/**/*.py`? Test names are long and unique,
> so they won't make other names ambiguous, but every walkthrough would then be able to
> show tests, which may be what we want anyway.

## Questions

> [!question] @claude: Starting a PRD switches the checkout to its branch, and the agent
> works in the same checkout, so it's then on the PRD's branch too, which is what we want.
> But it means one PRD at a time per checkout, and starting one is refused while anything
> is uncommitted, including the agent's work on another. Is one at a time right for now,
> or should each PRD get a `git worktree` of its own, with `codewalk serve` able to show
> several?

> [!question] @claude: Nothing tells the agent the person has done something: after
> answering in the browser, they say "carry on" in the agent's application, and the agent
> reads `codewalk context`. That's simple and keeps the person in charge of when the agent
> works. Should codewalk do more, say `codewalk context --wait`, which returns once a
> person's note changes what's in hand, so an agent can sit waiting for the next answer?

> [!question] @claude: Once the branch is merged, its base has its changes, so the merge
> base is the branch's own last commit and the list is empty. That's right while the PRD
> is open, but afterwards it's the record of what it changed. Should merging (or settling
> the last proposal) write the merge base into the front matter as `base_commit`, so the
> list keeps working against that commit, or is the git history enough by then?

> [!question] @claude: Some of this changes code that exists: [[cli::new]] gains
> `--base`, [[SpecIndex::refresh]] and [[Glossary::refresh]] call the new `parse`
> functions, and the template gains `base`. A `walk proposed` block can't say that: its
> name resolves at once, so it reads as written, not proposed. I've described those
> changes in prose instead. Should a proposal for a name that exists show its draft as a
> diff against the code as it is, and count as proposed until the code matches the draft
> or it's settled?

## What writing it showed

Writing this by hand, rather than through the skills, turned up where the process and
the tool fall short:

- **The browser can't start one.** Everything else a person does to a PRD (asking,
  answering, settling, reviewing, reconciling) is in the browser already; starting it
  wasn't, which is now [[?prd::start]] and [[?App::start_prd]].
- **The process wasn't written down.** Where a PRD's spec goes was the first thing to
  decide; it's now [in the spec](../spec/prds.md#where-a-prd-lives), and the
  `codewalk-propose` skill and the template should point to it.
- **The template's placeholders count as work.** `codewalk new --prd` writes a sample
  `walk proposed` block (`Type::new_method`, in Rust) and a sample question, and both show
  as in hand straight away, so `codewalk context` reports a fresh PRD as two items behind.
  The samples could be comments, or a language could be taken from `sources`.
- **Changing existing code can't be proposed,** above.
- **Proposed tests can't settle,** above.
- **`codewalk check` doesn't check the spec.** It checks walkthroughs only, so a term
  cited and not defined in a spec file, or defined twice across two, isn't reported by
  `check`, only on the spec's page. A PRD changes the spec more than anything else does,
  so this is where it matters.
- **A question's summary loses its links.** `codewalk context` shows a question about
  `[[cli::new]]` as "code that exists: [] gains", dropping the name it's about.
- **One branch, one PRD.** This one is on a branch that carries other work too (the
  glossary's move into the specs), so its changes against `main` would include that work.
  That's how this one was written, not how it should be: a PRD's branch should be its own.
