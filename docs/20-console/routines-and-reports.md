---
title: Routines and Reports
description: Everything that runs on a clock, with its last run and Run now; the reminders; the end-of-day reports.
order: 5
---

## Routines

Everything that runs on a clock, with its last run:

| Routine | When |
| --- | --- |
| The morning brief | `brief_time` (08:00 by default), with a switch |
| The end-of-day report | `report_time` (18:30 by default), with a switch |
| The CI watch | every 3 minutes, the newest run on `main` of every repo in your GitHub org |
| The server watch | every 15 minutes, read-only over SSH |
| The calendar | a heads-up 15 minutes before an event |
| The vault backup | 23:30 nightly: the vault, then the record |
| Housekeeping | 03:00: logs and old captures |
| Session compaction | 03:30: the shared session is compacted while the voice line is idle |
| The Telegram bridge and the globe | always on, as background services |

**Run now** is there for the report, the brief, compaction, the backup, housekeeping and CI. Below
them are the reminders, with Cancel. "What's scheduled" or "open the routines" brings the page up.

The pulse (`troi-console/pulse.py`) runs the clock. It is a background service, so the reminders,
the watches and the nightly jobs run whether or not Troi is started; what it has to say goes to the
agent when the voice line is up and to Telegram when it is down.

## Reports

The end-of-day reports, each shown as it is, with its PDF, and a button that builds today's now. A
report holds the day's commits in the git repositories under your file roots and in your GitHub org
(who, what, when), CI runs, notes changed in the vault, files touched, reminders that fired, and a
"What changed today" paragraph written by the agent. See
[Briefs and reports](../40-abilities/briefs-and-reports.md).
