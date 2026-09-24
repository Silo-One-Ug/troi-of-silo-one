---
title: What leaves the Mac
description: Photos, screenshots, prints and secrets stay. The nightly backup and the messages you send are the only things that go.
order: 6
---

| Thing | Where it stays | What leaves |
| --- | --- | --- |
| Camera looks and screenshots | `data/blobs/looks/`, `data/blobs/screens/`; the Trash after 14 days unless starred | only to your private nightly backup |
| Your voice and face prints | `data/prints/` | nothing; they never leave the Mac |
| Secrets (the PIN, the tokens, the keys) | the macOS login Keychain | nothing; the agent never writes a secret into a note, a summary or a log |
| The record | `data/troi.db` | one release a night to your private backup repository |
| The vault | `data/vault/`, or the vault you chose | a commit and push a night to its own private remote |
| Meeting recordings | `data/blobs/meetings/` | the audio goes to ElevenLabs Scribe only when you ask for a transcript |
| Pictures you ask to be made | `data/blobs/imagined/` | the prompt goes to the image backend you chose (OpenAI or Gemini) |
| Speech | the Mac (Kokoro, Whisper on the Apple GPU) | the reply text goes to ElevenLabs only when ElevenLabs is the voice |
| Messages | the record | what you send yourself on Telegram, and what the agent sends you there |

The agent's conversation runs through Claude Code, so a turn's text and the tool results it needs go
to the model as with any Claude Code session; the camera and screen frames it is handed go the same
way, which is why sight is off until you switch it on, and protected.

Reaching Troi from a phone is off by default; with Tailscale on, only your own devices can reach it
([On your phone](../20-console/on-your-phone.md)).
