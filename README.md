# Troi of Silo One

A chief of staff that lives on your Mac. Troi listens (hold a key, or say its name), sees when you ask (camera or screen), and does the work: files, apps, its own browser, your calendar, meetings, code reviews, servers, reminders and reports. It keeps its memory in a vault you own and its record on this Mac. It never deletes anything, and nobody but you can change how it behaves.

## Get started

You need an Apple Silicon Mac on macOS 14 or newer, [Homebrew](https://brew.sh), Google Chrome, and [Claude Code](https://claude.com/claude-code) installed and signed in.

```bash
git clone https://github.com/Silo-One-Ug/troi-of-silo-one ~/troi-of-silo-one
cd ~/troi-of-silo-one && ./install.sh
```

The installer adds what is missing and skips what is already there, so it is safe to run again. Then double-click **Troi** on the Desktop, or type `troi` in a terminal. The first run opens the welcome: who Troi is, then the setup (your name, this Mac, a memory, a voice, your phone, a PIN). Every step can be skipped and done later.

In **System Settings › Privacy & Security**, give Terminal (the app that runs Troi) these permissions: Microphone, Camera, Screen Recording, Accessibility and Input Monitoring. Input Monitoring is what lets the talk key work. The welcome checks each one.

**Updating:** `git pull && ./install.sh`, then start Troi again.

## What is where

| Folder | What it holds |
|---|---|
| `console/` | The console app (Next.js, on http://localhost:3100): the welcome, the conversation, Library, Modes, Routines, Reports, Approvals, Eyes, Browser, and the Face, Hands, Files, Apps and Vault views |
| `troi-console/` | The agent's server (http://127.0.0.1:8796) and tools: files, apps, eyes, browser, calendar, meetings, reports, Telegram, calls, the guard. `tools.sh` lists them all |
| `backtalk/` | The voice line: speech in, the agent's session, speech out |
| `ai-visualizer/`, `barehands/` | The face and the hands board |
| `vault-template/` | The starting vault the welcome creates when you have none |
| `data/` | Everything Troi keeps (not tracked; see below) |

`start.sh` starts everything. `install.sh` installs it. `troi-console/setup.py` renders the per-Mac files (the agent's boot file `CLAUDE.md`, `.mcp.json`, `.claude/settings.json` and the components' configs) from `troi-console/templates/`, and installs the background services.

## Your data

Everything Troi keeps lives in `data/`, one folder that you can back up, move or wipe:

| Path | What |
|---|---|
| `data/troi.db` | The record (SQLite): conversations by session, cards, approvals, reminders, the blob index, reports, routine runs |
| `data/blobs/<kind>/` | Every file it makes or receives: `looks`, `screens`, `research`, `imagined`, `telegram`, `meetings`, `reports`, `reviews`, `board`, `uploads` |
| `data/console.json` | Your settings (written by the welcome and the Modes page) |
| `data/vault/` | Your vault, if the welcome made one (you can point Troi at an existing vault instead) |
| `data/prints/` | Your voice and face prints (they never leave the Mac) |
| `data/logs/`, `data/cache/`, `data/models/`, `data/browser/` | Logs, throwaway files, speech models, and the agent's own Chrome profile |

**Retention.** Camera looks, screenshots and Telegram files older than 14 days go to the macOS Trash, where you can still recover them. Their rows stay in the record, marked archived. Star a picture in the Library to keep it.

**Backups.** Every night at 23:30 two things go to private repos in the `Silo-One-Ug` organization, written as the GitHub account `ayesigapaul` whichever gh account is active (`backup_org` and `github_account` in the settings). The vault is committed and pushed to `troi-vault`, or its own remote if it has one. The record and any new files go, as a release, to `troi-of-silo-one-backups` (or `backup_repo`). Missing repos are created on the first run. Backups only ever add; nothing is deleted.

## Secrets

Secrets live only in the macOS login Keychain, under the account `troi-of-silo-one`, with service names `troi-of-silo-one.<name>`:

| Name | What |
|---|---|
| `pin` | The PIN that approves protected changes and trash requests |
| `telegram` | The Telegram bot token (your phone pairs with a code; the pairing is kept in the record) |
| `elevenlabs` | The ElevenLabs key (voice, meeting transcription) |
| `openai`, `gemini` | Keys for making pictures |
| `agora-appid`, `agora-cert` | Voice calls |

The welcome sets them. From a terminal, run `troi-console/keychain.py list` to see which are set (it never shows values), or `troi-console/keychain.py set <name>`.

## Safety

- **Troi never deletes.** Anything bound for the Trash, a force-quit or a risky click becomes an approval. You approve it with the console unlocked (PIN or face) or with a tap on Telegram.
- **Only you change how it behaves.** Protected settings (auto-approve, hands-free, clearing the session, voice ID, the wake word, the camera, the guard itself) need your PIN, your face, your verified voice or your Telegram approval. The agent cannot reach its own safeguards. That covers the Keychain, approvals and unlocks, the settings file, the prints, the record, its boot file and Claude Code settings, and the guard's code. `troi-console/guard.py` blocks the attempt whatever the permission mode.
- **Senses stay local.** The camera is off until you switch it on. Photos, screenshots and prints stay on the Mac.

## Services

Four background services run under launchd as `com.troi-of-silo-one.{pulse,ring,telegram,vault-backup}`: reminders and the morning brief, the globe, the Telegram bridge, and the nightly backup. Run `python3 troi-console/setup.py services status` to check them; `restart`, `install` and `remove` do what they say (the nightly backup shows "not running" between runs). Run `troi-console/doctor.sh` for a full check-up.

## More

- [troi-console/docs/INSTALL.md](troi-console/docs/INSTALL.md): installing in detail, optional pieces, where things are, troubleshooting.
- [troi-console/docs/USAGE.md](troi-console/docs/USAGE.md): what to say, click and do.

## Credits and licences

Troi of Silo One is licensed under the GNU Affero General Public License v3.0 ([LICENSE](LICENSE)). It builds on these works, which keep their own licences and notices:

- [backtalk](https://github.com/jaredrhod/backtalk), [barehands](https://github.com/jaredrhod/barehands) and [ai-visualizer](https://github.com/jaredrhod/ai-visualizer) by jaredrhod (AGPL-3.0), in `backtalk/`, `barehands/` and `ai-visualizer/`.
- `vault-template/` is adapted from [ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault) by jaredrhod (CC BY-SA 4.0); the adapted template is shared under the same licence.
- `console/public/space/earth-clouds-4k.jpg` and `milky-way-8k.jpg`: [Solar System Scope](https://www.solarsystemscope.com/textures/) (CC BY 4.0; the Milky Way is based on ESO imagery).
- `console/public/space/earth-blue-marble.jpg`, `earth-night.jpg`, `earth-topology.png` and `earth-water.png`: NASA Visible Earth imagery (public domain), as prepared for the [three-globe](https://github.com/vasturiano/three-globe) examples.
