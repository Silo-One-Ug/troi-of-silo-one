---
title: Troubleshooting
description: The doctor first, then the symptoms and their fixes.
order: 7
---

Run `troi-console/doctor.sh` first. It checks the services, the ports, the permissions, the secrets,
the shared session, the backups and the logs, and names what is wrong in plain words. The agent is
its own mechanic: describe a problem to it in the console and it diagnoses and repairs what is its
to repair, and tells you in one sentence what needs you (a macOS permission, a secret in the
Keychain), with the exact place to do it.

| Symptom | Fix |
| --- | --- |
| The console says the agent is not answering | Start Troi from the Desktop. If it is running, `lsof -nP -iTCP:8796` shows who holds the port; starting Troi again frees its own ports. |
| The talk key does nothing | Give Terminal Input Monitoring, quit and reopen Terminal, and start Troi again. |
| "Accessibility missing" | System Settings › Privacy & Security › Accessibility: add Terminal. Start Troi again. |
| Troi hears itself or the TV | Turn on the wake word and Voice ID in Modes. Learn your voice with about a minute of push-to-talk speech. The face gate keeps hands-free to the moments you are at the camera. |
| Garbled transcription with a Bluetooth headset | Set `mic_device` in `backtalk/backtalk.json` to the Mac's own microphone. |
| A file you asked it to trash is still there | That is the design: the request waits in Approvals, across restarts too. Unlock with your PIN and approve it, or send "approve" on Telegram. |
| "Approving needs you" | Unlock the console: the PIN box at the lock, or **Check it's me** on the Eyes page. Or send "approve" on Telegram. |
| The hands board shows only a ring | That is the board at rest: its camera stays off until you switch Hands on (the Eyes page, or "hands on"). If it still sees no hands, allow the camera for `http://localhost:3100` in the browser's site settings. |
| The agent's browser tools say the browser is not reachable | Arc was opened without its debugging port (from the Dock, before Troi). Quit Arc and start Troi again, or run `troi-console/browser-mcp.sh open`. |
| The native hands say `no: … did not answer in time` | The app's main thread is busy (a dialog, a hang); wait, or look with `windows`. More in [The native hands](../40-abilities/native-hands.md). |
| The console did not build | See `data/logs/console-build.log`, then run `cd console && npm install && npm run build`. |
| The globe or the cursor complains about pyobjc | `uv pip install --python troi-console/.venv-ring/bin/python pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz pyobjc-framework-ApplicationServices` |
| The phone cannot reach the console | Modes › Your phone is **This Mac only** until you change it, and a change takes effect at Troi's next start. With **Tailscale**, the phone's Tailscale must be on and signed in to the same account; with **This network**, the phone must be on the same Wi-Fi. See [On your phone](../20-console/on-your-phone.md). |
| `Address already in use` on port 8796 at start, right after setting up https over Tailscale | Fixed in the server: Tailscale's https listener holds the tailnet side of that port, and the server now keeps to the Mac itself and lets Tailscale carry the phone. Start Troi again. |
| Safari on the phone says it could not establish a secure connection | You opened the Mac's `.ts.net` name; browsers force https on it. Open the Mac's Tailscale address instead (`http://100.x.y.z:3100`, shown under the switch in Modes). |
| A welcome step's Continue does nothing | The console cannot reach the agent's server. Start Troi from the Desktop and reload; `lsof -nP -iTCP:8796` shows whether its port is held by something else. |
| Voice calls say they need `call_page` | A phone allows its microphone only on an https page: host `console/public/call.html` on one and set `call_page` in the settings ([Calls](../10-talking/calls.md)). |
| The nightly backup shows "not running" | Normal between runs. `troi-console/backup-vault.sh` runs one now. |
| Anything else | Describe it to Troi in the console. It reads the troubleshooting guide that ships with each piece. |

## Logs

| Log | What is in it |
| --- | --- |
| `backtalk/logs/backtalk.log` | The voice line: what it heard, what it said, how long each turn took |
| `data/logs/hands.log` | Every action of the native hands |
| `data/logs/fs.log` | Every file operation |
| `data/logs/telegram.log` | The Telegram bridge, and the pairing code |
| `data/logs/console-build.log` | The console's build |
| `data/logs/console-app.log` | The console's server |
