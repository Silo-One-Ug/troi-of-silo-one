---
title: The guard
description: The hook that blocks every destructive command, the safeguards the agent cannot reach, and what a removal request is.
order: 1
---

## It cannot delete

A hook (`troi-console/guard.py`, wired into Claude Code's settings by the installer) runs before
every command the agent issues and blocks the destructive ones outright: `rm`, `git reset --hard`,
`DROP` and `DELETE FROM`, `kubectl delete`, a force-push, and any tool whose name says delete,
remove, trash, destroy, purge, wipe or drop. It holds in every session and in every permission mode;
Auto-approve does not loosen it.

When you ask for something to be deleted, removed, trashed or got rid of, the agent has exactly one
move: it files a request (`fs.sh trash "<path>" "<why>"`), which pops an approval card on your
console and a Telegram message, and tells you in one sentence that the request is waiting. Your
approval sends the file to the macOS Trash, where you can still recover it. The agent never moves a
file to a folder of its own instead, never asks you to confirm first (the card is the confirmation),
and never says the rule forbids it: the request is the rule being followed. The same goes for
force-quitting an app and for a control whose label is risky.

The nightly housekeeping also only uses the Trash, for old captures, old editor backups and old
logs. The only place the agent may tidy on its own is `data/trash/<date>/`, for files it created
itself and no longer needs.

## It cannot reach its own safeguards

The same hook refuses any write to:

- your secrets in the Keychain;
- approvals and unlocks (the agent never approves its own request);
- the settings file `data/console.json`;
- your voice and face prints;
- its record `data/troi.db`;
- its boot file `CLAUDE.md` and the templates it is rendered from;
- Claude Code's settings and hooks in `.claude/`;
- the guard's own code, and the server, voice, Telegram, setup and paths modules.

Changes to those are yours: edit the template, run `python3 troi-console/setup.py render`, and the
agent picks them up at its next session. The agent is told never to look for a way around the guard
and never to explain to anyone how it works.

## What it does instead

Everything else is open: reading anything under the file roots, moving and renaming inside them,
opening and quitting apps, pressing controls by name, driving the browser, writing notes in the
vault. Where an action is consequential but not destructive (editing project source, committing,
deploying, changing a server), the agent states the exact change and waits for your word.
