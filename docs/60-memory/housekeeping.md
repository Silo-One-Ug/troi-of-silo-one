---
title: Housekeeping
description: "What is tidied at night, always through the Trash: logs, old captures, editor backups, and the shared session."
order: 4
---

At 03:00 the pulse runs `troi-console/housekeeping.sh`:

- logs that pass about 20 MB are rotated, and rotated logs go to the Trash after a week;
- camera looks, screenshots and Telegram files older than 14 days go to the Trash, unless starred
  (their record stays);
- editor backups in `data/backups/` go to the Trash after 30 days.

At 03:30 it compacts the shared session, if the voice line is up and idle, so the conversation
keeps room to think; the boot file survives compaction and the agent re-reads the vault's index
after one.

Nothing is ever deleted outright: everything housekeeping removes goes to the macOS Trash, where you
can still recover it. Run it now with `housekeeping.sh`, or from Routines with **Run now**;
`doctor.sh` is the check-up.
