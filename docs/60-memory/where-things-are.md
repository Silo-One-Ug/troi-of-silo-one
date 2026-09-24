---
title: Where things are
description: "Every path in one table: your data, the settings, the record, the vault, the prints, the logs, the models, the rendered files and the services."
order: 5
---

Everything Troi keeps lives in `data/`, one folder that you can back up, move or wipe. It is not
tracked by git.

| Thing | Where |
| --- | --- |
| Your settings | `data/console.json` (written by the welcome and the Modes page) |
| Troi's record | `data/troi.db` (`troi-console/db.py tail`, `sessions`, `stats`) |
| Files it made or received | `data/blobs/<kind>/`: `looks`, `screens`, `research`, `imagined`, `telegram`, `meetings`, `reports`, `reviews`, `board`, `uploads` |
| The vault | `data/vault/`, or the one you chose (`vault` in the settings) |
| The previous version of every file edited in the console | `data/backups/` (to the Trash after 30 days) |
| The servers the pulse watches | `data/servers.json` |
| Voice and face prints | `data/prints/` (they never leave the Mac) |
| Logs | `data/logs/`, `backtalk/logs/backtalk.log` |
| Throwaway files | `data/cache/` (safe to delete at any time) |
| Speech models | `data/models/` |
| The agent's browser profile | Arc's own profile when the browser is Arc; `data/browser/` when it is a Chrome of the agent's own |
| Files the agent made and no longer needs | `data/trash/<date>/` |
| Secrets | the Keychain, account `troi-of-silo-one` (`troi-console/keychain.py list`) |
| Boot file (identity, rules, abilities) | `CLAUDE.md`, rendered from `troi-console/templates/CLAUDE.md` |
| Claude Code hooks and permissions | `.claude/settings.json`, rendered from `troi-console/templates/settings.json` |
| The agent's tool servers | `.mcp.json`, rendered from `troi-console/templates/mcp.json` |
| Voice line settings | `backtalk/backtalk.json` (rendered, plus your microphone choices) |
| The outlets the news reads | `troi-console/news.json` |
| Background services | `~/Library/LaunchAgents/com.troi-of-silo-one.*.plist` |
| The Desktop shortcut and the `troi` command | `~/Desktop/Troi.command`, `~/.local/bin/troi` |

`TROI_DATA` in the environment moves `data/` somewhere else.
