---
weight: 40
---

## The browser

`codewalk serve` is where walkthroughs are read and written. It's local: it listens only
on the loopback address, and writes only walkthroughs and the review file
(`serve.local`). It watches the files, and a page changes as its file, or the code it
shows, changes (`serve.live`). Ctrl-C stops it at once, whatever pages are open
(`serve.stop`).

### Reading

The index lists the walkthroughs by folder, with their tags, how they link to each other,
and how much is reviewed; and the specs, as a tree of their folders
(`ui.index`). Within a folder, a file's `weight`, in its front matter, says where it goes:
lighter first, then those without one, by title (`ui.weight`). Clicking a name, in prose or in the code shown, opens its file beside the
walkthrough, at the symbol, with an outline of the file (`ui.context`).

### Editing

Editing shows the Markdown and its preview side by side, scrolling together, and each
keeps your place: open the editor from what you're reading, and you're at the same
place, and the same going back (`ui.place`). The panes scroll; the page doesn't
(`ui.edit-panes`). Typing `[[`, or in a `walk` block, completes names.

## Requirements

r[serve.local]
The server MUST listen only on 127.0.0.1, and MUST NOT write any file but a walkthrough
or spec under the docs or spec globs, or `codewalk.review.json`.

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

r[ui.place]
Moving between reading and editing MUST keep the first line of Markdown in view.

r[ui.edit-panes]
While editing, the Markdown and the preview MUST each scroll on their own, and the page
itself MUST NOT scroll.
