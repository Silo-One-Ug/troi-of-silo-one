# Installing Troi of Silo One

Written for someone setting Troi up on a Mac for the first time. Budget half an hour; most of it is downloads.

## 1. Before you start

1. **A Mac with Apple Silicon** (M1 or newer) on macOS 14 or newer. The speech models run on the Apple GPU through MLX; Intel Macs are not supported.
2. **Homebrew.** Paste the one-liner from [brew.sh](https://brew.sh) into Terminal.
3. **Claude Code**, signed in: [claude.com/claude-code](https://claude.com/claude-code). Run `claude` once and log in.
4. **Google Chrome** from [google.com/chrome](https://www.google.com/chrome/). The hands board and the agent's own browser need it.

The installer adds these command-line tools with Homebrew if they are missing:

| Tool | Used for |
|---|---|
| `uv` | Python environments |
| `node` | the console app and the browser bridge |
| `ffmpeg` | Telegram voice notes, meeting recordings |
| `imagesnap` | the camera |
| `cliclick` | the agent's guarded cursor |
| `gh` | the CI watch and the nightly backups (run `gh auth login` after) |
| `espeak-ng` | pronunciation for the local voice |

## 2. Install

```bash
git clone https://github.com/Silo-One-Ug/troi-of-silo-one ~/troi-of-silo-one
cd ~/troi-of-silo-one && ./install.sh
```

The installer:

- builds the voice line's environment, plus voice ID, calls and voice activity detection;
- builds the environments for the globe and the cursor guard, and for face ID (optional);
- installs the browser bridge and the console app, and builds the console;
- renders this Mac's files from `troi-console/templates/`: the agent's boot file `CLAUDE.md`, and `.claude/settings.json` with the guard's hooks, vault access and denied destructive commands. It also renders `.mcp.json` and the components' configs, and marks the folder as trusted for Claude Code;
- patches the hands board with cursor control;
- loads the four background services: reminders and the morning brief, the globe, the Telegram bridge, and the nightly backup;
- puts **Troi** on the Desktop and a `troi` command in `~/.local/bin`;
- starts a resumable download of the larger speech model (1.5 GB) into `data/models`. The small model works in the meantime.

Run it again at any time: every step skips what is already done. To update, run `git pull && ./install.sh`.

## 3. Permissions (once)

Open **System Settings › Privacy & Security** and give **Terminal** (the app that runs Troi) these:

| Permission | Needed for |
|---|---|
| Microphone | hearing you |
| Camera | "look at me", face ID, the hands board |
| Screen Recording | "what's on my screen" |
| Accessibility | the guarded cursor (it reads the label of the control under the pointer before clicking) |
| Input Monitoring | the talk key (Right Option) |

Quit and reopen Terminal after granting them. The welcome checks each one, and `troi-console/doctor.sh` shows a red cross for any still missing.

## 4. Start, and the welcome

Double-click **Troi** on the Desktop, or type `troi` in a terminal. Chrome opens the console at http://localhost:3100. The first time, it goes to the welcome:

1. **The story.** Who Troi is, in seven scenes. Use the arrow keys or the scroll wheel, or skip straight to the setup.
2. **You.** Your name, your full name, the greeting, and what Troi calls you mid-conversation.
3. **This Mac.** The machine, the permissions, a test of the talk key, and the folders Troi may organise.
4. **Memory.** A new vault in `data/vault` (git-backed; Troi interviews you to fill it in), or the vault you already have. Also where the nightly backup of Troi's record goes.
5. **Voice.** Kokoro (local and free) or ElevenLabs (your key goes to the Keychain; pick one of your voices).
6. **Your phone.** A Telegram bot token, then the pairing code you send to your bot.
7. **Security.** A PIN (kept in the Keychain), then your face and your voice.
8. **Extras.** Keys for making pictures (OpenAI or Gemini), for calls (Agora), and the GitHub org whose builds Troi watches.
9. **Ready.** Troi restarts its voice with everything you set and introduces itself.

Then hold **Right Option** and speak. Ctrl-C in the Terminal window stops everything; the background services keep running.

To run the setup again, open http://localhost:3100/welcome?step=setup. Once you have been welcomed, changes there need the console unlocked with your PIN.

## 5. Optional pieces

### Telegram (talk from your phone)

1. In Telegram, message **@BotFather**, send `/newbot`, follow the prompts and copy the token.
2. Paste it in the welcome's **Your phone** step, or run `troi-console/keychain.py set telegram` and then `python3 troi-console/setup.py services restart telegram`.
3. Send your bot the pairing code the welcome shows (it is also in `data/logs/telegram.log`). From then on only your chat is accepted.

Text, photos and voice notes work both ways. Reply "approve" or "reject" to approval requests. `/call` starts a voice call.

### Voice calls (Agora)

1. Create a free project at [console.agora.io](https://console.agora.io) with **App ID + Token** authentication. Copy the App ID and the App Certificate into the welcome's **Extras** step, or run `keychain.py set agora-appid` and `keychain.py set agora-cert`.
2. Host `troi-console/call.html` somewhere static (GitHub Pages works: a public repo with just that file), and put its URL in `data/console.json` as `call_page`. Without it, the call page is served from the console, which only works on your own network.
3. `backtalk/.venv/bin/python troi-console/agora_call.py check` says what is configured. Then say "call me": Troi sends a link on Telegram and answers.

### GitHub CI watch

Run `gh auth login`, then set the org in the welcome's **Extras** step. The pulse checks the newest run on `main` of every repo every three minutes and reports failures in the console and on Telegram.

### Backups

Both run at 23:30 and go to private repos in the `Silo-One-Ug` organization, written as the GitHub account `ayesigapaul`. They use that account's gh token whichever account is active (`github_account` and `backup_org` in `data/console.json`). Sign it in once with `gh auth login`.

- **The vault** is committed and pushed to `troi-vault` in the organization, or to the vault's own remote if it already has one (`vault_repo` in `data/console.json` sets another). The repo is created on the first run, and pushes never force.
- **Troi's record**, the database and any new files, goes as one release a night to `troi-of-silo-one-backups`, or to `backup_repo` from the welcome's **Memory** step. Starting Troi never runs a backup; Routines › Backup › Run now does.

### Folders Troi may organise

Choose them in the welcome's **This Mac** step, or list them as `file_roots` in `data/console.json` and run `python3 troi-console/setup.py render`, so the agent may read them too. Troi moves, renames and tidies only inside these folders and its vault.

### Server watch

`troi-console/servers.py add <name> <ssh-host>` adds a server (kept in `data/servers.json`). The pulse checks every server over SSH every 15 minutes.

## 6. Where things are

| Thing | Where |
|---|---|
| Your settings | `data/console.json` |
| Troi's record | `data/troi.db` (`troi-console/db.py tail`, `sessions`, `stats`) |
| Files it made or received | `data/blobs/<kind>/` |
| The vault | `data/vault/`, or the one you chose |
| Voice and face prints | `data/prints/` |
| Logs | `data/logs/`, `backtalk/logs/backtalk.log` |
| Speech models | `data/models/` |
| The agent's Chrome profile | `data/browser/` |
| Secrets | the Keychain, account `troi-of-silo-one` (`troi-console/keychain.py list`) |
| Boot file (identity, rules, abilities) | `CLAUDE.md`, rendered from `troi-console/templates/CLAUDE.md` |
| Claude Code hooks and permissions | `.claude/settings.json`, rendered from `troi-console/templates/settings.json` |
| Voice line settings | `backtalk/backtalk.json` (rendered, plus your microphone choices) |
| Background services | `~/Library/LaunchAgents/com.troi-of-silo-one.*.plist` |

## 7. Starting over

1. Stop Troi (Ctrl-C in its Terminal window) and run `python3 troi-console/setup.py services remove`.
2. Move `data/` to the Trash. It holds everything Troi kept.
3. Remove the secrets:
   ```bash
   for n in pin telegram elevenlabs openai gemini agora-appid agora-cert; do
     security delete-generic-password -a troi-of-silo-one -s "troi-of-silo-one.$n" >/dev/null 2>&1 && echo "removed $n"
   done
   ```
4. Run `./install.sh` again. The next start opens the welcome.

## Troubleshooting

Run `troi-console/doctor.sh` first. Then:

| Symptom | Fix |
|---|---|
| The console says the agent is not answering | Start Troi from the Desktop. If it is running, `lsof -nP -iTCP:8796` shows who holds the port; starting Troi again frees its own ports. |
| The talk key does nothing | Give Terminal Input Monitoring, quit and reopen Terminal, and start Troi again. |
| "Accessibility missing" | System Settings › Privacy & Security › Accessibility: add Terminal. Start Troi again. |
| Troi hears itself or the TV | Turn on the wake word and Voice ID in Modes. Learn your voice with about a minute of push-to-talk speech. |
| Garbled transcription with a Bluetooth headset | Set `mic_device` in `backtalk/backtalk.json` to the Mac's own microphone. |
| A file you asked it to trash is still there | That is the design: the request waits in Approvals. Unlock with your PIN and approve it, or approve on Telegram. |
| "Approving needs you" | Unlock the console with your PIN (or your face) on the Approvals page, or approve on Telegram. |
| The hands board shows only a ring | Chrome needs camera permission for http://127.0.0.1:8794. Reload the page. |
| The console did not build | See `data/logs/console-build.log`, then run `cd console && npm install && npm run build`. |
| The globe or the cursor complains about pyobjc | `uv pip install --python troi-console/.venv-ring/bin/python pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz pyobjc-framework-ApplicationServices` |
| Anything else | Describe it to Troi in the console. It reads the troubleshooting guide that ships with each piece. |
