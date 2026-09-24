---
title: Calls
description: A voice call from your phone, through Agora. What it needs, and why the call page must be on https.
order: 4
---

"Call me" or `/call` on Telegram sends a link. Open it on your phone, tap to allow the microphone (or
switch to push to talk), and talk. The agent answers in Kokoro and stays in the same conversation;
with a voice print it listens for your voice (it lets short clips through). Hang up to end. On a call
the agent keeps to one or two sentences a turn.

## Setting it up

1. Create a free project at [console.agora.io](https://console.agora.io) with **App ID + Token**
   authentication. Copy the App ID and the App Certificate into the welcome's **Extras** step, or run
   `troi-console/keychain.py set agora-appid` and `troi-console/keychain.py set agora-cert`.
2. Host `console/public/call.html` on an https address (any static host works, such as GitHub Pages
   on a public repo holding just that file), and put its URL in `data/console.json` as `call_page`.
3. `backtalk/.venv/bin/python troi-console/agora_call.py check` says what is configured.

## Why https

A phone allows its microphone only on an https page. Without `call_page`, the console serves the page
on your own network at `http://<this Mac>:3100/call.html`, but phones refuse the microphone there, so
the agent says it cannot call. The Telegram and console channels do not have this limit.
