"""`codewalk`: check, serve, export and review walkthroughs.

It works from the repository the current folder is in. Where it looks is set in
`codewalk.toml` at the repository's root, if there is one.
"""

from __future__ import annotations

import sys

import rich_click as click
from rich.console import Console
from rich.table import Table

from .config import Config, repo_root
from .doc import Context, Walk

console = Console(highlight=False)


def context() -> Context:
    root = repo_root()
    return Context(root, Config.load(root))


@click.group(help=__doc__)
def main() -> None:
    pass


@main.command()
@click.argument("walkthroughs", nargs=-1)
@click.option("--strict", is_flag=True, help="Fail on code changed since it was reviewed, too.")
def check(walkthroughs: tuple[str, ...], strict: bool) -> None:
    """Check every reference resolves; exit 1 if one doesn't."""
    ctx = context()
    rels = list(walkthroughs) or ctx.walkthroughs()
    errors = warnings = pending = refs = 0
    for rel in rels:
        w = Walk(ctx, rel)
        refs += len(w.refs)
        for p in w.problems():
            colour = {"error": "red", "warning": "yellow", "pending": "cyan"}[p.severity]
            console.print(f"[bold]{rel}:{p.line}[/]: [{colour}]{p.severity}[/]: {p.message}", markup=True)
            if p.candidates:
                console.print(f"    [dim]did you mean: {', '.join(p.candidates)}[/]")
            errors += p.severity == "error"
            warnings += p.severity == "warning"
            pending += p.severity == "pending"
    status = "[green]ok[/]" if not errors else f"[red]{errors} broken[/]"
    changed = f", [yellow]{warnings} changed since review[/]" if warnings else ""
    in_hand = f", [cyan]{pending} in hand[/] (codewalk context)" if pending else ""
    console.print(f"{len(rels)} walkthroughs, {refs} references: {status}{changed}{in_hand}")
    sys.exit(1 if errors or (strict and warnings) else 0)


@main.command()
@click.option("--port", default=4471, show_default=True, help="Port to listen on, on 127.0.0.1.")
def serve(port: int) -> None:
    """The web view, with editing and live reload."""
    from .server import serve as run

    ctx = context()
    url = f"http://localhost:{port}"
    counts = f"{len(ctx.index.symbols)} symbols, {len(ctx.walkthroughs())} walkthroughs"
    console.print(f"codewalk: [link={url}]{url}[/link]  [dim]({counts})[/]")
    run(ctx, port)


@main.command()
@click.argument("walkthrough")
@click.argument("out")
def export(walkthrough: str, out: str) -> None:
    """Write a walkthrough as plain Markdown, with the code written out and linked."""
    ctx = context()
    (ctx.root / out).write_text(Walk(ctx, walkthrough).export(out))
    console.print(f"wrote {out}")


@main.command()
@click.argument("walkthrough")
def review(walkthrough: str) -> None:
    """Mark every embedded symbol reviewed as it stands."""
    from .server import App

    done = App(context()).review(walkthrough, None)["reviewed"]
    console.print(f"{len(done)} symbols marked reviewed in {walkthrough}")


@main.command()
@click.option("--dry-run", is_flag=True, help="Say what it would do, and do nothing.")
@click.option("--command", "command", default=None, help="How to run codewalk here, for the docs it writes.")
@click.option("--walkthroughs", default="docs/walkthroughs", show_default=True, help="Where new walkthroughs go.")
def init(dry_run: bool, command: str | None, walkthroughs: str) -> None:
    """Set codewalk up here: config, a section in AGENTS.md, and skills for agents."""
    from .setup import init as run

    for line in run(repo_root(), command, walkthroughs, dry_run):
        console.print(line)


@main.command()
@click.argument("path")
@click.option("--title", required=True, help="Its title.")
@click.option("--prd", is_flag=True, help="A PRD: a change proposed in full, to be settled as it's made.")
def new(path: str, title: str, prd: bool) -> None:
    """Start a walkthrough at PATH (from the repository root)."""
    from importlib import resources

    ctx = context()
    target = ctx.root / path
    if target.exists():
        raise click.ClickException(f"{path} exists already")
    author = ctx.config.who(ctx.root) or "you"
    if prd:
        text = (resources.files("codewalk") / "setup" / "prd.md").read_text().replace("{title}", title).replace("{author}", author)
    else:
        text = f"---\nsummary: \ntags: []\n---\n\n# {title}\n\n```walk\n```\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    console.print(f"wrote {path}: open it with `codewalk serve`, at /edit/{path}")


@main.command()
def lsp() -> None:
    """A language server, over stdin and stdout, for editing walkthroughs and specs."""
    from .lsp import main as run

    run()


@main.command(name="context")
@click.argument("walkthroughs", nargs=-1)
@click.option("--json", "as_json", is_flag=True, help="As JSON, not Markdown.")
def context_(walkthroughs: tuple[str, ...], as_json: bool) -> None:
    """What's in hand, for an agent starting a run: open questions, proposals, changes."""
    import json

    from .brief import as_markdown, brief

    ctx = context()
    briefs = [brief(ctx, rel) for rel in (list(walkthroughs) or ctx.walkthroughs())]
    if as_json:
        print(json.dumps([b.model_dump() for b in briefs], indent=2))
    else:
        print(as_markdown(briefs))


@main.command()
@click.argument("query")
@click.option("--limit", default=20, show_default=True)
def find(query: str, limit: int) -> None:
    """Find symbols matching QUERY, with the reference to write."""
    ctx = context()
    table = Table(box=None, show_header=False, pad_edge=False)
    table.add_column(style="bold")
    table.add_column(style="dim")
    table.add_column(style="dim")
    for sym in ctx.index.search(query, limit):
        table.add_row(ctx.index.shortest_unique(sym), sym.kind, f"{sym.file}:{sym.line}")
    console.print(table)


if __name__ == "__main__":
    main()
