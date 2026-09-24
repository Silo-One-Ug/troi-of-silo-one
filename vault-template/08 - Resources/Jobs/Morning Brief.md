---
status: active
project: meta
type: guide
---
# Morning Brief

**The job:** A spoken start-of-day summary for __OWNER__. Fires on "good morning" / "start my day" / "morning brief", or on the scheduled time (a "(scheduled morning brief)" line).

## Boot chain (read these, in order)
1. This note, end to end.
2. [[Active Priorities]] — the open work.
3. Yesterday's daily note in `01 - Daily Notes/` — what was in flight.
4. `__ROOT__/troi-console/ci-status.sh` — CI, open PRs and latest release per repo (only when `github_org` is set).
5. `__ROOT__/troi-console/remind.sh list` — reminders set for today.
6. `__ROOT__/troi-console/agenda.py today` — the day's events.

## The procedure
1. Check the real date and time first.
2. Gather the sources above. Do not read anything else.
3. Speak it in this order, at most six short sentences: greeting with the day and date; the top open priority; anything red in CI or a PR waiting; the day's events and reminders; one thing carried over from yesterday. If a source is empty, skip it without saying so.
4. End with "What are we working on first?" and wait.

## Headlines
Run `__ROOT__/troi-console/news.py brief uganda --n 2 --hours 18` and say the three most important stories in one sentence each, with the outlet. Add one line from `news.py brief world --n 1` only if something big happened. Offer to read any of them out.

## Quality bar
- Under thirty seconds spoken. Facts only, from the sources; nothing invented.

## Lessons (fold corrections in here over time)
- None yet.
