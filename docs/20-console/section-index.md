---
title: The console
description: A web app at localhost:3100 with space behind it, a floating bar, eight pages and five views. What is where.
sidebarTitle: Overview
---

The console is a web app at `http://localhost:3100`. Behind the pages is space: the Earth from low
orbit, turning slowly, with a spacecraft whose engines light while the agent works. One control
floats over everything: **the bar**, at the bottom centre.

## The bar

The bar shows the agent's name and state, with a small audio wave: its voice while it speaks, a
breath while it listens. It holds:

- the five **views**, which fill the whole window: the Face, the Board, the Files galaxy, the
  Apps galaxy and the Vault ([The views](../30-views/));
- the **pages**: Conversation, Library, Modes, Routines, Reports, Approvals (with a count of what is
  waiting), Eyes, Browser, Agents (with a count of the agents at work) and Sessions;
- then the bell, the lock and the light/dark switch.

| Page | What it is for |
| --- | --- |
| [Conversation](conversation.md) | Everything the agent hears and says, live; typed turns; the cards it draws |
| [Library](library.md) | Every picture it took, made, found or received, shelved by source and by day |
| [Modes](modes.md) | Every switch: permissions, the microphone, the wake word, the model, eyes, voice ID, face ID, the voice, your phone |
| [Routines and Reports](routines-and-reports.md) | Everything that runs on a clock, with Run now; the end-of-day reports |
| [Approvals](approvals.md) | What waits on you, and a record of earlier decisions |
| [Eyes](eyes.md) | What the agent sees, the sight modes, the hands switch, face ID |
| [Browser](browser.md) | The agent's browser, mirrored live, yours to take over |
| [Agents](agents.md) | Who the brain has put on a task, named for the job, and how each is doing |
| [Sessions](sessions.md) | Every conversation the record holds, the current one, and a new one when you say so |

Also here: [The globe](the-globe.md), the small gold globe that floats over every Space, and
[On your phone](on-your-phone.md), where the console lays itself out as an app.

## Notifications and sound cues

The bell in the bar turns on the system's own notifications; a green dot on the bell says they
are on. Approvals and reminders always notify; a reply or a Telegram message notifies only while
the console is not the page you are looking at.

Short interface sounds (made with ElevenLabs sound effects, in `troi-console/assets/`) play for a new
approval, a due reminder, and a Telegram message while you are elsewhere. Turn them off with
`"cues": false` in `data/console.json`; movie mode silences them for you.

## The lock

Some things need the console unlocked: approving a request, and the protected switches. Type your
PIN at the lock in the bar, or use **Check it's me** on the Eyes page. The console stays unlocked for
15 minutes. Five wrong PINs lock it for ten minutes. See
[Protected settings and the PIN](../50-safety/protected-settings-and-the-pin.md).

## The agent drives it too

"Switch to the hands", "open my files", "open the vault", "open the modes", "show me the browser",
"float the conversation", "tidy up": the agent does all of it with `console.sh`, whose commands the
console follows on whichever page is open, in the same second. The full list is in
[console.sh](../70-reference/console-sh.md).

## Light and dark

The switch in the bar picks the theme; on the phone, More › Appearance offers auto, light and dark.
The views are always dark: they are canvases of their own.
