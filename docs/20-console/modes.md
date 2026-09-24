---
title: Modes
description: Every switch in one place, which ones are protected, and what each option means.
order: 3
---

Every switch, in one place. A protected choice needs the console unlocked: for Auto-approve and
Hands-free, the page asks you to unlock and pick again; the other protected switches are filed for
your approval on Telegram when the console is locked.

| Switch | Options |
| --- | --- |
| Permissions | **Ask first** / **Auto-approve** (two clicks to confirm; protected) |
| Microphone | **Push to talk** (hold Right Option) / **Hands-free** (protected) |
| Wake word | In hands-free, only sentences containing the agent's name are acted on (turning it off is protected) |
| Model | **Fast** / **Deep** (Deep lasts for this session) |
| Effort | **Low** to **Max**; saved as the default |
| Eyes | **Off** / **Every reply** / **Watch** / **Screen** (turning sight on is protected) |
| Voice ID | **Off** / **Only me** / **Learn my voice** (about a minute of push-to-talk speech; off and learn are protected) |
| Strictness | How closely a voice must match your voice print. Right if someone else gets through, left if it starts ignoring you (looser is protected) |
| Face ID | **Learn my face**: five photos, a second apart (protected) |
| Voice | **Kokoro** / **ElevenLabs**, and which of your ElevenLabs voices |
| Your phone | **This Mac only** / **Tailscale** / **This network**: where the agent answers from Troi's next start (widening it is protected) |

## Permissions and the model

**Ask first** makes the agent ask before it acts; **Auto-approve** lets it run without asking. The
guard does not depend on this switch: deletions, force-quits, risky clicks and protected changes need
you in either mode ([The guard](../50-safety/the-guard.md)).

**Deep** picks the larger model for this session and goes back to **Fast** at the next start.
**Effort** is how hard the model thinks per turn; Max is thorough and slow, Low is quick.

## Eyes

**Every reply** takes a fresh camera frame with each request; **Watch** speaks up when the room
changes; **Screen** reads a screenshot with every request. See [Eyes](eyes.md).

## Your phone

Where the agent's server answers, from Troi's next start:

- **This Mac only** (the default): nothing beyond this Mac.
- **Tailscale**: your own devices, from anywhere, over [Tailscale](https://tailscale.com); every
  other network is turned away. The option appears when Tailscale is installed on the Mac.
- **This network**: any phone on this Wi-Fi. Only on a network you trust.

See [On your phone](on-your-phone.md) for the steps.

## The same switches by voice

"Push to talk mode", "go hands free", "start asking again", "stop asking for permission", "switch to
the deep model", "back to the fast model", "set effort to high": the agent sends the phrase to the
voice line once it is idle. The protected ones go through only in your verified voice, from an
unlocked console, or with your approve on Telegram.
