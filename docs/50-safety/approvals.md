---
title: Approvals
description: What needs your approval, how to give it, what waits across a restart, and what expires.
order: 2
---

## What needs you

| Request | Filed when | Approved, it |
| --- | --- | --- |
| Trash | you ask for a file or folder to be removed | goes to the macOS Trash |
| Force quit | an app must be killed rather than asked to quit | quits the app |
| Risky click | the native hands or the cursor meet a control labelled delete, pay, send, submit, install, reset, quit and the like | replays as a click at the control's position |
| Protected setting | a protected switch is changed from a locked console, by a voice that is not yours, or by the agent | applies the setting |
| A site's go-ahead | the browser would pay, delete or send from a site | happens only with your explicit word in the same turn; nothing is filed |

## How to approve

- **The console, unlocked**: your PIN at the lock in the bar, or **Check it's me** on the Eyes
  page, then the card on the Approvals page. The console stays unlocked for 15 minutes.
- **Telegram**: "approve" or "reject" (or `/approve`) decides the newest request that is waiting.
- **Rejecting** never needs the console unlocked.

You are told where a request is waiting: a card, a badge on the globe and on the bar, a
notification, a sound cue, and a Telegram message.

## Waiting and expiring

Requests wait across a restart. Risky clicks expire, because the screen has moved on and the
position would no longer mean the same control. Earlier decisions stay listed on the Approvals page
and in the record.

## Who cannot approve

The agent. Its request is filed through the server, and the approve and unlock endpoints are among
the safeguards the guard keeps from it. Someone at your console who does not know the PIN cannot
either, nor can a voice that is not yours: the request simply waits.
