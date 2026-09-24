---
title: Settings
description: Every key in data/console.json, what writes it, and the voice line's own file.
order: 3
---

`data/console.json` holds your settings. The welcome and the Modes page write it; a few keys are
only ever set by hand. The agent cannot write the file (it is among the guard's safeguards); its
switches go through the server, which guards the protected ones. After editing keys the agent's boot
file uses (`file_roots`, `vault`), run `python3 troi-console/setup.py render`.

## You

| Key | What it is |
| --- | --- |
| `owner` | Your first name, the one the agent greets you by |
| `owner_full` | Your full name |
| `address` | How it greets you ("Hello `<address>`.") |
| `call` | What it calls you mid-conversation ("sir", "boss", your name) |
| `welcomed` | Whether the welcome has been finished |

## Memory and files

| Key | What it is |
| --- | --- |
| `vault` | The path of the vault |
| `file_roots` | The folders the agent may read and organise |
| `projects` | Named projects for coding sessions (`code.sh`) |
| `projects_root` | A folder whose subfolders are projects by name |

## Listening and sight

| Key | Default | What it is |
| --- | --- | --- |
| `wake_word` | `true` | Hands-free acts only on sentences with the agent's name |
| `wake_names` | `troi`, `troy`, `troye`, `troie` | The spellings the transcriber may produce for the name |
| `voice_id` | `off` | `off`, `on` (only you) or `learn` |
| `voice_id_threshold` | `0.78` | How closely a voice must match your print (the Strictness slider) |
| `face_id_threshold` | | How close a face match must be |
| `face_gate` | `false` | Hands-free with the wake word answers only while your face is at the camera |
| `eyes` | `off` | `off`, `every`, `watch` or `screen` |
| `hands` | `pinch_close` 0.32, `pinch_open` 0.48, `ext` 1.45, `dwell_ms` 1300, `magnet` 16 | Hand-tracking sensitivity |
| `guard_settings` | `true` | The guard on protected settings (turning it off is protected) |

## Voice and sound

| Key | Default | What it is |
| --- | --- | --- |
| `tts` | `kokoro` | `kokoro` or `elevenlabs` |
| `elevenlabs_voice` | | The ElevenLabs voice id |
| `living_greeting` | `true` | The one-line remark after the greeting at session start |
| `cues` | `true` | The interface sound cues |
| `duck_music` | | Apple Music dips while the agent speaks |
| `voice_replies` | | A voice note with every Telegram reply |

## The clock

| Key | Default | What it is |
| --- | --- | --- |
| `brief_time`, `brief_enabled` | `08:00`, on | The morning brief |
| `report_time`, `report_enabled` | `18:30`, on | The end-of-day report |

## GitHub and servers

| Key | What it is |
| --- | --- |
| `github_orgs` | The GitHub orgs and users whose builds the pulse watches, set under Routines › CI watch (`github_org`, the old single one, still counts) |
| `github_account` | The account the backups are written as |
| `backup_org` | The organization the backup repositories live under |
| `backup_repo` | The repository for the record's nightly release (default `troi-of-silo-one-backups`) |
| `vault_repo` | The repository a vault without a remote is pushed to (default `troi-vault`) |

## The phone

| Key | Default | What it is |
| --- | --- | --- |
| `lan` | `false` | Where the agent's server answers from its next start: `false` (this Mac only), `"tailscale"` (your own devices over Tailscale) or `true` (this network). Widening it is protected |
| `call_page` | | The https address of `call.html`, for voice calls |

## The voice line's own file

`backtalk/backtalk.json` is rendered by `setup.py render` and keeps your microphone choices:
`mic_device` (set it to the Mac's own microphone if a Bluetooth headset garbles transcription) and
`voice` (the Kokoro voice, `bm_lewis` by default).
