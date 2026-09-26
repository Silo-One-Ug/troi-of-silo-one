# The native hands

The agent drives every app on the Mac by name, through the accessibility tree macOS keeps for each window, from one
resident process. It does not take a screenshot to find a button and does not guess coordinates; it asks the app for
its buttons, fields, rows and menus, acts on the one it means, and reads the result back from the element itself.

Two doors to the same engine:

- **the brain**: the `mcp__hands__*` tools, served by `hands.sh mcp` (listed in the repo's `.mcp.json` as `hands`);
- **people and scripts**: `troi-console/hands.sh <command>` in a terminal.

Both run `hands.py` in `backtalk/.venv`, the Python that already has PyObjC and the accessibility permission.

## Why

The guarded cursor (`cursor.sh`) needs a screenshot, a look at it, and a click at a coordinate; with the model's turn
around each step that is 10–25 seconds per click, and the 1600-pixel screenshot does not match the 1512-point display,
so clicks landed a little off. The tree costs 45 ms to read, names every control, and says whether the press worked.

## The tools

| Tool | What it does | Returns |
|---|---|---|
| `apps` | running apps, front first | names, bundle ids, pids |
| `launch app` | opens an app (name or bundle id) and waits for its window; a running one is brought to the front | the front window's title |
| `focus app` | brings an app to the front | whether it is in front now |
| `windows [app]` | an app's windows | id, title, focused/main/minimized, frame |
| `inspect [app] [window] [--depth N] [--all]` | the front window (or a window id) as an indented tree | one line per element: `id role "label" =value state [actions] @x,y wxh` |
| `find app text [--role R]` | elements whose title, description, value, placeholder or identifier contain the text | the matching lines, best first |
| `read id` | everything about one element | role, label, value, enabled/focused/selected, actions, frame, window, attribute names |
| `press app text [--role R]` | presses the control called *text* (button, tab, checkbox, row, link, menu button…) | its state after the press and the front window |
| `set app target value` | puts a value into a field, checkbox, slider or pop-up (*target* = id or label) | the value read back |
| `perform id action` | any action the element offers: Press, Confirm, Cancel, ShowMenu, Increment, Decrement, Raise, Pick | ok |
| `menu app [path]` | no path: the menu bar; `View`: its items with ✓ marks, shortcuts and disabled state; `File > Export…`: chooses that item | the listing, or what was chosen |
| `type text` | inserts at the focused field: through the tree when the field allows it, else as keystrokes | how it went in, and the field's value |
| `key combo` | `return`, `tab`, `esc`, `space`, `delete`, arrows, `home`, `end`, `f1`–`f12`, a letter or digit, with `cmd`/`shift`/`alt`/`ctrl`: `cmd+s` | ok |
| `click x y [--double\|--right] [--screenshot\|--share]` | the pointer, for what has no name, in screen points; `--share` converts pixels of the frame the owner is sharing (`share.sh`) to the points it covers; `--screenshot` converts pixels of a `look-screen.sh` screenshot to points | what was under the point |
| `wait app text [--role R] [--timeout S]` | waits for an element to appear: a sheet's button, a window title, a status | the element, and how long it took |
| `doctor` | is the accessibility API available to this process, what is in front, how fast a look is | a line of numbers |

`app` is a name (`Finder`, `Mail`), a bundle id, a pid, or `front` for the frontmost app. Roles can be short:
`button`, `field`, `checkbox`, `radio`, `row`, `link`, `menuitem`, `tab`, `popup`, `slider`.

Element ids (`e12`) come from `inspect`, `find` and `windows`; they stay valid for the life of the process (the
brain's session) and the same element keeps the same id. An id whose element has gone says so; run `inspect` again.

### A typical turn

```
menu Finder "File > New Finder Window"        → chose File > New Finder Window
wait Finder Applications --role row           → e4 AXRow/OutlineRow "Applications" @325,331 183x32 (0.7 s)
press Finder Applications --role row          → clicked AXRow 'Applications'; front window "Applications"
press Finder "list view" --role radio         → pressed AXRadioButton 'list view'; value 1
menu Finder "File > Close Window"             → chose File > Close Window
```

Every answer carries the read-back (the value, the selection, the front window's title), so the next step needs no
screenshot. When the names are unknown, `inspect` or `find` first.

## Guards, always on

The same rules as the cursor, from the same code (`cursor.py`):

- a control whose label is risky — delete, remove, erase, trash, pay, buy, send, submit, confirm, allow, install,
  reset, format, quit, restart, log out, transfer… — is **not pressed**: an approval request is filed for the owner
  (console card + Telegram) with the control's position, so an approved request replays as a click; the tool answers
  `needs_approval` and the agent says it is waiting. The check covers every way of pressing: `press`, a menu item,
  `click`, `perform` (any action that activates something; Confirm on a window or sheet checks its default button),
  `set` on a checkbox, switch or pop-up, and a bare Return, Enter or Space: the key checks the focused control or,
  for Return and Enter, the default button of the front window or of a sheet on it, so a Return cannot confirm
  "Empty Trash". Text typed with a line break is checked the same way (a text area just takes the newline). When the
  front app shows nothing to check at all (an Electron app whose tree is off, even after switching it on), Return and
  Enter are refused rather than sent blind, with the alternative named: press the button by name, or `set` the field.
  `cursor.sh key` and `cursor.sh type` ask `hands.sh key-check` and refuse when they cannot see what the key would press;
- password fields (secure text fields, or fields whose name says password/passcode/PIN) are never written to;
- destructive shortcuts (`cmd+q`, `cmd+w`, `cmd+delete`, `cmd+alt+esc`…) are refused;
- an app that does not answer the tree within 1.5 s gets "did not answer in time", never a hang;
- every action is logged to `data/logs/hands.log`.

The agent's own rule on top: it acts on an interface only when the owner asked for that action in the conversation.

## What the tree does not reach

- **Electron and Chromium apps** (VS Code, Obsidian, Postman, Chrome, Comet, Spotify) build their tree only when an
  assistive client asks. The first touch switches it on and waits a moment; the window chrome then appears, but web
  content and VS Code's editor stay thin. Use the browser tools for web pages, `code`/files for VS Code, the vault's
  files for Obsidian.
- **WezTerm** exposes no tree at all; `wezterm cli` (`list`, `send-text`, `get-text`) is the door.
- **Terminal** exposes its whole buffer as one text area: `find Terminal --role textarea ""` then `read` gives the output.
- **Custom canvases** (games, drawing surfaces, the Chess board) need `click` and, if it must, a screenshot.

## Measured (M4, macOS 26.6.2)

- `doctor` (every app + the front window's attributes): 49 ms · a full `inspect` of a Finder window from the
  terminal, process start included: 0.33 s · the tool server is ready 0.6 s after the brain spawns it, then one call
  is one round trip · the Finder round trip above, waits included: 3.5 s.
- For comparison: `osascript` costs 170–300 ms per call warm and 4.9 s when System Events must launch; the old
  look-then-click loop 10–25 s per click.

## Setting it up

1. `troi-console/hands.sh doctor` must say `"accessibility_trusted": true`. If not: System Settings › Privacy &
   Security › Accessibility for the app that launches the agent (Terminal), then start the agent again.
2. The brain sees the tools through the repo's `.mcp.json`, which `setup.py render` writes from
   `troi-console/templates/mcp.json`; the `hands` server entry lives there. The boot file's "Your real hands" bullet
   (`templates/CLAUDE.md`) tells the agent to reach for these tools before the cursor. Both templates are protected by
   the guard (the agent cannot change its own rules), so the owner applies changes to them and runs
   `python3 troi-console/setup.py render`.
3. A running brain picks the tools up on its next session: restart the voice line in place with
   `kill -USR1 "$(cat data/cache/voice.pid)"` (about 20 s; the same conversation resumes), or start the agent again.
4. `doctor.sh` includes a line for the hands.

## Troubleshooting

- `no: X is not running` — `launch` it, or check `apps` for the exact name.
- `no: nothing called '…'` — `inspect` the app: labels are what the app calls things (`"list view"`, `"Send"`, a row's texts).
- `no: … cannot be pressed (actions: …)` — use `perform` with one of the actions listed, `set` for a field, or `click` its frame.
- `no: element e12 is gone` — the window or view changed; `inspect` again.
- `no: … did not answer in time` — the app's main thread is busy (a dialog, a hang); wait, or look with `windows`.
- Nothing in an Electron app — call `windows` once, wait a second, `inspect` again; if still nothing, the app does not expose its content (use its own door).
