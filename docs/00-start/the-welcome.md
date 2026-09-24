---
title: The welcome
description: The story, then the setup step by step. What is needed, what can wait, and how to run it again.
order: 4
---

The first time the console opens, it goes to `/welcome`: who Troi is, then the setup one step at a
time. Your name and a memory are needed; everything else can wait. Until you finish, Troi hears but
does not answer.

## The story

Who Troi is, in seven scenes: it listens, it sees when you ask, it works, it remembers, it asks
first, and five minutes of setup. Use the arrow keys or the scroll wheel, or skip straight to the
setup.

## The setup

1. **You.** Your name (Troi greets you by the first word of it), and what it calls you
   mid-conversation: "sir", "boss", your first name, or a word of your own.
2. **This Mac.** The machine, the permissions, a test of the talk key (it shows the words it heard),
   and the folders Troi may organise (its file roots).
3. **Memory.** A new vault in `data/vault` (git-backed; Troi interviews you to fill it in), or the
   vault you already have. Also where the nightly backup of Troi's record goes: the GitHub account and
   organization it will write as.
4. **Voice.** Kokoro (local and free) or ElevenLabs (your key goes to the Keychain; pick one of your
   voices).
5. **Your phone.** A Telegram bot token, then the pairing code you send to your bot.
6. **Security.** A PIN (kept in the Keychain), then your face and your voice.
7. **Extras.** Keys for making pictures (OpenAI or Gemini) and for calls (Agora). The GitHub builds
   Troi watches are set later, in Routines.
8. **Ready.** Troi restarts its voice with everything you set and introduces itself.

Then hold **Right Option** and speak.

## Running it again

Open `http://localhost:3100/welcome?step=setup`. Once you have been welcomed, changes there need the
console unlocked with your PIN, like any protected change. Every step can also be done later from
Modes or from a terminal:

| Step | Later |
| --- | --- |
| Voice | Modes › Voice, or `troi-console/keychain.py set elevenlabs` |
| Your phone | `troi-console/keychain.py set telegram`, then `python3 troi-console/setup.py services restart telegram` |
| Security | `troi-console/keychain.py set pin`; Modes › Voice ID › Learn my voice; Modes › Face ID › Learn my face |
| Extras | `troi-console/keychain.py set openai`, `gemini`, `agora-appid`, `agora-cert` |
| The CI watch | Routines › **CI watch**: the GitHub orgs and users to follow, as many as you like |
| Folders | `file_roots` in `data/console.json`, then `python3 troi-console/setup.py render` |

See [Secrets](../70-reference/secrets.md) and [Settings](../70-reference/settings.md).
