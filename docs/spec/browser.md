---
weight: 40
---

## The browser

`codewalk serve` is where walkthroughs are read and written. It's local: it listens only
on the loopback address, writes only walkthroughs, specs and the review file, and changes
git only to start a PRD's branch (`serve.local`). It watches the files, and a page changes as its file, or the code it
shows, changes (`serve.live`). Ctrl-C stops it at once, whatever pages are open
(`serve.stop`).

### Reading

The index lists the walkthroughs by folder, with their tags, how they link to each other,
and how much is reviewed; and the specs, as a tree of their folders
(`ui.index`). Within a folder, a file's `weight`, in its front matter, says where it goes:
lighter first, then those without one, by title (`ui.weight`). Clicking a name, in prose or in the code shown, opens its file beside the
walkthrough, at the symbol, with an outline of the file (`ui.context`).

The margin, beside a walkthrough or a spec file, is a pane of its own: it scrolls by
itself, and follows the page, keeping the cards for what's in the middle of the window
beside it, even when cards above have piled up. Opening a spec for one requirement lines
its card up with the prose citing it (`ui.margin`).

### Editing

Editing shows the Markdown and its preview side by side, scrolling together, and each
keeps your place: open the editor from what you're reading, and you're at the same
place, and the same going back (`ui.place`). The panes scroll; the page doesn't
(`ui.edit-panes`). Typing `[[`, or in a `walk` block, completes names.

## Terms

t[weight]
A number in a walkthrough's or spec file's front matter saying where it goes in its
folder: lighter first, then those without one, by title.

t[spec-view]
A spec file as the browser shows it: its prose, with each requirement the prose cites in
the margin beside it, and what's uncited, missing or drifted.

t[margin]
The column beside a page in the browser: for a walkthrough, its trail, block by block;
for a spec file, the requirements its prose cites.

## Requirements

r[serve.local]
The server MUST listen only on 127.0.0.1, MUST NOT write any file but a walkthrough or
spec under the docs or spec globs, or `codewalk.review.json`, and MUST NOT run a git
command that changes anything, except to start a PRD's branch.

r[serve.stop]
On SIGINT or SIGTERM, the server MUST end the pages' event streams and stop within a few
seconds, with pages open.

r[serve.live]
A page MUST be refreshed when its file, or a source file it shows, changes.

r[ui.index]
The index MUST group walkthroughs by folder, filterable by tag and text, and MUST list
spec files as a tree of their folders, with titles rendered from their Markdown.

r[ui.weight]
Within a folder, walkthroughs and spec files with a `weight` in their front matter MUST
be listed in ascending order of it, before those without one, which MUST be listed by
title.

r[ui.context]
Clicking a name in prose, or in shown code where the name is a symbol in the same file
or the only symbol with that name, MUST open the symbol's file beside the page, scrolled
to and highlighting the symbol.

r[ui.margin]
Reading a walkthrough or spec file, the margin MUST scroll on its own, and as the page
scrolls it MUST keep the cards for the prose at the middle of the window beside that
prose. A spec view opened for a requirement MUST show its card beside the prose citing it.

r[ui.place]
Moving between reading and editing MUST keep the first line of Markdown in view.

r[ui.edit-panes]
While editing, the Markdown and the preview MUST each scroll on their own, and the page
itself MUST NOT scroll.
