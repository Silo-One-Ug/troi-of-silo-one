---
title: Telegram
description: Talk to Troi from your phone. Setting up the bot, pairing, approving from Telegram, and when Troi writes first.
order: 3
---

Text, photos and voice notes both ways, in the same session as the console.

## Setting it up

1. In Telegram, message **@BotFather**, send `/newbot`, follow the prompts and copy the token.
2. Paste it in the welcome's **Your phone** step, or run `troi-console/keychain.py set telegram` and
   then `python3 troi-console/setup.py services restart telegram`.
3. Send your bot the pairing code the welcome shows (it is also in `data/logs/telegram.log`). From
   then on only your chat is accepted; the pairing is kept in the record.

## Using it

- **Replies.** The agent answers in plain text, and adds a voice note (in Kokoro) when you sent one;
  `"voice_replies": true` in the settings sends a voice note with every reply.
- **Photos** you send arrive in the conversation and land in the Library under Telegram; voice notes
  arrive already transcribed.
- **Approvals.** Send "approve" or "reject" (or `/approve`) to decide the newest request that is
  waiting: a trash request, a force-quit, a risky click, a protected setting.
- **Calls.** `/call` starts a voice call ([Calls](calls.md)).
- **Pictures from the agent.** "Send me those" after a research session sends the pictures on the
  board to your phone; the agent can also send any file with `telegram.py photo`.

## The agent writing first

It messages you when something needs you while the voice line is down: a reminder, a failed build, a
server change, a calendar heads-up. It never sends more than one message for one event. The
end-of-day report's PDF arrives there every evening.

## The bridge

The Telegram bridge is one of the four background services, so it runs whether or not Troi is
started. `python3 troi-console/setup.py services status` shows it; `services restart telegram`
restarts it after a token change.
