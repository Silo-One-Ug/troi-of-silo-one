---
title: Eyes and screen
description: A look through the camera or at the screen when you ask, the sight modes, watch mode, and where the pictures stay.
order: 4
---

## On request

- "Look at me", "what do you see", "what am I holding": one camera photo, described briefly, as a
  friend would.
- "Look at my screen", "what's on my screen", "read this error": one screenshot, read.

The camera is never turned on by the agent itself. You do, from the console or by asking.

## Continuous, when you switch it on

Eyes in Modes (or on the Eyes page) has four modes:

- **Off.**
- **Every reply**: a fresh camera frame with each request, so it answers knowing what it can see; it
  mentions it only when it matters or you ask.
- **Watch**: when the room changes it says one short sentence, only if something is worth telling
  you (someone arrived, you are showing it something); otherwise nothing.
- **Screen**: a screenshot with every request. It needs the Screen Recording permission for
  Terminal.

Turning sight on is a protected change ([Protected settings and the
PIN](../50-safety/protected-settings-and-the-pin.md)).

## Privacy

Photos stay in `data/blobs/looks/` and screenshots in `data/blobs/screens/` (and in your private
nightly backup); after 14 days they go to the Trash unless starred. The agent never writes down
anything about the people in a picture beyond answering the question. See
[What leaves the Mac](../50-safety/what-leaves-the-mac.md).
