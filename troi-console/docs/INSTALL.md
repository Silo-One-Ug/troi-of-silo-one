# Installing Troi of Silo One

Written for someone setting Troi up on a Mac for the first time. Budget half an hour; most of it is downloads.

## 1. Before you start

1. **A Mac with Apple Silicon** (M1 or newer) on macOS 14 or newer. The speech models run on the Apple GPU through MLX; Intel Macs are not supported.
2. **Homebrew.** Paste the one-liner from [brew.sh](https://brew.sh) into Terminal.
3. **Claude Code**, signed in: [claude.com/claude-code](https://claude.com/claude-code). Run `claude` once and log in.
4. **Google Chrome** from [google.com/chrome](https://www.google.com/chrome/). The hands board and the page tools that run without a window need it, and without Arc it is the agent's own browser. If **Arc** is installed, Arc becomes the browser the agent drives, and yours at the same time (Arc runs one instance only): the agent starts it with its debugging port, and asks it to quit and come back, tabs and spaces intact, if you opened it from the Dock first.

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
| Camera | "look at me", face ID, the face gate |
| Screen Recording | "what's on my screen" |
| Accessibility | the guarded cursor (it reads the label of the control under the pointer before clicking) |
| Input Monitoring | the talk key (Right Option) |

Quit and reopen Terminal after granting them. The welcome checks Screen Recording, Accessibility and the talk key, and `troi-console/doctor.sh` checks Accessibility and Screen Recording. macOS asks for the camera and the microphone the first time Troi uses them. Hand tracking on the board and in the galaxies runs in Chrome, which asks for its own camera permission.

## 4. Start, and the welcome

Double-click **Troi** on the Desktop, or type `troi` in a terminal. The agent's browser (Arc, or Chrome) opens the console at http://localhost:3100. The first time, it goes to the welcome:

1. **The story.** Who Troi is, in seven scenes. Use the arrow keys or the scroll wheel, or skip straight to the setup.
2. **You.** Your name (Troi greets you by the first word of it), and what it calls you mid-conversation.
3. **This Mac.** The machine, the permissions, a test of the talk key, and the folders Troi may organise.
4. **Memory.** A new vault in `data/vault` (git-backed; Troi interviews you to fill it in), or the vault you already have. Also where the nightly backup of Troi's record goes.
5. **Voice.** Kokoro (local and free) or ElevenLabs (your key goes to the Keychain; pick one of your voices).
6. **Your phone.** A Telegram bot token, then the pairing code you send to your bot.
7. **Security.** A PIN (kept in the Keychain), then your face and your voice.
8. **Extras.** Keys for making pictures (OpenAI or Gemini) and for calls (Agora). The GitHub builds Troi watches are set later, in Routines.
9. **Ready.** Troi restarts its voice with everything you set and introduces itself.

Then hold **Right Option** and speak. Ctrl-C in the Terminal window stops everything; the background services keep running.

To run the setup again, open http://localhost:3100/welcome?step=setup. Once you have been welcomed, changes there need the console unlocked with your PIN.

## 5. Optional pieces

### Telegram (talk from your phone)

1. In Telegram, message **@BotFather**, send `/newbot`, follow the prompts and copy the token.
2. Paste it in the welcome's **Your phone** step, or run `troi-console/keychain.py set telegram` and then `python3 troi-console/setup.py services restart telegram`.
3. Send your bot the pairing code the welcome shows (it is also in `data/logs/telegram.log`). From then on only your chat is accepted.

Text, photos and voice notes work both ways. Send "approve" or "reject" to decide the newest request that is waiting. `/call` starts a voice call.

### Voice calls (Agora)

1. Create a free project at [console.agora.io](https://console.agora.io) with **App ID + Token** authentication. Copy the App ID and the App Certificate into the welcome's **Extras** step, or run `troi-console/keychain.py set agora-appid` and `troi-console/keychain.py set agora-cert`.
2. Host `console/public/call.html` on an https address (any static host works, such as GitHub Pages on a public repo holding just that file), and put its URL in `data/console.json` as `call_page`. A phone allows its microphone only on an https page: without `call_page` the console serves the page on your own network at http://\<this Mac\>:3100/call.html, but phones will refuse the microphone there.
3. `backtalk/.venv/bin/python troi-console/agora_call.py check` says what is configured. Then say "call me": Troi sends a link on Telegram and answers.

### GitHub CI watch

Run `gh auth login`, then add the GitHub orgs and users to follow under Routines › **CI watch** (as many as you like; they are `github_orgs` in `data/console.json`). The pulse checks the newest run on `main` of every repo of each of them every three minutes: failures are spoken by the agent, or sent to Telegram when the voice line is down.

### Backups

Both run at 23:30 and go to private repos, written as the GitHub account in `github_account` and, when one is set, under the organization in `backup_org` (both in `data/console.json`; the welcome's **Memory** step shows the pair it will use). They use that account's gh token whichever account is active in `gh`. Sign it in once with `gh auth login`.

- **The vault** is committed and pushed to its own git remote. A vault without one gets `troi-vault` in the organization (or `vault_repo` from `data/console.json`), created on the first run. Pushes never force.
- **Troi's record**, the database and any new files, goes as one release a night to `troi-of-silo-one-backups`, or to `backup_repo` from the welcome's **Memory** step. Starting Troi never runs a backup; Routines › Vault backup › Run now does (it backs up the record too).

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
| The agent's browser profile | Arc's own profile when the browser is Arc; `data/browser/` when it is a Chrome of the agent's own |
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
| A file you asked it to trash is still there | That is the design: the request waits in Approvals, across restarts too. Unlock with your PIN and approve it, or send "approve" on Telegram. |
| "Approving needs you" | Unlock the console: the PIN box on the Approvals page, or **Check it's me** on the Eyes page. Or send "approve" on Telegram. |
| The hands board shows only a ring | That is the board at rest: its camera stays off until you switch Hands on (the Eyes page, or "hands on"). If it still sees no hands, allow the camera for http://localhost:3100 in the browser's site settings. |
| The agent's browser tools say the browser is not reachable | Arc was opened without its debugging port (from the Dock, before Troi). Quit Arc and start Troi again, or run `troi-console/browser-mcp.sh open`, which asks Arc to quit and brings it back with the port. |
| The console did not build | See `data/logs/console-build.log`, then run `cd console && npm install && npm run build`. |
| The globe or the cursor complains about pyobjc | `uv pip install --python troi-console/.venv-ring/bin/python pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz pyobjc-framework-ApplicationServices` |
| Anything else | Describe it to Troi in the console. It reads the troubleshooting guide that ships with each piece. |
