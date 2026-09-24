---
status: active
project: meta
type: guide
---
# Meeting Prep & Notes

**The job:** Before a meeting, a short brief; after it, the note and the action items.

## Before (a "(calendar: … starts at HH:MM)" line, or "prep me for …")
1. `__ROOT__/troi-console/agenda.py next` — who, when, the link.
2. Search the vault for the people and the project; read the last note about them.
3. Say it in three sentences: what the meeting is about, what happened last time, what __OWNER__ wants out of it. Offer to record it (`meeting.py start`).

## After (a recording, or "write up the meeting")
1. `meeting.py transcribe <file>` — a speaker-labelled transcript (it prints the credits used).
2. Write the meeting note in the project's folder: date, who, what was decided, what is open, with a link to the transcript's path.
3. Put __OWNER__'s action items on [[Active Priorities]], tagged with the project, and log the meeting in today's daily note.

## Quality bar
- Decisions and actions, not a transcript retold. Names spelled right. Nothing invented.
