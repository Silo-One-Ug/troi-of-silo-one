---
title: Briefs and reports
description: The morning brief at the start of the day and the end-of-day report at its close, on a clock or on request.
order: 10
---

## The morning brief

"Good morning", "start my day", or the clock at `brief_time` (08:00 by default; the Routines page
has the time and a switch): the agent runs the Morning Brief job from the vault, with the day's
events, the reminders, the open priorities and what changed overnight.

## The end-of-day report

At `report_time` (18:30 by default; set it in Routines or as `report_time` in `data/console.json`),
the pulse builds a report of the day:

- commits in the git repositories under your file roots, and in your GitHub org (who, what, when);
- CI runs, notes changed in the vault, files touched and reminders that fired;
- a "What changed today" paragraph, written by the agent from those facts in the same shared
  session.

It is saved as HTML and PDF under `data/blobs/reports/`, the PDF is sent to you on Telegram, and the
Reports page lists every report. Ask for it any time ("send me today's report", "what changed
today") or run `troi-console/report.py`: `--date` for another day, `--no-send` to keep it local,
`--no-narrative` to skip the paragraph.
