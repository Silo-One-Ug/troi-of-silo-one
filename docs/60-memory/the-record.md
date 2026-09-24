---
title: The record
description: data/troi.db, the SQLite file with everything Troi heard, said, showed and decided. How to read it, and how long things are kept.
order: 2
---

Everything the voice line logs is tailed into `data/troi.db`: the conversation per session, the
cards the tools showed, approvals and what became of them, reminders, pictures, reports, routine
runs and the index of every file in `data/blobs/`. The console loads the last lines from it when it
opens, so a reload keeps the conversation.

## Reading it

```bash
troi-console/db.py tail 50       # the last lines of the conversation
troi-console/db.py sessions      # the sessions
troi-console/db.py stats         # what is in the record
troi-console/db.py star <path>   # keep a capture past the 14-day tidy-up
troi-console/db.py retain        # the retention pass, now
```

The server serves it too: `/history`, `/sessions` and `/approvals` ([The API](../70-reference/api.md)).

## Retention

Camera looks, screenshots and Telegram files older than 14 days go to the macOS Trash at night
unless starred (the star in the Library, or `db.py star`). Their rows stay in the record, marked
archived. Everything else in the record stays.

## Who may write it

The agent's tools write the record; the agent itself cannot touch the file, which is among the
safeguards the guard keeps from it. It goes to your private backup repository every night as one
release ([Backups](backups.md)).
