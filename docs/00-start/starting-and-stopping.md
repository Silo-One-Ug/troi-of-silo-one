---
title: Starting and stopping
description: The Desktop shortcut and the troi command, what comes up, the services that keep running, and starting over.
order: 5
---

## Start

Double-click **Troi** on the Desktop, or type `troi` in a terminal. Everything comes up:

| Piece | Where |
| --- | --- |
| The console | `http://localhost:3100` |
| The agent's server (its API) | `http://127.0.0.1:8796` |
| The face | `http://127.0.0.1:8790` |
| The hands board | `http://127.0.0.1:8794` |
| The agent's browser | Arc, or a Chrome of the agent's own, with its debugging port 9223 |
| The voice line | in the Terminal window |

The agent's browser opens the console. The first time, the console goes to
[the welcome](the-welcome.md). Starting Troi twice is safe: the new launch replaces the old one and
frees its own ports.

The Desktop shortcut and the `troi` command both run `start.sh` at the root of the repository, which
builds the console when its code changed, serves it, and hands over to `troi-console/start.sh` for
the agent's own processes.

## Stop

Ctrl-C in that Terminal window, or close it. The globe dims to "off". The four background services
keep running: the pulse (reminders, the briefs, the watches), the globe, the Telegram bridge and the
nightly backup. Check them with:

```bash
python3 troi-console/setup.py services status
```

`restart`, `install` and `remove` do what they say. The nightly backup shows "not running" between
runs; that is normal. See [Services](../70-reference/services.md).

## A terminal session

The Conversation page takes typed turns in the same session as your voice. For a terminal session of
your own, `cd ~/troi-of-silo-one && claude` gives you the same boot file and the same memory.

## Updating

`git pull && ./install.sh`, then start Troi again.

## Starting over

1. Stop Troi (Ctrl-C in its Terminal window) and run `python3 troi-console/setup.py services remove`.
2. Move `data/` to the Trash. It holds everything Troi kept.
3. Remove the secrets:

   ```bash
   for n in pin telegram elevenlabs openai gemini agora-appid agora-cert; do
     security delete-generic-password -a troi-of-silo-one -s "troi-of-silo-one.$n" >/dev/null 2>&1 && echo "removed $n"
   done
   ```

4. Run `./install.sh` again. The next start opens the welcome.
