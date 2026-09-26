---
title: The board
description: "The agent's show-and-tell surface: a light gray, full-width page of tiles it fills and you move with the mouse. Cards, pictures, notes from the vault, charts, tables, slideshows and video; everything stays until you clear it."
order: 4
---

The board is where the agent shows you things (`http://127.0.0.1:8794`, on the Mac only; the **Hands**
view in the console). When you ask to see something ("show me", "put it up", "pull up my notes on X"),
the agent finds the thing, puts it on the board, and says what it put up. Research pictures land as a
numbered grid with a caption; a picture it made, a screenshot, a photo from Telegram, a note from the
vault, a chart, a table or a plan can all go up, and anything can be presented centre stage, enlarged,
with the rest dimmed.

The board is a full-width page, its reading text in Inter and its labels, numbers and code in JetBrains Mono, with the content sitting on the paper: a small title
over each tile, hairlines, no boxes. Light or dark follows the system, or the console's switch when the
board is framed in it (`?theme=dark|light` forces one). It grows downward and scrolls when there is more
than a screen of it. Opened on its own, the page hands over to the console's Hands view, so the console's bar
is the one navigation everywhere.

## The mouse

- Drag a tile by its title (a picture anywhere). Tiles never land on each other: a drop onto another
  tile slides to the nearest free spot.
- Scroll inside a note or a panel with the wheel.
- Double-click a title, or a picture, to spotlight it; Esc, another double-click or a click on the paper
  ends the spotlight.
- Hover a tile for its × (put it away) and its corner grip (resize).
- Tabs, accordions, buttons and choices click. A click on a button, a choice or a checklist item
  reaches the agent as a line, so a click is an answer.
- Checkboxes tick. In a note from the vault, the tick lands in the note itself (the `[ ]` becomes
  `[x]` on that line).
- A slideshow is a carousel: drag it, use its arrows or dots, or the arrow keys when it has the focus;
  it advances by itself until the mouse rests on it.
- Videos and audio play with their own controls; YouTube and Vimeo with theirs.
- **Tidy** (top right) lines everything up in rows; **Clear** (click it twice) puts everything away.

## What lands

| Tile | How it gets there |
| --- | --- |
| A card | `board.sh '{"a":"add_card","title":"…","body":"…"}'`; with a `file`, a click on it opens the vault note |
| A picture or a video | `show-image.sh <file> [title]`, `pictures.py … --show`, or `add_img` with a file from the airlock |
| A note from the vault | `add_card` with `"file":"0/<path>.md"` and `"open":1`, or a click on the note's card |
| A panel: charts, tables, stats, a slideshow, a video, a map, a plan… | `show.py '<tree>' --board`, the same tree `show.py` draws in the conversation |
| Several at once, in a grid | `board.sh '{"a":"layout","items":[…],"caption":"…"}'` |

`show.py vocabulary` lists the components: layout (stack, row, grid, columns, card, group, tabs,
accordion, slideshow, steps, timeline, hero), text (heading, text, markdown, quote, code, badge, tags,
callout), data (stat, progress, gauge, key-values, list, table, chart, sparkline, rating, countdown,
clock, calendar), media (image, gallery, video, YouTube, Vimeo, audio, an https page, a map, avatars)
and answers (button, choice).

## Colour

The board colours its structure by itself, from the theme's tokens: section dividers and table headers
in the accent, zebra rows, accent list markers and checkboxes, a fine accent line on cards, numbers
right-aligned in tabular figures. The agent adds the tones for meaning (ok, warn, bad, note), gold for
the one thing to look at, and keeps to one accent and no more than three hues on a panel.

## Organised by itself

A new tile flows into the first free space, in reading order, and scrolls into view. `layout` places
several tiles in the cells of a grid, a row or a column, with a caption under them. `tidy`
(`show.py board tidy`, or the button) re-flows the whole board. The agent can drive a panel that is up:
a new tree in place (a live dashboard), the next slide, play or pause, scroll, move, resize, spotlight
(`show.py board "<title>" next|set|scroll|present …`).

## It stays

Whatever is up is saved to `data/board/scene.json` a second after any change and comes back when the
page reloads or the Mac restarts. `barehands/bin/board-state.sh` prints what is on the board, or the
saved scene when the page is closed; `board-state.sh events` lists the last clicks on buttons and
choices.

## The empty board

With nothing up, the board says what it is for and offers a few requests to click; a click sends the
request to the agent, as if you had typed it.

## On a phone

Under 768 px the same tiles flow as one column in reading order, full width, nothing to drag: the
page lays the column out and keeps each tile's place on the glass untouched, so the desktop finds
everything where it was. A tap on a title spotlights a tile (it scrolls into view whole, the others
fade); a tap on the title again, or on a faded tile, lets it go. The × puts a tile away; Tidy has
nothing to do in a column and is hidden. Something the agent adds while you are on the phone lands at
the bottom, and under everything on the glass.

## Files and safety

Only files inside `barehands/media/` (the airlock) can appear on the board; `show-image.sh`,
`pictures.py` and `show.py` copy files there first. Anything remote is https or refused. The board
runs on the Mac only, and it has no camera: the **Hands** switch, and the gestures below, belong to the
galaxies.

## Hand gestures (the galaxies)

The webcam is off until you ask, to save the battery. The **Hands** switch on the Eyes page, or
"hands on" to the agent, turns hand tracking on in the Files, Apps and Vault views; the **Hands**
button inside a galaxy does the same and keeps the console's switch in step. The browser asks for the
camera the first time.

| Hand | Meaning |
| --- | --- |
| One finger (index) | The cursor. Hover a star or a card to focus it; hold still for a moment (dwell) to open it |
| A pinch (thumb and index), or index and middle fingers together | Grab and drag; a long pinch opens the menu |
| Fist | The cursor hides and anything held is dropped |
| A pinched hand rolled, on empty space | Rotate the galaxy |
| Two pinched hands apart or together | Zoom (turning them rotates, moving them up and down tilts) |
| In a peek drawer: hand up and down | Scrolls like a trackpad (small movements, repeat) |
| In a peek drawer: swipe right | Closes it |

## Tuning

The galaxies' sensitivity lives in `data/console.json` under `hands` (pinch thresholds, the dwell
time, the magnet), or use `console.sh hands <key> <value>`:

| Key | Default | What it is |
| --- | --- | --- |
| `pinch_close` | 0.32 | how close thumb and index must come to count as a pinch |
| `pinch_open` | 0.48 | how far apart they must go to release |
| `ext` | 1.45 | how straight a finger must be to count as extended (pointing) |
| `dwell_ms` | 1300 | how long to hold still before a dwell opens something |
| `magnet` | 16 | how far from a star, in pixels, the cursor still catches it |

Press **P** in a galaxy to sample a pose.
