---
title: Files and apps
description: Organising files inside your file roots, opening and quitting applications, and the requests that wait for you.
order: 1
---

## Your file roots

Troi reads and organises only inside the folders you gave it: the file roots chosen in the welcome's
**This Mac** step (or `file_roots` in `data/console.json`, followed by `python3 troi-console/setup.py
render`, so the agent may read them too), plus its vault. A disk that is not mounted is simply
missing, and the agent says so.

## Organising files

"Move X into Y", "rename this", "make a folder", "copy it to the Desktop", "show it in Finder",
"open it in Preview": done directly, through `fs.sh` (`move`, `rename`, `copy`, `mkdir`, `reveal`,
`open [app]`, `undo`). These never overwrite and log to `data/logs/fs.log`. When asked to organise a
folder, the agent proposes the plan first (what moves where), then does the moves, and puts anything
unwanted in a trash request rather than deleting it.

The same operations are on the [Files galaxy](../30-views/files-galaxy.md): drag a star onto a folder,
right-click for rename or a new folder.

## Removing anything

"Delete X", "trash X", "get rid of it": the agent files a request (`fs.sh trash <path> "why"`) and
tells you it is waiting. Nothing moves until you approve it, with the console unlocked or "approve"
on Telegram, and then it goes to the macOS Trash, where you can still recover it. The agent never
performs a removal itself and never looks for a way around the guard
([The guard](../50-safety/the-guard.md)).

## Applications

"Open Spotify", "close Chrome", "bring Mail to the front", "what's running": `apps.sh` lists, opens,
focuses and quits apps. A quit is polite; the app may ask you to save. **Force quit** only files a
request for your approval, like the Trash. The [Apps galaxy](../30-views/apps-galaxy.md) shows every
app as a star.

## Pressing things inside an app

Buttons, menus, fields and rows inside an app are the [native hands](native-hands.md): "click the
Save button", "open the View menu and switch to list", "type hello in that field".
