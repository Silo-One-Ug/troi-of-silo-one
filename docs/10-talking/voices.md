---
title: The voices
description: Kokoro, local and free, or ElevenLabs with one of your own voices. How to switch, and what happens when one cannot answer.
order: 2
---

Kokoro speaks by default, local and free. **ElevenLabs** is the premium voice.

## ElevenLabs

1. Keep your key in the Keychain: the welcome's Voice step does it, or
   `troi-console/keychain.py set elevenlabs`.
2. In **Modes**, the Voice switch then offers ElevenLabs, with an **ElevenLabs voice** picker (and a
   reload button) listing your voices. Picking one switches to it at once. With no pick, your own
   cloned voice comes first, else the first listed.

From a terminal, or by asking the agent:

```bash
troi-console/console.sh voice list
troi-console/console.sh voice elevenlabs "Rachel"
troi-console/console.sh voice kokoro
```

The change applies from the next reply, and Kokoro takes over the moment ElevenLabs cannot answer.
The same key powers meeting transcription (ElevenLabs Scribe) and the sound cues were made with
ElevenLabs sound effects.

## Where the voice is heard

- In the room, through the Mac's speakers.
- On Telegram, as a voice note when you sent one, or with every reply when `"voice_replies": true`
  is in the settings. Voice notes are made with Kokoro.
- On a call, in Kokoro.

## Music while it speaks

With `duck_music` on in the settings, Apple Music dips while the agent speaks and comes back after.
