---
weight: 40
---

## The browser

`codewalk serve` is where codewalks are read and written. It's local: it listens only
on the loopback address, and writes only codewalks and the review file
(`serve.local`). It watches the files, and a page changes as its file, or the code it
shows, changes (`serve.live`), including code that's added, removed or moved. A change
caught half-made, as git makes them in a rebase, is read again a moment later, and never
stops the watching (`serve.live.settle`). Ctrl-C stops it at once, whatever pages are open
(`serve.stop`).

### Reading

The index lists the codewalks by folder, with their tags, how they link to each other,
and how much is reviewed; and the specs, as a tree of their folders
(`ui.index`). Within a folder, a file's `weight`, in its front matter, says where it goes:
lighter first, then those without one, by title (`ui.weight`). Clicking a name, in prose or in the code shown, opens its file beside the
codewalk, at the symbol, with an outline of the file (`ui.context`). So does a
Markdown link to a source file, at the line it names, if any (`ui.context-link`). A requirement a PRD proposes can be opened in Zed or asked about, as
an excerpt can (`ui.prd-requirement`). The contents, to
the left, mark the section you're reading, as you scroll and wherever you came from
(`ui.contents`).

The margin, beside a codewalk or a spec file, follows the page, keeping the cards for
what's in the middle of the window beside it, even when cards above have piled up; it
isn't scrolled by itself, and scrolling over it scrolls the page. Opening a spec for one
requirement lines its card up with the prose citing it (`ui.margin`). Opening or closing a
file beside the page keeps your place: the block whose name you clicked, or the one at the
top of the window, stays where it was (`ui.context-place`).

### Editing

Editing shows the Markdown and its preview side by side, scrolling together, and each
keeps your place: open the editor from what you're reading, and you're at the same
place, and the same going back (`ui.place`). The panes scroll; the page doesn't
(`ui.edit-panes`). Typing `[[`, or in a `walk` block, completes names. The preview's
margin can be put away as it can when reading, and is, while a file is open beside the
editor (`ui.edit-margin`).

## Terms

r[term.weight]
A number in a codewalk's or spec file's front matter saying where it goes in its
folder: lighter first, then those without one, by title.

r[term.spec-view]
A spec file as the browser shows it: its prose, with each requirement the prose cites in
the margin beside it, and what's uncited, missing or drifted.

r[term.margin]
The column beside a page in the browser: for a codewalk, its trail, block by block;
for a spec file, the requirements its prose cites.

## Requirements

r[serve.local+2]
The server MUST listen only on 127.0.0.1, and MUST NOT write any file but a codewalk
or spec under the docs or spec globs, `codewalk.review.json`, or, in a workspace, a new
project's `codewalk.toml` (`ui.project-add`).

r[serve.workspace]
Started in a folder that has no `codewalk.toml`, and isn't in a repository whose root
has one, `codewalk serve` MUST serve every folder one level below it that has a
`codewalk.toml` (and no folder deeper) as a project of one workspace, named by its
folder. With no such folder, it MUST serve the folder itself, as before.

r[serve.workspace-pages]
In a workspace, each project's pages and API MUST be served under `/p/<name>/`, every
link and request a page makes MUST stay under its project's path, and `/` MUST lead to
the first project by name. Each project MUST be read, watched and refreshed on its own.

r[ui.project]
In a workspace, every page's top bar MUST show the projects, with the page's selected,
and choosing another MUST open its index.

r[ui.project-add]
In a workspace, the projects MUST end with Add project, which MUST offer the
workspace's folders that have no `codewalk.toml`, and for the one chosen, its folders
(two levels down) for its codewalks and, optionally, its specs. Adding it MUST write the
folder's `codewalk.toml`, with those folders and its code guessed from what's at its
root, serve it at once, and open it; a folder outside the workspace, or one that's a
project already, MUST be refused.

r[serve.files]
The server MUST show a file beside a page if it's under the root or is an indexed source,
which may be outside the root (`../other/src/**/*.rs`), and MUST NOT show any other.

r[serve.stop]
On SIGINT or SIGTERM, the server MUST end the pages' event streams and stop within a few
seconds, with pages open.

r[serve.live]
A page MUST be refreshed when its file, or a source file it shows, changes.

r[serve.live.settle]
The index MUST follow source files being added, removed and moved. A change that can't be
read, because a file went or was half-written while it was read, MUST be read again
shortly, and MUST NOT stop later changes from being followed.

r[ui.index]
The index MUST group codewalks by folder, filterable by tag and text, and MUST list
spec files as a tree of their folders, with titles rendered from their Markdown.

r[ui.weight]
Within a folder, codewalks and spec files with a `weight` in their front matter MUST
be listed in ascending order of it, before those without one, which MUST be listed by
title.

r[ui.context]
Clicking a name in prose, or in shown code where the name is a symbol in the same file
or the only symbol with that name, MUST open the symbol's file beside the page, scrolled
to and highlighting the symbol.

r[ui.contents]
Reading a codewalk, its contents MUST mark the section whose heading is the last at or
above the top quarter of the window, or the last heading in the window once the page is
scrolled to its end, and MUST keep that mark in view in the contents.

r[ui.context-link]
Clicking a Markdown link, in a codewalk's prose, to a source file the index reads MUST
open that file beside the page, scrolled to and highlighting the line or lines its `#L`
anchor names, if it has one, and MUST NOT follow the link.

r[ui.prd-requirement]
Each requirement a PRD proposes MUST offer to open the PRD in Zed at it, and to ask a
question about it, as an excerpt does; the question MUST be written directly after it.

r[ui.margin+2]
Reading a codewalk or spec file, the margin MUST follow the page, keeping the cards for the
prose at the middle of the window beside that prose, and scrolling over the margin MUST
scroll the page. A spec view opened for a requirement MUST show its card beside the prose
citing it.

r[ui.context-place]
Opening or closing a file beside the page MUST leave the block whose name was clicked, or
else the block at the top of the window, at the same height in the window.

r[ui.place]
Moving between reading and editing MUST keep the first line of Markdown in view.

r[ui.edit-panes]
While editing, the Markdown and the preview MUST each scroll on their own, and the page
itself MUST NOT scroll.

r[ui.edit-margin]
While editing, the preview MUST offer the same toggle for its margin as reading does,
remembered between the two, and MUST hide its margin while a file is open beside it.
