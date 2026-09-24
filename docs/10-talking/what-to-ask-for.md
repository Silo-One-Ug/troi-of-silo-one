---
title: What to ask for
description: Sentences that work, what each one does, and where to read more.
order: 5
---

Say it the way you would to a person; these are examples, not commands. Each row links to the page
that explains the ability.

| Say | What happens |
| --- | --- |
| "show me my files" / "open `<folder>` in the galaxy" / "where is `<project>`" | The [Files galaxy](../30-views/files-galaxy.md) opens, and the item lights up |
| "open the apps" / "open Spotify" / "close Chrome" / "what's running" | The [Apps galaxy](../30-views/apps-galaxy.md), or the app is opened, focused or politely quit |
| "look at me" / "what am I holding" | One camera photo, described ([Eyes and screen](../40-abilities/eyes-and-screen.md)) |
| "what's on my screen" / "read this error" | A screenshot, read |
| "remind me in 20 minutes to …" / "remind me at 3pm …" | The pulse fires it, and the agent says it (on Telegram when the voice line is down) |
| "what's on today" / "when is my next meeting" | The Mac's Calendar app ([Reminders and calendar](../40-abilities/reminders-and-calendar.md)) |
| "record this meeting" / "stop recording" / "transcribe it" | A recording, then a speaker-labelled transcript and a meeting note ([Meetings](../40-abilities/meetings.md)) |
| "good morning" | The morning brief ([Briefs and reports](../40-abilities/briefs-and-reports.md)) |
| "send me today's report" / "what changed today" | The end-of-day report, now |
| "how is CI" / "any failed builds" | CI status across the GitHub orgs and users you watch ([Code, CI and servers](../40-abilities/code-ci-and-servers.md)) |
| "review PR 3 on my-app" / "review my changes in the website" | A code review in a headless session of the agent's own, posted to the PR only when you say "post it" |
| "work on the website" / "open the my-app project" | A Terminal window with a Claude Code session inside that project that is still your agent |
| "how are the servers" / "check prod" | A read-only health check over SSH of every server it knows |
| "play some jazz" / "play my gospel playlist" / "pause" / "next" / "what's this song" / "louder" | Apple Music ([Music and movies](../40-abilities/music-and-movies.md)) |
| "movie mode" / "movie mode off" | Push to talk, cues off, the conversation hidden and the page dimmed; then back |
| "back up now" | The nightly backup, now: the vault, then the record |
| "call me" | A call link on Telegram; the agent answers ([Calls](calls.md)) |
| "show me the photo of …" | The picture goes up on the hands board |
| "move X into Y" / "rename" / "make a folder" | Done directly, inside your file roots, never overwriting ([Files and apps](../40-abilities/files-and-apps.md)) |
| "delete X" / "trash X" | An approval card. Nothing moves until you approve it, and then it goes to the macOS Trash |
| "click the Save button" / "type hello in that field" / "open the View menu and switch to list" | The [native hands](../40-abilities/native-hands.md): the control is found by name in the app's accessibility tree, pressed, and the result read back; risky labels ask for approval |
| "draw me a …" / "make a picture of …" | A picture, in the Library and on the board ([Pictures](../40-abilities/pictures.md)) |
| "research …" / "show me what … looks like" | Credited pictures on the board while it talks |
| "what's in the news" / "what does NTV say about …" | Headlines per outlet, Uganda first, read out or on the board ([News](../40-abilities/news.md)) |
| "open example.com and fill in the form" | The agent's browser ([The browser](../40-abilities/the-browser.md)) |
| "show me a chart of …" / "compare these" | Drawn in the conversation as a chart, a table or cards ([Drawing in the conversation](../40-abilities/drawing.md)) |
| "switch to the hands" / "open the vault" / "float the conversation" / "tidy up" | The agent drives its own console ([The console](../20-console/)) |
| "go hands free" / "stop asking for permission" / "clear the session" | Only in your verified voice (or your face), from an unlocked console, or with your approve on Telegram |
| "who are you" / "are you human" | Its stock answers; what it is built on stays under the hood ([Guests](../50-safety/guests.md)) |
