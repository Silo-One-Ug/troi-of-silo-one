---
title: The vault
description: The memory Troi thinks with. Its structure, the daily notes, the jobs, the checkpoint discipline, and working with it in Obsidian.
order: 1
---

The vault is Troi's memory and its formation: a folder of Markdown notes, yours to read and edit in
Obsidian or any editor, git-backed. The welcome creates one in `data/vault` from `vault-template/`
(Troi interviews you to fill it in) or points Troi at a vault you already have.

Troi boots fresh every session and holds only the current job; it reaches for the rest on demand.
That works because the vault is organised so retrieval is precise: one index, one note per thing,
one master note per recurring job pointing at exactly what that job needs.

## The structure

| Path | What it is |
| --- | --- |
| `VAULT-INDEX.md` | The operating manual: your profile, the rules, the map of the vault. Read at every session start, and again after a compaction |
| `Active Priorities.md` | What is open now; scanned at every start so nothing queued slips |
| `00 - Inbox/` | Things not yet filed |
| `01 - Daily Notes/` | One note a day, in monthly folders (`06 - June 2026/2026-06-14.md`), always created from `Daily Note Template.md`; an append-only log |
| `06 - Personal/` | Your own notes |
| `07 - Archive/` | What is done |
| `08 - Resources/` | Reference material, `Who is Troi.md` (its profile and stock answers), and `Jobs/` |
| `08 - Resources/Jobs/` | The master note per recurring job: Morning Brief, CI Failure Response, Code Review, Meeting Prep & Notes, Server Maintenance |

Every folder has an index note named after it (`08 - Resources.md`), kept in sync with the folder;
a note the map does not show is one no future session will find.

## How it stays healthy

- **Checkpoints.** Any time something changes that a future session would need, the agent persists
  it without being asked: the relevant note, the folder's index and today's daily note, in the same
  pass, and reads it back to verify. A daily-note entry alone is never the documentation.
- **One source of truth.** It updates an existing note before creating a new one, and deletes what
  it replaced instead of leaving both (daily notes excepted).
- **Written decisions.** A decision that matters is written down with its reason; one that only
  lives in chat is not made yet.
- **Banked methods.** When a recurring operation fails on the first approach and a second works, the
  winning method (and the dead end) goes into that operation's note.

## Working with it yourself

- **Obsidian** is the natural editor: wikilinks, the graph, the daily notes. Rename notes inside
  Obsidian so it repairs the `[[links]]` that point to them; a rename from the shell breaks them.
- **The console** shows the vault as [a wall of cards](../30-views/vault.md) and draws its links as
  the memory graph; notes open and edit in the drawer, with the previous version kept in
  `data/backups/`.
- **Deliverables** land in your folders or the vault, never in the agent's temporary directories.

## Backups

The vault is committed and pushed every night at 23:30 ([Backups](backups.md)).
