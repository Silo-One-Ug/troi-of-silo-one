---
title: Eyes
description: What the agent sees, the sight modes, Look now and Screen now, the hands switch, and face ID.
order: 7
---

The **Eyes** page shows what the agent sees: the live frame while the camera is on, or the look you
just took. **Look now** takes a photo and **Screen now** a screenshot. "Show me what you see" opens
the page by voice.

## The sight modes

The mode switch is the same as in Modes:

- **Off.** The camera stays off; the agent looks only when you ask.
- **Every reply**: a fresh camera frame with each request.
- **Watch**: it speaks up when the room changes, one short sentence, only when something is worth
  telling you.
- **Screen**: a screenshot with every request, so it answers knowing what is on your screen. Screen
  sight needs the Screen Recording permission for Terminal.

Turning sight on is a protected change. The camera is never turned on by the agent itself.

## Hands

The **Hands** switch turns hand tracking on in the galaxies (the board is driven with the mouse):
one switch for the board's camera and the galaxies' hands. The webcam is off until then, to save the
battery. "Hands on" and "hands off" do the same by voice. See [The
board](../30-views/hands-board.md).

## Face ID

**Check it's me** unlocks the console like the PIN does, once your face is learnt (Modes › Face ID ›
Learn my face). The page also shows the face controls. A photo held up to the camera can fool it; the
PIN cannot, so keep the PIN for the things that matter most. See
[Face ID and the face gate](../50-safety/face-id-and-the-face-gate.md).

## Where the pictures go

Looks land in `data/blobs/looks/` and screenshots in `data/blobs/screens/`, and in the Library. They
stay on the Mac (and in your private nightly backup); after 14 days they go to the Trash unless
starred.
