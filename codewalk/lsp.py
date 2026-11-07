"""A language server, so an editor can do what the web view does while you write.

    codewalk lsp

It speaks LSP over stdin and stdout, for Markdown files under the docs and spec folders:

- **Diagnostics**: every problem `codewalk check` finds, as you type, including open
  questions and proposals in hand, as hints.
- **Completion**: after `[[`, in a `walk` block, and after `[[r:`, `[[t:` or `[[f:`.
- **Hover**: a symbol's signature and docs; a requirement's text and the code that names
  it; a term's or fact's definition.
- **Go to definition**: the symbol, requirement, term or fact.
- **Quick fixes**: replace an ambiguous or unknown name with one of the candidates.

It needs no grammar of its own: it parses with the same Markdown parser as everything
else, which knows each reference's line, and finds where on the line it is by the same
patterns. See `SYNTAX.md` for the syntax it understands.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from .config import Config, repo_root
from .doc import WIKI, Context, Walk, embed_line
from .server import App

# A reference on a line, and where: (target, start column, end column)
Span = tuple[str, int, int]

LINK = re.compile(r"\]\((walk|req|term|fact):([^)\s]+)\)")
TICKED = re.compile(r"`([a-z0-9][a-z0-9.\-]*\.[a-z0-9.\-]+)`")
SCHEMES = {"walk": "", "req": "r:", "term": "t:", "fact": "f:"}


def in_walk_block(lines: list[str], row: int) -> bool:
    """Whether line `row` (0-based) is inside a ```walk block (not a proposal's draft).

    Parameters
    ----------
    lines : list of str
        The file's lines.
    row : int
        The line, 0-based.

    Returns
    -------
    bool
        True inside a plain ```walk block; False outside one, or in a `walk proposed` draft.
    """
    inside = False
    for line in lines[:row]:
        s = line.strip()
        if s.startswith("```"):
            inside = (not inside) and s == "```walk"
    return inside


def references_on(line: str, walk_block: bool) -> list[Span]:
    """Every reference on a line, with its columns.

    Parameters
    ----------
    line : str
        The line.
    walk_block : bool
        Whether it's inside a ```walk block, where a reference is the whole line's target.

    Returns
    -------
    list of Span
        Each reference's target, start column and end column.
    """
    out: list[Span] = []
    if walk_block:
        if parsed := embed_line(line):
            target = parsed[0]
            start = line.index(target)
            out.append((target, start, start + len(target)))
        return out
    for m in WIKI.finditer(line):
        target = m.group(1).strip().lstrip("?")
        out.append((target, m.start(), m.end()))
    for m in LINK.finditer(line):
        out.append((SCHEMES[m.group(1)] + m.group(2), m.start(), m.end()))
    for m in TICKED.finditer(line):
        out.append(("r:" + m.group(1), m.start(), m.end()))
    return out


def reference_at(lines: list[str], row: int, col: int) -> Span | None:
    for span in references_on(lines[row], in_walk_block(lines, row)):
        if span[1] <= col <= span[2]:
            return span
    return None


def completion_query(lines: list[str], row: int, col: int) -> tuple[str, int] | None:
    """What's being typed at the cursor, if it's a name.

    Parameters
    ----------
    lines : list of str
        The file's lines.
    row, col : int
        The cursor, 0-based.

    Returns
    -------
    tuple of (str, int) or None
        The query and the column it starts at; None if the cursor isn't on a name.
    """
    before = lines[row][:col]
    opened = before.rfind("[[")
    if opened >= 0 and "]]" not in before[opened:] and "|" not in before[opened:]:
        return before[opened + 2 :].lstrip("?"), opened + 2 + (1 if before[opened + 2 : opened + 3] == "?" else 0)
    if in_walk_block(lines, row) and re.fullmatch(r"\s*\S*", before):
        word = before.strip()
        return word, col - len(word)
    return None


def uri_path(uri: str) -> Path:
    return Path(unquote(urlparse(uri).path))


class CodewalkServer(LanguageServer):
    """The language server: pygls's, with the project it works on, made when it's first needed."""

    def __init__(self):
        super().__init__("codewalk", "0.1.0")
        self.ctx: Context | None = None
        self.app: App | None = None

    def context(self, uri: str) -> tuple[Context, App, str] | None:
        path = uri_path(uri)
        if self.ctx is None:
            root = repo_root(path.parent)
            self.ctx = Context(root, Config.load(root))
            self.app = App(self.ctx)
        self.ctx.refresh()
        try:
            rel = str(path.relative_to(self.ctx.root))
        except ValueError:
            return None
        return self.ctx, self.app, rel


server = CodewalkServer()


def _walk(ls: CodewalkServer, uri: str) -> tuple[Walk, list[str]] | None:
    found = ls.context(uri)
    if not found:
        return None
    ctx, _, rel = found
    text = ls.workspace.get_text_document(uri).source
    return Walk(ctx, rel, text), text.split("\n")


SEVERITY = {"error": lsp.DiagnosticSeverity.Error, "warning": lsp.DiagnosticSeverity.Warning, "pending": lsp.DiagnosticSeverity.Hint}


def diagnose(ls: CodewalkServer, uri: str) -> None:
    got = _walk(ls, uri)
    if not got:
        return
    w, lines = got
    diagnostics = []
    for p in w.problems():
        row = max(0, p.line - 1)
        line = lines[row] if row < len(lines) else ""
        start, end = 0, len(line)
        if p.ref and p.ref.split(" > ")[0] in line:
            start = line.index(p.ref.split(" > ")[0])
            end = start + len(p.ref.split(" > ")[0])
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(start=lsp.Position(line=row, character=start), end=lsp.Position(line=row, character=end)),
                message=p.message,
                severity=SEVERITY[p.severity],
                source="codewalk",
                data={"candidates": p.candidates, "ref": p.ref},
            )
        )
    ls.text_document_publish_diagnostics(lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics))


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: CodewalkServer, params: lsp.DidOpenTextDocumentParams):
    diagnose(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: CodewalkServer, params: lsp.DidChangeTextDocumentParams):
    diagnose(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: CodewalkServer, params: lsp.DidSaveTextDocumentParams):
    diagnose(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION, lsp.CompletionOptions(trigger_characters=["[", ":"]))
def completion(ls: CodewalkServer, params: lsp.CompletionParams):
    found = ls.context(params.text_document.uri)
    if not found:
        return None
    _, app, _ = found
    lines = ls.workspace.get_text_document(params.text_document.uri).source.split("\n")
    pos = params.position
    q = completion_query(lines, pos.line, pos.character)
    if q is None or (len(q[0]) < 2 and not q[0].endswith(":")):
        return None
    query, start = q
    items = app.symbols(query if query[:2] in ("r:", "t:", "f:") else query.split("::")[-1])
    if "::" in query:
        items = [i for i in items if query.lower() in i["qualified"].lower()]
    edit_range = lsp.Range(start=lsp.Position(line=pos.line, character=start), end=pos)
    return lsp.CompletionList(
        is_incomplete=True,
        items=[
            lsp.CompletionItem(
                label=i["ref"],
                kind=lsp.CompletionItemKind.Reference,
                detail=f"{i['kind']} · {i['file']}:{i['line']}",
                documentation=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=f"```\n{i['signature']}\n```\n\n{i['doc'] or ''}"),
                text_edit=lsp.TextEdit(range=edit_range, new_text=i["ref"]),
                sort_text=f"{n:03}",
            )
            for n, i in enumerate(items)
        ],
    )


def describe(ctx: Context, target: str) -> tuple[str, tuple[str, int]] | None:
    """Markdown describing what `target` names, and where it is.

    Parameters
    ----------
    ctx : Context
        The project.
    target : str
        A reference: a symbol, or `r:`, `t:` or `f:` and an ID.

    Returns
    -------
    tuple of (str, tuple of (str, int)) or None
        The Markdown, and the file and line it's defined at; None if nothing by that name.
    """
    if target.startswith(("t:", "f:")):
        d = ctx.glossary.get(target)
        if not d:
            return None
        status = f" · *{d.status}*" if d.status else ""
        return f"**{d.kind}** `{d.id}`{status}\n\n{d.text}\n\n{d.file}:{d.line}", (d.file, d.line)
    if target.startswith("r:"):
        r = ctx.spec.find(target[2:])
        if not r:
            return None
        traces = ctx.index.traces().get(r.id, [])
        code = "\n".join(f"- {t.kind}: `{ctx.index.shortest_unique(t.symbol) if t.symbol else t.file}` ({t.file}:{t.line})" for t in traces)
        return f"**requirement** `{r.id}`\n\n{r.text}\n\n{code}\n\n{r.file}:{r.line}", (r.file, r.line)
    sym, _ = ctx.index.resolve(target.split(" > ")[0])
    if not sym:
        return None
    markers = ", ".join(f"{k} {i}" for k, i in sym.markers)
    return (
        f"**{sym.kind}** `{sym.qualified}`\n\n```\n{sym.signature}\n```\n\n{sym.doc}\n\n"
        + (f"```text\n{sym.details}\n```\n\n" if sym.details else "")
        + f"{markers}\n\n{sym.file}:{sym.line}",
        (sym.file, sym.line),
    )


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: CodewalkServer, params: lsp.HoverParams):
    found = ls.context(params.text_document.uri)
    if not found:
        return None
    ctx = found[0]
    lines = ls.workspace.get_text_document(params.text_document.uri).source.split("\n")
    span = reference_at(lines, params.position.line, params.position.character)
    if not span or not (what := describe(ctx, span[0])):
        return None
    row = params.position.line
    return lsp.Hover(
        contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=what[0]),
        range=lsp.Range(start=lsp.Position(line=row, character=span[1]), end=lsp.Position(line=row, character=span[2])),
    )


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(ls: CodewalkServer, params: lsp.DefinitionParams):
    found = ls.context(params.text_document.uri)
    if not found:
        return None
    ctx = found[0]
    lines = ls.workspace.get_text_document(params.text_document.uri).source.split("\n")
    span = reference_at(lines, params.position.line, params.position.character)
    if not span or not (what := describe(ctx, span[0])):
        return None
    file, line = what[1]
    at = lsp.Position(line=line - 1, character=0)
    return lsp.Location(uri=(ctx.root / file).as_uri(), range=lsp.Range(start=at, end=at))


@server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
def code_action(ls: CodewalkServer, params: lsp.CodeActionParams):
    actions = []
    for d in params.context.diagnostics:
        data = d.data or {}
        for cand in (data.get("candidates") or [])[:6]:
            actions.append(
                lsp.CodeAction(
                    title=f"Use {cand}",
                    kind=lsp.CodeActionKind.QuickFix,
                    diagnostics=[d],
                    edit=lsp.WorkspaceEdit(changes={params.text_document.uri: [lsp.TextEdit(range=d.range, new_text=cand)]}),
                )
            )
    return actions


def main() -> None:
    server.start_io()
