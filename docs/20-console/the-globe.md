---
title: The globe
description: The small gold globe that floats over every Space, turns with the agent's state, and counts what is waiting on you.
order: 1
---

A small gold globe floats on every Space and over full-screen apps: a wireframe sphere on a tilted
axis, with an orbit ring and two satellites. It is the agent's presence when the console is not in
front of you.

- **It turns with the agent's state**: slow when idle, fast when thinking, pulsing when speaking, and
  it dims to "off" when Troi is stopped.
- **Drag it** to move it, and **double-click** it to open the console.
- **A red badge** counts what is waiting on you: approvals, plus reminders due in the next ten
  minutes (overdue ones too).
- **The menu bar T** shows or hides the globe, opens the console, or quits the globe.

The globe is one of the four background services (`ring`), so it is there whether or not Troi is
started: `python3 troi-console/setup.py services status` shows it, and `services restart ring`
brings it back if it is gone.
