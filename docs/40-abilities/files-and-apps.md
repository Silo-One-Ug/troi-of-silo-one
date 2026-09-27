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

The hands go deeper too: `zip` and `unzip` (an archive beside the thing, unpacked into a new folder
beside it), `size` (a folder and its largest children), `dupes` (duplicates found by size and a hash,
reported in groups with what the copies take; nothing removed), `recent` (what changed in the last
days), `tag` and `tags` (Finder tags, the existing ones kept) and `plan` (what would go where, by kind
or by month; nothing moves until you say so). All of it stays inside your file roots and never
overwrites: a name that exists gets " 2".

## The clipboard

"What did I just copy", "turn what I copied into a table", "put this on the clipboard": the agent
reads the clipboard on request (text, copied files as their paths, or a picture, saved under
`data/blobs/clips/`) and writes text to it. Anything that looks like a secret (a key, a token, a
password) is never shown: the agent says so and you paste it where it goes yourself. There is no
clipboard history: only what is on it now, when asked.

The same operations are on the [Files galaxy](../30-views/files-galaxy.md): drag a star onto a folder,
right-click for rename or a new folder.

## Workspaces

"Start my work setup" sets the desk in one word: the apps open, what must run is started, the pages
go up in your browser, and a sticky note carries the open priorities from the vault. A workspace is
a list of steps in `data/workspaces.json`: an app to open or quit, a page (https), a command to run
(skipped when its check already succeeds, and never anything that removes, kills, resets or forces;
those words are refused), a sticky note, one of the agent's own tools, an app to bring forward, a
line to say. Each step reports, and one failing does not stop the rest. "Start my work setup", "end
my work setup", "add opening Slack to my work setup" are the words; `workspace.py` is the tool, and
`--dry` says what a workspace would do without doing it.

## Devices

"What's connected", "is the sound going to my AirPods", "play through the speakers", "what's the
battery on my AirPods": the agent sees the displays, the sound devices and which are the defaults
for output and input, the Bluetooth devices with their batteries when they tell them, the USB
devices and the printers. It routes the sound only at your word, and "my AirPods are connected but
there's no sound" gets the diagnosis first (where the sound goes, what it could go to), then the
switch when you say so. A Bluetooth device coming or going can be a watch.

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
