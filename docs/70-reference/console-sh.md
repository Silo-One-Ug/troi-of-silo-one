---
title: console.sh
description: The agent's remote control for its own console. Each command becomes a directive the console follows on whichever page is open, or a setting the server guards.
order: 2
---

`troi-console/console.sh` is how the agent drives the console; it works from a terminal too. Each
command becomes a directive the console follows on whichever page is open, in the same second, or
(marked \*) a setting, which the server guards like any other. Run it with no arguments for the
list.

## Places and views

| Command | What it does |
| --- | --- |
| `go <place>` | `conversation`, `library`, `modes`, `routines`, `reports`, `approvals`, `eyes`, `browser`, `face`, `hands`, `files`, `apps`, `vault` |
| `view face\|hands\|files\|apps\|vault` | A full-window view |
| `vault show\|clear` | The Vault view, or back to the face |
| `files "<folder>"` | That folder as a galaxy in the Files view |
| `focus "<path>"` | Light up that file or folder in the galaxy |
| `apps open` | The Apps galaxy |
| `images open\|close` | The Library |
| `modes\|routines\|approvals\|reports open\|close` | Those pages (`close` goes back to the conversation) |
| `camera open\|close` | The Eyes page |
| `browser open\|close` | The Browser page |

## The conversation

| Command | What it does |
| --- | --- |
| `talk column\|floating` | The conversation as a full column, or a floating pane over every page |
| `panel hide\|show` | Hide or show the floating conversation |
| `tidy` | Put the floating conversation back in its place and show it |
| `hint "<text>"` | A short note above the bar, for nine seconds |

## Switches

| Command | What it does |
| --- | --- |
| `gestures on\|off` | Hand tracking: the board's camera and the galaxies' hands |
| `hands <key> <value>` \* | Tune hand tracking: `pinch_close`, `pinch_open`, `ext`, `dwell_ms`, `magnet` |
| `eyes off\|every\|watch\|screen` \* | The camera and screen sight (turning them on is protected) |
| `wake on\|off` \* | The wake word for hands-free (off is protected) |
| `face-gate on\|off` \* | Hands-free only while your face is at the camera (off is protected) |
| `voice-id off\|on\|learn` \* | Voice identification (off and learn are protected) |
| `voice list\|kokoro\|elevenlabs ["<name or id>"]` \* | Which voice speaks |
| `mode "<phrase>"` | A voice-console phrase, sent once the voice line is idle: "push to talk mode", "go hands free", "start asking again", "stop asking for permission", "switch to the deep model", "back to the fast model", "set effort to low\|medium\|high\|max" |

A directive is picked up by whichever console is open; when none is, it is simply lost, so the agent
opens the page it means first.
