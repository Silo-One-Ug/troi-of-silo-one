---
title: Permissions
description: The five macOS permissions Terminal needs, what each one is for, and who asks for it.
order: 3
---

Troi runs from Terminal (the app the Desktop shortcut opens), so the permissions go to Terminal.
Open **System Settings › Privacy & Security** and give it these:

| Permission | Needed for |
| --- | --- |
| Microphone | hearing you |
| Camera | "look at me", face ID, the face gate |
| Screen Recording | "what's on my screen" |
| Accessibility | the native hands (every app's controls by name) and the guarded cursor (it reads the label of the control under the pointer before clicking) |
| Input Monitoring | the talk key (Right Option) |

Quit and reopen Terminal after granting them; a permission granted to a running app takes effect at
its next launch.

## Who checks what

- The welcome checks Screen Recording, Accessibility and the talk key.
- `troi-console/doctor.sh` checks Accessibility and Screen Recording, and `troi-console/hands.sh
  doctor` must say `"accessibility_trusted": true` for the native hands.
- macOS asks for the camera and the microphone the first time Troi uses them.
- Hand tracking on the board and in the galaxies runs in the browser, which asks for its own camera
  permission (allow the camera for `http://localhost:3100` in the browser's site settings if it
  sees no hands).

## If something is missing

| Symptom | Fix |
| --- | --- |
| The talk key does nothing | Give Terminal Input Monitoring, quit and reopen Terminal, and start Troi again. |
| "Accessibility missing" | System Settings › Privacy & Security › Accessibility: add Terminal. Start Troi again. |
| "What's on my screen" comes back empty | Screen Recording for Terminal, then a restart of Terminal. |
| The board shows only its placeholder | Nothing is up. Ask the agent to show you something, or click one of the requests written on the board. |
