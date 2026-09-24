---
title: The Files galaxy
description: A folder drawn as a galaxy. Moving around, peeking at files, editing, moving, and the memory graph.
order: 1
---

A folder drawn as a galaxy. Folders are glowing nuclei, and files are stars, coloured and marked by
type. Solid lines are the folder tree; dashed lines join related files (the same name with different
extensions, wikilinks, links inside Markdown). The root of the Files galaxy is called **Silo One**;
it holds the folders you gave Troi in the welcome (its file roots) and the vault.

## Moving around

- **Click** a folder to unfold it; **double-click** it to make it the centre. Breadcrumbs go up.
- **The search box** finds a file by name.
- **Wheel** to zoom; **Shift-drag** rotates, **Alt-drag** tilts, and `0` resets.
- **Recent** (the button next to Hands) shows files changed in the last seven days. The view
  refreshes itself when files change.

## Peeking

Double-click a file to peek at it in the **drawer**, a small window of its own inside the galaxy
(drag it, resize it, or minimise it to a chip under the Hands button). It shows rendered Markdown,
highlighted code, Word, Excel, CSV as a table, JSON, PDF, audio, video, 3D models and images.

- **Edit** and **Save** text files. The previous version is kept in `data/backups/`, and goes to the
  Trash after 30 days.
- **Open in app** opens the file in its application.
- **Ask Troi** sends it to the agent.

## Changing things

- **Right-click** (or press and hold) for rename, new folder, reveal in Finder, move to Trash (an
  approval) or let it float.
- **Drag a file onto a folder** to move it; a menu confirms and offers to copy instead.
- **Drag a star aside** to pin it where you work.

Moves and renames happen directly, inside the file roots, and never overwrite. A trash request waits
in Approvals until you approve it, and then the file goes to the macOS Trash.

## Memory graph

**Memory graph** draws the vault's notes and their wikilinks instead of the folder tree.

## By voice

"Show me my files", "open `<folder>` in the galaxy", "where is `<project>`": the galaxy opens on that
folder, and the item lights up.
