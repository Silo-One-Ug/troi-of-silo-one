---
title: The hands board
description: The hand-tracked glass board where the agent shows things, the Hands switch, and the gesture table for the board and the galaxies.
order: 4
---

A hand-tracked glass board runs on this Mac (`http://127.0.0.1:8794`, on the Mac only). It is the
agent's show-and-tell: when you ask to see something ("show me", "put it up", "pull up my notes on
X"), the agent finds the thing, puts it on the glass, and says what it put up. Research pictures
land here as a numbered grid under a caption card; a picture it made, a screenshot, a photo from
Telegram or a note from the vault can be presented centre stage, enlarged and spotlit.

The board has a calm dark backdrop, its camera stays off until hand tracking is on, and pictures
keep their true colours. "Switch to the hands" opens it; the agent switches to it itself before
putting something up.

## The Hands switch

The webcam is off until you ask, to save the battery. The **Hands** switch on the Eyes page, or
"hands on" to the agent, turns hand tracking on for the board and the galaxies; the **Hands** button
in the corner of the board, and the one inside a galaxy, do the same and keep the console's switch in
step. The browser asks for the camera the first time. At rest, with the camera off, the board shows
the ring: the agent's presence, turning with its state.

## Gestures

| Hand | Meaning |
| --- | --- |
| One finger (index) | The cursor. Hover a star or a card to focus it; hold still for a moment (dwell) to open it |
| A pinch (thumb and index), or index and middle fingers together | Grab and drag; a long pinch opens the menu |
| Fist | The cursor hides and anything held is dropped |
| A pinched hand rolled, on empty space | Rotate the galaxy |
| Two pinched hands apart or together | Zoom (turning them rotates, moving them up and down tilts) |
| In a peek drawer: hand up and down | Scrolls like a trackpad (small movements, repeat) |
| In a peek drawer: swipe right | Closes it |

The mouse also works as a hand on the board: move is an open hand, hold is a pinch, click is a tap.

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
