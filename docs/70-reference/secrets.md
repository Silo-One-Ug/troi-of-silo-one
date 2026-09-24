---
title: Secrets
description: The Keychain items Troi uses, what each one is for, and how to set or remove them. Values are never shown.
order: 4
---

Secrets live only in the macOS login Keychain, under the account `troi-of-silo-one`, with service
names `troi-of-silo-one.<name>`. The welcome sets them; `troi-console/keychain.py list` says which
are set (it never shows values) and `troi-console/keychain.py set <name>` sets one. The agent's
tools use them in place; the agent itself cannot change them (the Keychain is among the guard's
safeguards) and is told never to write a secret into a note, a summary or a log.

| Name | What |
| --- | --- |
| `pin` | The PIN that unlocks the console: approvals and protected changes |
| `telegram` | The Telegram bot token (your phone pairs with a code; the pairing is kept in the record) |
| `elevenlabs` | The ElevenLabs key (the voice, meeting transcription) |
| `openai`, `gemini` | Keys for making pictures |
| `agora-appid`, `agora-cert` | Voice calls |

After setting `telegram`, restart the bridge: `python3 troi-console/setup.py services restart
telegram`.

## Removing them

```bash
for n in pin telegram elevenlabs openai gemini agora-appid agora-cert; do
  security delete-generic-password -a troi-of-silo-one -s "troi-of-silo-one.$n" >/dev/null 2>&1 && echo "removed $n"
done
```

GitHub is different: the backups, the CI watch and the PR reviews use `gh`'s own login
(`gh auth login`), not a Keychain item of Troi's.
