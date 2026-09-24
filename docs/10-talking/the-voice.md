---
title: The voice
description: The talk key, hands-free listening, the wake word, voice ID, stopping a reply, long jobs, and the greeting.
order: 1
---

## The talk key

Hold **Right Option**, speak, release. That key is never gated by voice ID or the face gate, so it
always works.

## Hands-free

Hands-free listens all the time. With the wake word on, say the name first: "Troi, what time is
it". Words before the name are dropped, so a television in the room does not trigger it. The names
it answers to are `wake_names` in the settings (`troi`, `troy`, `troye` and `troie` out of the box).

Going hands-free is a protected change: "go hands free" goes through in your verified voice (or your
face), from an unlocked console, or with your approve on Telegram. See
[Protected settings and the PIN](../50-safety/protected-settings-and-the-pin.md).

## Voice ID

**Only me** fails closed. A clip that cannot be identified as you is dropped, whether it is too
short, too different or unreadable, and the transcript shows why, with its score. Learn your voice in
Modes › Voice ID › **Learn my voice**: about a minute of push-to-talk speech. **Strictness** is how
closely a voice must match your print: move it right if someone else gets through, left if it starts
ignoring you. Turning voice ID off, loosening it or learning again is protected.

## Stopping a reply

Say "**stop**", or press **Stop** (the square button) or **Esc** in the console. With barge-in on,
only a sentence with the agent's name interrupts.

## Long jobs

The agent says so instead of going quiet, and gives a short update if it is still busy after a
while. It ignores its own voice, so its replies do not become its requests.

## The greeting

The voice line says your greeting ("Hello Paul.", as you set it in the welcome) the moment it starts.
Once the brain is warm, it is handed a session-start line with the time, today's reminders and the
top of your priorities. It then adds what a fellow person would add: a word on the time of day or the
day ahead, a dry remark, or a small joke now and then. It is never the same line twice and it is not
scripted. Turn it off with `"living_greeting": false` in `data/console.json`.

## Movie mode

"Movie mode" switches to push to talk so the film cannot wake the agent, silences the sound cues,
hides the floating conversation and dims the page. "Movie mode off" restores it; if you were
hands-free before, say "go hands free" yourself, since that one is protected.

## If it does not hear you

- The talk key always works. If nothing happens when you hold it, Terminal needs Input Monitoring
  ([Permissions](../00-start/permissions.md)).
- In hands-free, check the wake word and voice ID switches in Modes; a dropped line shows as a faint
  "ignored" line in the conversation with the reason.
- Garbled transcription with a Bluetooth headset: set `mic_device` in `backtalk/backtalk.json` to
  the Mac's own microphone.
