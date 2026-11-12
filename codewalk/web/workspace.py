"""Serving several projects at once: a workspace.

A folder with no `codewalk.toml` of its own, but with folders one level below it that
have one, is a workspace, and each of those folders is a project. One server serves them
all: each project's pages are under `/p/<name>/`, named by its folder, and a project is
added by writing a `codewalk.toml` into another of the workspace's folders.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from codewalk.config import FILE, Config
from codewalk.walk.doc import Context
from codewalk.web.server import STATIC, App, make_app

# Folders never worth offering as a project's docs or specs
SKIP = {"node_modules", "target", "dist", "build", "__pycache__", "venv"}


def _folders(root: Path, depth: int = 2) -> list[str]:
    """The folders below `root`, to `depth` levels, as paths from it; hidden ones left out.

    Parameters
    ----------
    root : Path
        Where to look.
    depth : int
        How many levels down.

    Returns
    -------
    list of str
        In order.
    """
    out: list[str] = []
    for child in sorted(root.iterdir()) if root.is_dir() else []:
        if child.is_dir() and not child.name.startswith(".") and child.name not in SKIP:
            out.append(child.name)
            if depth > 1:
                out += [f"{child.name}/{f}" for f in _folders(child, depth - 1)]
    return out


# r[impl serve.workspace]
def find_projects(folder: Path) -> list[Path]:
    """The folders one level below `folder` that have a `codewalk.toml`.

    Parameters
    ----------
    folder : Path
        The workspace.

    Returns
    -------
    list of Path
        By name.
    """
    return [p for p in sorted(folder.iterdir()) if p.is_dir() and not p.name.startswith(".") and (p / FILE).is_file()]


def guess_sources(root: Path) -> list[str]:
    """Where a project's code probably is, from what's at its root.

    A Rust crate's `src`, and a Python project's packages: `src`, or each folder at the root
    with an `__init__.py`. Otherwise codewalk's default.

    Parameters
    ----------
    root : Path
        The project's folder.

    Returns
    -------
    list of str
        Globs, from the project's folder.
    """
    out = []
    if (root / "Cargo.toml").is_file():
        out.append("src/**/*.rs")
    if (root / "pyproject.toml").is_file() or (root / "setup.py").is_file():
        if (root / "src").is_dir():
            out.append("src/**/*.py")
        else:
            out += [f"{p.name}/**/*.py" for p in sorted(root.iterdir()) if (p / "__init__.py").is_file()]
    return out or Config().sources


def config_text(sources: list[str], docs: str, specs: str | None) -> str:
    """A new project's `codewalk.toml`.

    Parameters
    ----------
    sources : list of str
        Globs for its code.
    docs : str
        The folder its codewalks are in, from its root.
    specs : str or None
        The folder its specs are in, if it has any.

    Returns
    -------
    str
        The file's text.
    """
    lines = [
        "# Where codewalk looks, from this folder: its code, its specs and its codewalks",
        f"sources = {json.dumps(sources)}",
        f"specs = {json.dumps([f'{specs}/**/*.md'] if specs else [])}",
        f"docs = {json.dumps([f'{docs}/**/*.md'])}",
    ]
    return "\n".join(lines) + "\n"


class Workspace:
    """The projects served together, and the server that serves them.

    Parameters
    ----------
    folder : Path
        The workspace: its folders one level down with a `codewalk.toml` are its projects.
    watch : bool
        Whether to watch each project's files and refresh its pages as they change.
    """

    def __init__(self, folder: Path, watch: bool = True):
        self.folder = folder
        self.watch = watch
        self.projects: dict[str, Starlette] = {}
        self.stop: asyncio.Event | None = None
        self.tasks: list[asyncio.Task] = []
        self.starlette = Starlette(
            routes=[
                Route("/", self.root),
                Route("/api/workspace", self.info),
                Route("/api/workspace/projects", self.add, methods=["POST"]),
                Mount("/static", StaticFiles(directory=STATIC)),
            ],
            exception_handlers={ValueError: self.refused},
            lifespan=self.lifespan,
        )
        for project in find_projects(folder):
            self.mount(project.name)

    def names(self) -> list[str]:
        return sorted(self.projects)

    def apps(self) -> list[App]:
        return [s.state.app for s in self.projects.values()]

    # r[impl serve.workspace-pages]
    def mount(self, name: str) -> None:
        """Serve the project in the folder `name`, under `/p/<name>/`, watching it if running.

        Parameters
        ----------
        name : str
            The project's folder, one level below the workspace.
        """
        root = self.folder / name
        sub = make_app(Context(root, Config.load(root)), watch=False, base=f"/p/{name}", workspace=self)
        self.projects[name] = sub
        self.starlette.router.routes.append(Mount(f"/p/{name}", sub))
        if self.stop is not None and self.watch:
            self.tasks.append(asyncio.create_task(sub.state.app.watch(self.stop)))

    @asynccontextmanager
    async def lifespan(self, _):
        self.stop = asyncio.Event()
        if self.watch:
            self.tasks = [asyncio.create_task(app.watch(self.stop)) for app in self.apps()]
        yield
        self.stop.set()
        for task in self.tasks:
            task.cancel()

    async def root(self, request: Request):
        names = self.names()
        if not names:
            return PlainTextResponse("No folder here has a codewalk.toml", status_code=404)
        return RedirectResponse(f"/p/{names[0]}/")

    async def refused(self, request: Request, exc):
        return JSONResponse({"error": str(exc)}, status_code=409)

    # r[impl ui.project-add]
    async def info(self, request: Request):
        """The projects, and the folders that could be one, with the folders in each."""
        candidates = [
            {"name": p.name, "folders": _folders(p), "sources": guess_sources(p)}
            for p in sorted(self.folder.iterdir())
            if p.is_dir() and not p.name.startswith(".") and p.name not in self.projects and not (p / FILE).exists()
        ]
        return JSONResponse({"projects": self.names(), "candidates": candidates})

    # r[impl ui.project-add]
    # r[impl serve.local+2]
    async def add(self, request: Request):
        """Make a folder a project: write its `codewalk.toml`, and serve it."""
        body = await request.json()
        name, docs, specs = body["folder"], body["docs"], body.get("specs") or None
        root = self.folder / name
        if "/" in name or name.startswith(".") or not root.is_dir():
            raise ValueError(f"{name} isn't a folder in this workspace")
        if (root / FILE).exists() or name in self.projects:
            raise ValueError(f"{name} is a project already")
        folders = _folders(root)
        for f in (docs, specs):
            if f is not None and f not in folders:
                raise ValueError(f"{f} isn't a folder in {name}")
        (root / FILE).write_text(config_text(guess_sources(root), docs, specs))
        self.mount(name)
        return JSONResponse({"project": name, "href": f"/p/{name}/"})
