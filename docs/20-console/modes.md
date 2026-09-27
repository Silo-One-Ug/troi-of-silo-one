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
| Brain | the models by name, for this session, drawn from the voice line's `models` map (name to model id in `backtalk/backtalk.json`, the one list); the switch shows the brain the session runs on, as the voice line reports it |
| Effort | **Low** to **Max**; saved as the default |
| Eyes | **Off** / **Every reply** / **Watch** / **Screen** (turning sight on is protected) |
| Voice ID | **Off** / **Only me** / **Learn my voice** (about a minute of push-to-talk speech; off and learn are protected) |
| Strictness | How closely a voice must match your voice print. Right if someone else gets through, left if it starts ignoring you (looser is protected) |
| Face ID | **Learn my face**: five photos, a second apart (protected) |
| Voice | **Kokoro** / **ElevenLabs**, and which of your ElevenLabs voices |
| Speech | **Aloud** / **Text only**: with Text only the agent answers on the page and nothing is spoken, so no ElevenLabs credit is used |
| Mood | **Off** or a soundscape from the Mac while you work (Focus, Calm, Café, Forest, Night, Storm, Fire, Hum, and your own), with its volume; a mood's loop is made once with ElevenLabs |
| Power | **Auto** / **Full** / **Saver**: how much of the battery the page may spend; Auto follows the battery (this device only) |
| Your phone | **This Mac only** / **Tailscale** / **This network**: where the agent answers from Troi's next start (widening it is protected) |

## Permissions and the model

**Ask first** makes the agent ask before it acts; **Auto-approve** lets it run without asking. The
guard does not depend on this switch: deletions, force-quits, risky clicks and protected changes need
you in either mode ([The guard](../50-safety/the-guard.md)).

**Brain** picks a model by name for this session (`switch to fable` is the phrase behind it). The
names come from one place, the `models` map in the voice line's config: add a model there and it
appears here, in the phrases and in `brain.sh`. The switch shows the brain the session runs on, as
the voice line itself reports it, so a switch made by voice, by the agent or from your phone shows
here too; until the line has reported, it shows the launch default. The next start returns to the
fast model; "switch to the deep model" means the configured deep one. **Effort** is how hard the
model thinks per turn; Max is thorough and slow, Low is quick.

The agent pulls these two levers by itself for heavy work (code changes, reviews, research reports,
long reads, server operations): it says so in a line, switches to the deep brain (Fable) or a named
one at a higher effort between turns, continues the task there, and comes back to the fast model and
the resting effort when the piece is done (`brain.sh`; the resting effort is medium unless you set
another with `brain.sh rest <level>`). The switches show here as they happen.

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

## Speech

**Text only** keeps the voice quiet: every answer still lands in the conversation, on Telegram and
on the board as before, but nothing is synthesised or played, and the ElevenLabs balance is
untouched. Fillers and the greeting stay quiet too. **Aloud** brings the voice back from the next
line. By voice or from a terminal: `console.sh speak on|off|toggle|status`. The agent switches it
itself on your word ("text only", "go quiet", "speak", "aloud"), before it answers, so the reply
follows the new setting.

## ElevenLabs credits

Under the ElevenLabs voice, a meter of your allowance: what is left of the month's characters, the
tier and the reset date, amber under a quarter, red under a tenth. The agent's server holds the key
and asks ElevenLabs at most every five minutes; the page refreshes every minute while it is open.
One credit is one character spoken; a 30-second sound loop for Mood is about 1,200. Out loud, "how
much voice credit is left" gets the same numbers (`credits.sh`).

## Keys

The third card keeps the secrets the welcome asked for, in the Mac's Keychain and never in a file:
the ElevenLabs API key (the voice), the Telegram bot token (your phone), the OpenAI and Gemini keys
(pictures), the Agora app id and certificate (phone calls), and the PIN. Each has a badge (**kept**
or **not set**), a field, and **Keep**. Add a key here later, or replace one: a key already kept is
replaced only from an unlocked console (the lock in the bar). A new Telegram token wakes the bridge;
a new ElevenLabs key reloads the voices.

## Sounds

While the agent works, the console plays a soft pad from the browser, a low warm chord under a slow
filter with a breath of wind, and a small chime the moment the work is done and the answer is on its
way. It is made in the browser, with no files, and it is on by default; **Sounds** in Modes (or in
More on a phone) turns it off, for that device only. A browser plays nothing before the first click
or key on a page, so the first stretch of work after a fresh page is silent until you touch it.

**Mood** is the other kind of sound: a soundscape from the Mac itself while you work (Focus is
rain on a window, Calm the sea, Café, Forest, Night, Storm, Fire, Hum), with its own volume slider.
The first time you pick a mood the agent has ElevenLabs make its 30-second seamless loop (about
1,200 credits, once, from the same allowance as the voice); after that the loop is kept and costs
nothing. It dips while the agent speaks and comes back after. By voice: "play rain sounds",
"something calm", "sounds off". Your own moods: `sounds.py add <mood> "<what it sounds like>"`.
Music itself stays with Apple Music ("play some jazz").

## Power

The page spends battery in two places: the planet (a WebGL scene drawn at every screen refresh) and
the polls of the agent's server (one feed of `/state` for the whole page, paced by what is
happening: brisk while the agent speaks or works, a walk when idle, a stroll when the tab is hidden;
the transcript the same). **Power** picks how much of it the page may spend:

- **Auto** (the default): Saver while the device is discharging, Full when it is plugged in or when
  the browser cannot say (Chrome knows; Safari does not; the ring tells its own pane).
- **Full**: the planet at the screen's rate, with its glow.
- **Saver**: the planet at a few frames a second, one pixel per point, no glow, and the server asked
  less often when nothing is happening.

A hidden tab draws nothing at all, in every mode. The setting is this device's (the browser's
storage). The ring's globe follows the Mac's power on its own: fewer frames at idle, fewer still on
battery, the full rate while the agent speaks or works.

## Stances

A stance is several switches and a way of working, taken in one word: "developer mode" (the deep
brain at high effort, text only, quiet hours, the focus sound), "researcher mode" (the deep brain,
the board in front, the calm sound), "guardian mode" (watching and reporting, nothing held),
"maintenance mode" (the machine, the disk, the plan before any move), "scheduler mode" (the
calendar, the priorities, the reminders), "focus mode" (speak only when spoken to, the action items
held) and "meeting mode" (text only, sounds off, held). "Mode off" puts back whatever the stance
changed. A stance pulls only the switches that need no verification; the microphone and the
permissions stay where they are. The stances are in `data/modes.json`, yours to change by asking;
`mode.py` is the tool.
