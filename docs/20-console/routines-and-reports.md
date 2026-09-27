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
| The CI watch | every 3 minutes, the newest run on `main` of every repo of the GitHub orgs and users on its card |
| The server watch | every 15 minutes, read-only over SSH |
| The Grafana watch | every minute, the alert rules' state at your Grafana (`data/grafana.json`, the token in the Keychain): what began firing and what resolved |
| The calendar | a heads-up 15 minutes before an event |
| The Mac itself | every 15 minutes, read-only: the startup disk, memory pressure, a process hot for two rounds, the battery, the heat; only what is new is said |
| The vault backup | 23:30 nightly: the vault, then the record |
| Housekeeping | 03:00: logs and old captures |
| Session compaction | 03:30: the shared session is compacted while the voice line is idle |
| The Telegram bridge and the globe | always on, as background services |

**Run now** is there for the report, the brief, compaction, the backup, housekeeping and CI. Below
them are the reminders, with Cancel. The CI watch's card is where its GitHub orgs and users are set:
type a name and press Watch; × stops watching one. It needs `gh` signed in. "What's scheduled" or
"open the routines" brings the page up.

### Watches

"Watch this, and when it happens, do that." Say it in words ("watch my Downloads for PDFs and file
the invoices under Finance", "every Monday at eight, prepare my weekly briefing", "tell me when
Docker stops", "when the disk is under ten gigabytes, warn me") and the agent files a watch. The
triggers: a schedule in plain words, a folder, a file, a process, an app, a page, the disk, the
power, the battery, the Wi-Fi. When one fires, the agent gets your instruction and does it under its
usual rules: nothing is deleted, anything risky is filed for your approval. A watch can also only tell.
The Routines page lists them with a switch; a watch is switched off, never removed. Each has a
cooldown and a daily cap, a burst of new files comes as one line, and a one-off ("in twenty
minutes", "at nine tomorrow") turns itself off after firing. Under the hood: `watches.py`.

### Triage and quiet hours

What the pulse has to say is sorted before it is said. **Urgent** (a server down or unreachable, a
critical alert) is spoken as soon as the agent is free and always sent to your phone, quiet hours or
not. **Action** (a failed build, a new server issue, a reminder, a calendar heads-up, a watch) is
spoken when the agent is free, and goes to the phone when the voice line is down. **FYI** (a build
green again, an issue resolved) is never spoken: it waits in the digest. **Ignore** is only logged.
"What did I miss" reads the digest, by level, newest first.

Quiet hours hold the action items for the digest and let only the urgent through: your word ("don't
disturb me for two hours unless it's urgent"), a meeting being recorded, movie mode, an event in
progress on your calendar, and the night (23:00 to 07:00; `quiet_night: false` in the settings turns
that off). A watch can be made fyi or urgent when it is set.

The pulse (`troi-console/pulse.py`) runs the clock. It is a background service, so the reminders,
the watches and the nightly jobs run whether or not Troi is started; what it has to say goes to the
agent when the voice line is up and to Telegram when it is down.

## Reports

The end-of-day reports, each shown as it is, with its PDF, and a button that builds today's now. A
report holds the day's commits in the git repositories under your file roots and in the GitHub orgs
and users the CI watch follows (who, what, when), CI runs, notes changed in the vault, files
touched, reminders that fired, and a "What changed today" paragraph written by the agent. See
[Briefs and reports](../40-abilities/briefs-and-reports.md).
