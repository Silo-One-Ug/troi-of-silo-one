---
title: The Vault wall
description: "The agent's memory as a wall of cards: folders as stacks, notes with their opening lines, search, and the memory graph."
order: 2
---

The vault is your agent's memory ([The vault](../60-memory/the-vault.md)). The Vault view shows it
as a wall of cards drawn by the same engine as the galaxies, so every gesture is the same.

- **Folders** sit across the top as small stacks, each with the opening lines of its index note, its
  counts and its newest notes.
- **Notes** sit below, with their opening lines, word and link counts, age and tags.
- **Tap a folder** to open it, and **tap a note** to read it in the drawer (rendered Markdown,
  editable; the previous version is kept in `data/backups/`).
- **Drag a note onto a folder** to move it. **Right-click** for rename, new folder, reveal, or a
  trash request.
- **Search** lights up matches in titles, excerpts and tags. **Memory graph** draws the notes and
  their wikilinks instead.

"Open the vault" opens it by voice; "clear" goes back to the face. Renaming a note here keeps its
wikilinks whole only when done inside Obsidian; the wall renames the file, so fix `[[links]]` after,
or rename in Obsidian.
