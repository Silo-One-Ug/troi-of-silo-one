---
title: The API
description: The agent's server speaks AG-UI. The endpoints another client can use, and the ones the console uses.
order: 6
---

The agent's server listens on `http://127.0.0.1:8796` (and, when you turn it on, on Tailscale or
the network: [On your phone](../20-console/on-your-phone.md)). It accepts JSON requests from its own
pages only: a POST must carry an `Origin` of one of this Mac's names, and the protected endpoints
need an unlock token or a paired phone.

## AG-UI

The server speaks [AG-UI](https://docs.ag-ui.com), so any AG-UI client can drive the agent; the
console is one.

- `POST /agent` takes a `RunAgentInput`: the last user message is the line, and
  `forwardedProps.silent: true` makes it a written turn, answered but not spoken. It streams the
  standard events over SSE: the reply as it grows and the tool in use; `silo.state`, `silo.partial`
  and `silo.note`; the cards `silo.pictures`, `silo.headlines` and `silo.ui`; and `silo.approval`
  when something waits for you.
- `GET /events` is the same vocabulary as a running feed of the whole conversation.
- `POST /ask` runs one turn and returns the reply.

## The record

| Endpoint | What it returns |
| --- | --- |
| `GET /history` | The last lines of the conversation |
| `GET /sessions` | The sessions |
| `GET /approvals` | Requests, waiting and decided |
| `GET /transcript`, `GET /state` | What the console polls: the live transcript, and the agent's state with the directives waiting for the console |
| `GET /config` | The settings the console shows, and whether a PIN, prints and keys are set |

## Acting

| Endpoint | What it does |
| --- | --- |
| `POST /say` | A line to the agent (`when: "idle"` waits for the voice line to be idle) |
| `POST /ui` | A directive for the console (what `console.sh` sends) |
| `POST /settings` | A settings change; a protected one is filed unless the console is unlocked |
| `POST /unlock` | The PIN, for a 15-minute unlock token |
| `POST /approve` | Decide a request (unlocked, or from the paired phone) |
| `GET /pending`, `POST /pending-click`, `POST /pending-setting` | What waits, and how the tools file a request |
| `POST /fs` | A file operation inside the file roots |
| `GET /tree`, `/recent`, `/file`, `POST /write` | The galaxies' folder tree, recent files, a file's contents, and an edit (with a backup) |
| `GET /vaultcards`, `/vaultgraph` | The Vault wall and the memory graph |
| `GET /apps`, `POST /app`, `GET /appicon` | The Apps galaxy |
| `GET /images`, `/img`, `POST /star` | The Library |
| `POST /upload`, `GET /find` | A file from the console page (`X-Kind: uploads` keeps it in `data/blobs/uploads` for the agent; otherwise a picture for the board), and the @ picker's search of the file roots |
| `GET /reports`, `GET /report`, `GET /routines`, `POST /routines` | Reports and Routines: the list, one report, the clock and its switches |
| `POST /look`, `/face-verify` | A look now, and Check it's me |
| `GET /browser`, `POST /board`, `POST /show` | The Browser page's mirror, the board, and a card for the conversation |
| `GET /voices` | Your ElevenLabs voices |
| `GET /doctor` | The doctor's findings |
| `POST /setup/profile`, `/setup/vault`, `/setup/backup`, `/setup/services`, `/setup/finish`, `GET /setup/status`, `POST /keychain`, `GET /telegram` | The welcome |

The endpoints under "Acting" exist for the console and the tools, and can change with them; `/agent`,
`/events`, `/ask`, `/history`, `/sessions` and `/approvals` are the ones to build on.
