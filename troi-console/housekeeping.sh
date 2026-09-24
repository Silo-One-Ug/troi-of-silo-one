#!/bin/bash
# Nightly tidy: rotate logs that grew, keep 7 days of them; thin the agent's own throwaway pictures.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; H="$ROOT"; D=$(date +%Y%m%d)
rotate() { f="$1"; [ -f "$f" ] || return; sz=$(du -k "$f" | cut -f1); [ "$sz" -gt 20000 ] || return; mv "$f" "${f%.log}-$D.log" 2>/dev/null || mv "$f" "$f-$D"; : > "$f"; echo "rotated $(basename $f) ($((sz/1024)) MB)"; }
rotate "$H/backtalk/logs/backtalk.log"; rotate "$LOGS/telegram.log"; rotate "$LOGS/fs.log"; rotate "$LOGS/cursor.log"; rotate "$LOGS/agora.log"
for f in "$LOGS/console.out" "$LOGS/pulse.out" "$LOGS/telegram.out" "$LOGS/ring.out"; do [ -f "$f" ] && [ $(du -k "$f" | cut -f1) -gt 20000 ] && : > "$f" && echo "emptied $(basename $f)"; done
find "$H/backtalk/logs" "$LOGS" -name "*-20*.log" -mtime +7 -print -delete 2>/dev/null | sed 's/^/expired /'
# the agent's own captures past their retention (looks, screens, Telegram pictures: 14 days) go to the Trash; starred ones stay
/usr/bin/python3 "$C/db.py" retain 2>/dev/null | sed "s/^/  /"
find "$DATA/backups" -type f -mtime +30 -print -delete 2>/dev/null | sed 's/^/expired backup /'
echo "housekeeping done $(date '+%H:%M')"
