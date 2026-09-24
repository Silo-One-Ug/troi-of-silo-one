---
title: Installing
description: What you need, the one command, what the installer does, and how to update.
order: 2
---

Written for someone setting Troi up on a Mac for the first time.

## Before you start

1. **A Mac with Apple Silicon** (M1 or newer) on macOS 14 or newer. The speech models run on the
   Apple GPU through MLX; Intel Macs are not supported.
2. **Homebrew.** Paste the one-liner from [brew.sh](https://brew.sh) into Terminal.
3. **Claude Code**, signed in: [claude.com/claude-code](https://claude.com/claude-code). Run `claude`
   once and log in.
4. **Google Chrome** from [google.com/chrome](https://www.google.com/chrome/). The hands board and
   the page tools that run without a window need it, and without Arc it is the agent's own browser.
5. **Arc**, optionally, from [arc.net](https://arc.net). If Arc is installed, it becomes the browser
   the agent drives, and yours at the same time (Arc runs one instance only): the agent starts it
   with its debugging port, and asks it to quit and come back, tabs and spaces intact, if you opened
   it from the Dock first. See [The browser](../40-abilities/the-browser.md).

The installer adds these command-line tools with Homebrew if they are missing:

| Tool | Used for |
| --- | --- |
| `uv` | Python environments |
| `node` | the console app and the browser bridge |
| `ffmpeg` | Telegram voice notes, meeting recordings |
| `imagesnap` | the camera |
| `cliclick` | the agent's guarded cursor |
| `gh` | the CI watch and the nightly backups (run `gh auth login` after) |
| `espeak-ng` | pronunciation for the local voice |

## Install

```bash
git clone https://github.com/Silo-One-Ug/troi-of-silo-one ~/troi-of-silo-one
cd ~/troi-of-silo-one && ./install.sh
```

The installer:

- builds the voice line's environment, plus voice ID, calls and voice activity detection;
- builds the environments for the globe and the cursor guard, and for face ID (optional);
- installs the browser bridge and the console app, and builds the console;
- renders this Mac's files from `troi-console/templates/`: the agent's boot file `CLAUDE.md`, and
  `.claude/settings.json` with the guard's hooks, vault access and denied destructive commands. It
  also renders `.mcp.json` and the components' configs, and marks the folder as trusted for Claude
  Code;
- patches the hands board with cursor control;
- loads the four background services: reminders and the morning brief, the globe, the Telegram
  bridge, and the nightly backup;
- puts **Troi** on the Desktop and a `troi` command in `~/.local/bin`;
- starts a resumable download of the larger speech model (1.5 GB) into `data/models`. The small
  model works in the meantime.

Run it again at any time: every step skips what is already done.

## Updating

```bash
cd ~/troi-of-silo-one && git pull && ./install.sh
```

Then start Troi again. The installer re-renders the per-Mac files from the templates, rebuilds the
console when its code changed, and leaves your data alone.

## Next

[Permissions](permissions.md), then [the welcome](the-welcome.md).
