---
title: Services
description: The four background services under launchd, setup.py, and the files it renders from the templates.
order: 5
---

Four background services run under launchd as `com.troi-of-silo-one.{pulse,ring,telegram,vault-backup}`,
whether or not Troi is started:

| Service | What it does |
| --- | --- |
| `pulse` | Reminders, the morning brief and the end-of-day report, the CI watch, the server watch, the calendar heads-ups, housekeeping and session compaction |
| `ring` | The globe |
| `telegram` | The Telegram bridge |
| `vault-backup` | The nightly backup at 23:30 (it shows "not running" between runs) |

```bash
python3 troi-console/setup.py services status
python3 troi-console/setup.py services restart [pulse|ring|telegram|vault-backup]
python3 troi-console/setup.py services install
python3 troi-console/setup.py services remove
```

## The rendered files

`python3 troi-console/setup.py render` writes this Mac's files from `troi-console/templates/`:

| Template | Rendered file | What it is |
| --- | --- | --- |
| `templates/CLAUDE.md` | `CLAUDE.md` | The agent's boot file: identity, rules, abilities |
| `templates/settings.json` | `.claude/settings.json` | Claude Code's settings: the guard's hooks, vault access, denied destructive commands |
| `templates/mcp.json` | `.mcp.json` | The agent's tool servers: the browser and the native hands |
| the components' configs | `backtalk/backtalk.json` and others | The voice line and the pieces, with your paths and names |

The installer renders them and marks the folder as trusted for Claude Code; run `render` again after
changing a template or the keys it uses (`file_roots`, `vault`, your name). The templates and the
rendered files are among the guard's safeguards: the agent cannot change its own rules.

## The stack Troi starts

`start.sh` (the Desktop shortcut and the `troi` command) starts, in order: the console on `:3100`,
then, through `troi-console/start.sh`, the agent's server on `:8796`, the face on `:8790`, the
hands board on `:8794`, the browser with its port `9223` and its bridge, the eyes, and the voice
line in the Terminal window. Ctrl-C stops all of it; the four services above keep running.
