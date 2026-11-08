---
weight: 40
---

## The browser

`codewalk serve` is where codewalks are read and written. It's local: it listens only
on the loopback address, and writes only codewalks and the review file
(`serve.local`). It watches the files, and a page changes as its file, or the code it
shows, changes (`serve.live`). Ctrl-C stops it at once, whatever pages are open
(`serve.stop`).

### Reading

The index lists the codewalks by folder, with their tags, how they link to each other,
and how much is reviewed; and the specs, as a tree of their folders
(`ui.index`). Within a folder, a file's `weight`, in its front matter, says where it goes:
lighter first, then those without one, by title (`ui.weight`). Clicking a name, in prose or in the code shown, opens its file beside the
codewalk, at the symbol, with an outline of the file (`ui.context`).

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

r[serve.local]
The server MUST listen only on 127.0.0.1, and MUST NOT write any file but a codewalk
or spec under the docs or spec globs, or `codewalk.review.json`.

r[serve.stop]
On SIGINT or SIGTERM, the server MUST end the pages' event streams and stop within a few
seconds, with pages open.

r[serve.live]
A page MUST be refreshed when its file, or a source file it shows, changes.

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
