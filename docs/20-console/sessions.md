---
title: Sessions
description: "Every conversation the record holds, the one the agent is in now, and a new one when you say so: a session is yours to start, never the agent's."
order: 10
---

A session is one continuous conversation with the agent: everything said since it began, in every
channel, is the thread it reasons over. The record keeps every session; the **Sessions** page lists
them, newest first, with a title, when it began, when it last spoke and how many lines it holds. The
one the agent is in now carries a **Current** badge.

- **Titles.** Once a session has a few lines, a small model reads it and writes a title of a few
  words, the way a file in a cabinet is labelled; until then the title is your first real line. The
  pencil on an open session renames it, and the agent renames one when you ask.
- **Read one.** Open a session and it shows as it was said: your lines as bubbles, the agent's
  replies as they rendered, the notes between. Nothing on the page changes the record.
- **New session.** The button asks first, then sends the agent the very phrase you would say
  yourself, "clear the session". The agent answers "Cleared. Fresh slate." and starts clean: the
  thread of the old conversation is gone from its head, while the record below and the vault keep
  everything. The new session appears in the list with its first line.
- **Yours to start.** Starting a session is the owner's decision and nobody else's. The phrase is
  caught by the voice line before the agent hears it, and the agent has no tool that could start
  one; the same goes for compacting. Say "clear the session" or "compact the session" out loud, or
  type it in the conversation, and it happens; nothing else does it.
- **Delete.** The bin on a session takes it off the list; its lines stay in the record, and **Show
  the deleted** lists it with **Restore**. Deleting needs you, as an approval does: an unlocked
  console (your PIN, or your face). The session in use cannot be deleted; start a new one first.
- **The agent asks, you decide.** When you tell the agent to delete a session, it files a request
  (`troi-console/sessions.sh delete`), which lands on the Approvals page and in Telegram like a
  trash request; your yes deletes it the same way, and a no leaves it. The agent never deletes a
  session on its own.
- **On the phone** the page is under **More**.

The Conversation page's eraser is different: it only clears the page you are looking at and
touches neither the record nor the session.
