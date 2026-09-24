---
title: Backups
description: The vault and the record go to private repositories of yours every night at 23:30. What is written where, as whom, and how to run one now.
order: 3
---

Every night at 23:30 two things go to private repositories, written as the GitHub account in
`github_account` and, when one is set, under the organization in `backup_org` (both in
`data/console.json`; the welcome's **Memory** step shows the pair it will use). They use that
account's `gh` token whichever account is active in `gh`. Sign it in once with `gh auth login`.

- **The vault** is committed and pushed to its own git remote. A vault without one gets `troi-vault`
  in the organization (or `vault_repo` from the settings), created on the first run. Pushes never
  force.
- **Troi's record**, the database and any new files in `data/blobs/`, goes as one release a night
  to `troi-of-silo-one-backups`, or to `backup_repo` from the welcome's **Memory** step.

Missing repositories are created on the first run. Backups only ever add; nothing is deleted.

## Now

"Back up now" to the agent, or Routines › Vault backup › **Run now**, or from a terminal:

```bash
troi-console/backup-vault.sh     # the vault, then the record
```

Starting Troi never runs a backup. The nightly backup is one of the four background services, so it
runs whether or not Troi is started; between runs `services status` shows it as not running, which
is normal.

## Restoring

The vault is a git repository: clone it. The record is a release: download its assets back into
`data/` (the database, and the files under `data/blobs/`). Point the welcome's Memory step at the
vault, and Troi is back with everything it knew.
