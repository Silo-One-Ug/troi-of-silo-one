#!/bin/bash
# troi doctor: checks every piece and says what is wrong in plain words. Exit 1 if anything is red.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"; H="$ROOT"; bad=0
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
red()  { printf "  \033[31m✗\033[0m %s\n" "$1"; bad=1; }
echo "AGENT DOCTOR  $(date '+%Y-%m-%d %H:%M')"
echo "services"
for s in ring pulse telegram vault-backup; do launchctl list 2>/dev/null | grep -qF "com.troi-of-silo-one.$s" && ok "$s service loaded" || red "$s service not loaded  (python3 $C/setup.py services install)"; done
echo "the running stack"
for p in "3100 console" "8796 agent API" "8790 face" "8794 hands board"; do set -- $p; lsof -nP -t -iTCP:$1 -sTCP:LISTEN >/dev/null 2>&1 && ok "$2 on :$1" || warn "$2 not running on :$1 (start the agent)"; done
pgrep -f "troi-console/voice[.]py" >/dev/null && ok "voice line running" || warn "voice line not running (start the agent)"
pgrep -f "eyes[.]py" >/dev/null && ok "eyes daemon" || warn "eyes daemon not running"
[ -p "$C/.typed" ] && ok "typing pipe present" || warn "typing pipe missing (console typing/telegram relay will fall back)"
echo "permissions"
"$C/.venv-ring/bin/python" -c "from ApplicationServices import AXIsProcessTrusted; import sys; sys.exit(0 if AXIsProcessTrusted() else 1)" 2>/dev/null && ok "Accessibility (cursor guard can read buttons)" || red "Accessibility missing for the app that launches the agent: System Settings > Privacy & Security > Accessibility"
"$C/hands.sh" doctor 2>/dev/null | grep -q '"accessibility_trusted": true' && ok "native hands answer (hands.sh doctor)" || red "native hands cannot see the apps (Accessibility for the app that launched the agent; run $C/hands.sh doctor)"
g="$("$C/google.sh" status --line 2>/dev/null)"; case $? in 0) ok "$g";; 2) warn "$g";; *) warn "${g:-Google account not set up (google.sh setup)}";; esac
SC="$(mktemp -t sc-test).png"   # screencapture will not write into a folder of the agent's own; a temp file is fine
/usr/sbin/screencapture -x -R0,0,2,2 "$SC" 2>/dev/null && [ -s "$SC" ] && ok "Screen Recording (screen sight)" || red "Screen Recording missing for the app that launches the agent (Terminal): System Settings > Privacy & Security > Screen Recording, then quit and reopen Terminal"
command rm -f "$SC" 2>/dev/null
echo "secrets"
K="troi-of-silo-one"; for s in "telegram Telegram bot" "agora-appid Agora app id" "agora-cert Agora certificate" "elevenlabs ElevenLabs voice"; do set -- $s; n=$1; shift; security find-generic-password -a "$K" -s "$K.$n" >/dev/null 2>&1 && ok "$* in the Keychain" || warn "$* not set (onboarding, or: keychain.py set $n)"; done
security find-generic-password -a "$K" -s "$K.pin" >/dev/null 2>&1 && ok "PIN set (console unlock for protected settings)" || warn "no PIN: protected settings can only be approved on Telegram (onboarding, or: keychain.py set pin)"
g=$(python3 -c 'import json;print(json.load(open("'"$CONFIG"'")).get("guard_settings", True))' 2>/dev/null); [ "$g" = "False" ] && red "the settings guard is OFF (guard_settings in console.json)" || ok "settings guard on"
/usr/bin/python3 "$C/imagine.py" check >/dev/null 2>&1 && ok "picture making: $(/usr/bin/python3 "$C/imagine.py" check | head -1 | sed 's/image backends: //')" || warn "picture making: no image key yet (onboarding, or: keychain.py set openai / gemini)"
[ -x "$C/.venv-face/bin/python" ] && { [ -f "$PRINTS/face/owner.npy" ] && ok "face ID: face known" || warn "face ID installed but no face learnt yet (console: Modes > Face ID > Learn my face)"; } || warn "face ID not installed (run ./install.sh again: it builds the face ID environment)"
echo "memory and sessions"
[ -s "$H/backtalk/.backtalk_session" ] && ok "shared session: $(command cat $H/backtalk/.backtalk_session | cut -c1-8)…" || warn "no shared session yet (first voice launch sets it)"
if [ ! -f "$VAULT/VAULT-INDEX.md" ]; then warn "no vault yet (the welcome makes one, or: python3 $C/setup.py vault new)"
elif [ -d "$VAULT/.git" ]; then ok "vault is a git repo ($(git -C "$VAULT" log --oneline 2>/dev/null | wc -l | tr -d ' ') backups)"; else red "the vault is not a git repo, so it has no backups (cd \"$VAULT\" && git init -b main)"; fi
if [ -d "$VAULT/.git" ]; then b=$(git -C "$VAULT" status --short 2>/dev/null | wc -l | tr -d ' '); [ "$b" -gt 0 ] && warn "$b vault change(s) not yet backed up (tonight, or: backup-vault.sh)" || ok "vault fully backed up"; fi
echo "housekeeping"
df -h "$HOME" | awk 'NR==2 {print "  free disk: " $4}'
for f in "$H/backtalk/logs/backtalk.log" "$LOGS/telegram.log" "$LOGS/console-app.log"; do [ -f "$f" ] && sz=$(du -k "$f" | cut -f1) && { [ "$sz" -gt 20000 ] && warn "$(basename $f) is $((sz/1024)) MB (housekeeping rotates it)" || ok "$(basename $f) $((sz/1024)) MB"; }; done
n=$(find "$BLOBS" -type f 2>/dev/null | wc -l | tr -d ' '); ok "$n files in the blob store ($(du -sh "$DATA" 2>/dev/null | cut -f1) in data/)"
p=$(curl -s -m 3 http://127.0.0.1:8796/pending 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)['pending']))" 2>/dev/null); [ -n "$p" ] && [ "$p" -gt 0 ] && warn "$p approval(s) waiting for the owner" || true
[ $bad -eq 0 ] && echo "all green" || echo "something needs attention (see ✗ above)"
exit $bad
