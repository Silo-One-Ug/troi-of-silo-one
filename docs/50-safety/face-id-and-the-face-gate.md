---
title: Face ID and the face gate
description: Your face as a verifier beside the voice print and the PIN, and hands-free that answers only while you are at the camera.
order: 4
---

## Face ID

Face ID is another way to prove it is you, beside the voice print, the PIN and Telegram. It uses a
real face-recognition model in its own environment, and nothing leaves the Mac.

Learn your face once in Modes › Face ID › **Learn my face**: five photos, a second apart. It is a
protected change, so it needs the console unlocked or a Telegram approve; the agent never runs the
enrolment itself. From then on:

- **Check it's me** on the Eyes page unlocks the console like the PIN does.
- When someone gives a protected spoken order in a voice that does not match yours, the agent says
  "One moment, let me see you" and checks the camera before refusing.

A photo held up to the camera can fool it; the PIN cannot, so keep the PIN for the things that
matter most. `face_id_threshold` in the settings is how close a match must be.

## The face gate

The face gate (`face_gate` in the settings, or `console.sh face-gate on|off`) makes hands-free with
the wake word answer only while your face is at the camera, so the television cannot wake the agent
by name. It is checked at most every two minutes, from a camera photo under 15 seconds old or a
fresh one. It needs a learnt face, it fails closed, the talk key always works, and turning it off is
protected.
