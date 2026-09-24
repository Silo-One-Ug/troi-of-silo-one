---
title: The toolbox
description: Every tool the agent has, in troi-console/, with its usage. tools.sh prints the same list.
order: 1
---

All in `troi-console/` unless noted. Read a script's header for its usage; several of them act when
run with no arguments (`backup-vault.sh`, `report.py`, `housekeeping.sh`, `look.sh`,
`look-screen.sh`, `doctor.sh`, `ci-status.sh`). `troi-console/tools.sh` prints this list.

| Tool | Usage | What it does |
| --- | --- | --- |
| browser | `mcp__playwright__*` (navigate, click, type, snapshot, screenshot, tabs) | The browser the agent drives: Arc when it is installed (your Arc, your logins included: money, deletions and messages need your go-ahead), else a Chrome of its own |
| hands | `mcp__hands__*` (apps, launch, focus, windows, inspect, find, read, press, set, perform, menu, type, key, wait, click) | Every app by name through its accessibility tree, the result read back, no screenshot; risky labels are filed for approval. `hands.sh <command>` is the same from a terminal |
| `cursor.sh` | `where`, `under`, `move`, `click`, `double`, `right`, `drag`, `type`, `key` | The pointer and keyboard fallback for what has no name (`look-screen.sh` first; risky buttons need your approval) |
| `look.sh` | | One camera photo, its path printed |
| `look-screen.sh` | `[display]` | One screenshot, its path printed |
| `read.py` | `<file> [--sheet NAME] [--rows N] [--max-chars N]` | A file the Read tool cannot open, as text: xlsx sheets as tables, csv, pptx slides, docx and rtf through textutil, pdf through pdftotext |
| `apps.sh` | `list`, `running`, `open`, `focus`, `quit`, `kill` (asks you) | Applications |
| `fs.sh` | `move`, `rename`, `copy`, `mkdir`, `reveal`, `open [app]`, `undo`, `trash` (asks you), `pending` | Files, only inside the file roots (the vault is one) |
| `console.sh` | see [console.sh](console-sh.md) | The console, driven |
| `show-image.sh` | `<file> [title] [x] [y]` | A picture or a 3D model on the hands board |
| `../barehands/bin/board.sh`, `board-state.sh` | `'{"a":"present",…}'` | The hands board itself, and what is on it |
| `remind.sh` | `20m "text"`, `15:00 "text"`, `list`, `cancel N` | Reminders |
| `show.py` | `'<json tree>'`, `chart …`, `table …`, `vocabulary` | Interface drawn in the conversation |
| `media.py` | `now`, `play [words]`, `pause`, `resume`, `stop`, `next`, `prev`, `volume N`, `louder`, `quieter`, `shuffle on\|off`, `like`, `movie on\|off` | Apple Music by voice, and movie mode |
| `db.py` | `tail [N]`, `sessions`, `stats`, `star <id\|path>`, `retain` | The record |
| `meeting.py` | `devices`, `start <name> [--device NAME]`, `stop`, `status`, `transcribe <file> [--lang xx] [--speakers N]`, `list` | Meetings |
| `ci-status.sh` | | CI, PRs and releases per repo of the GitHub orgs and users you watch |
| `pr.py` | `list [repo]`, `review <repo> <n> [--post] [--tests]`, `review <project> --local`, `show <repo> <n>` | A PR review, headless, in a throwaway checkout |
| `code.sh` | `list`, `<project> [--window]` | A Claude Code session inside a project folder that still boots as the agent |
| `servers.py` | `list`, `add <name> <ssh-host> [role]`, `check [name] [--json]` | Read-only health of the servers in `data/servers.json` |
| `agenda.py` | `today`, `next`, `week`, `soon [min]`, `current` | The Mac's Calendar app |
| `face.py` | `verify`, `check` | Face ID (its own environment); learning your face is yours to do |
| `browser-mcp.sh` | `open`, `which` | Open the browser with its port 9223 (Arc, or Chrome), or say which it is |
| `news.py` | `brief [uganda\|world\|all] [--n N] [--hours H] [--show]`, `topic "<words>"`, `read <url>`, `videos <outlet>`, `social <outlet>`, `sources` | The news, Uganda first |
| `pictures.py` | `search "topic" [--n 6] [--show] [--add]`, `page <url> [--show]`, `shot <url> [--show]`, `board <title> <files…>`, `focus <n\|word>`, `unfocus`, `clear` | Research pictures, credited, on the board |
| `imagine.py` | `"prompt" [--show] [--size 1536x1024] [--from img]`, `check` | A picture from words |
| `telegram.py` | `send "text"`, `say "text"`, `photo <file> [caption]` (with `backtalk/.venv/bin/python`) | A message, a voice note or a picture to your phone |
| `agora_call.py` | `call`, `check`, `link` (with `backtalk/.venv/bin/python`) | A voice call to your phone |
| `report.py` | `[--date D] [--no-send] [--no-narrative]` | The end-of-day report |
| `backup-vault.sh` | | Back up now: the vault, then the record |
| `doctor.sh` | | The check-up, in plain words |
| `housekeeping.sh` | | Rotate logs, send old captures to the Trash |
| `hands.sh` | `doctor`, and every hands tool by name | The native hands from a terminal |
| `setup.py` | `render`, `services status\|restart\|install\|remove` | The rendered files and the background services |
| `keychain.py` | `list`, `set <name>` | Secrets |
| `gh` | | GitHub (and `gcloud`, `docker`, `kubectl` where this Mac has them) |
