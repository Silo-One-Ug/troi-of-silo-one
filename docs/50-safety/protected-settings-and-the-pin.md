---
title: Protected settings and the PIN
description: Which changes need you, the four ways to prove it is you, the PIN and its 15-minute unlock, and what happens until something can verify you.
order: 3
---

Some switches lower the agent's guard. Anyone in the room could otherwise say "go hands free" or
"stop asking for permission", so each needs you.

## What is protected

- **Spoken or typed phrases**: auto-approve ("stop asking for permission"), hands-free listening
  ("go hands free") and clearing the session. They go through in your verified voice. If the voice
  does not match and your face is learnt, the camera gets a look before the order is refused. They
  also go through from an unlocked console, or with your approve on Telegram.
- **Settings**: voice ID off, looser or learning; the wake word off; the camera or screen sight on;
  learning a face; the face gate off; reaching Troi from the network or over Tailscale; and the guard
  itself. They change only from an unlocked console or with your approve on Telegram.

## Unlocking

Set a PIN once (the welcome's Security step does it, or `troi-console/keychain.py set pin`), then
type it at the lock in the bar, or use **Check it's me** on the Eyes page. The console stays
unlocked for 15 minutes: protected switches apply straight away, and approvals go through. Five
wrong PINs lock the console for ten minutes. The PIN lives in the Keychain and is never shown.

## The four verifiers

| Verifier | Used for | Note |
| --- | --- | --- |
| The PIN | unlocking the console | cannot be fooled by a photo; keep it for the things that matter most |
| Your face | unlocking the console; a second look when a spoken order's voice does not match | a photo held to the camera can fool it |
| Your voice | spoken protected orders | fails closed: an unreadable clip is dropped |
| Your Telegram chat | approving any request from your phone | only the paired chat is accepted |

## What arrives another way

Anything protected that arrives another way, including the agent being talked into it, becomes an
approval card and a Telegram message. The guard on settings is on by default (`guard_settings` in
the settings), and turning it off is itself protected.

Until something can verify you (a PIN, a paired phone, or a voice or face print), the guard stands
down and changes apply directly; the doctor warns about it. Set a PIN in the welcome and the guard
stands up.
