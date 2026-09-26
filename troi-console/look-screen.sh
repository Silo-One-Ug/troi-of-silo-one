#!/bin/bash
# the agent's screen sight: capture the screen (or one display) and print the path; while the owner shares a screen or a
# window (share.sh), the shared frame is what you get (--whole for the real screen).
# Needs Screen Recording permission for the terminal app the first time.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; OUT="$BLOBS/screens"; mkdir -p "$OUT"
# a live share (share.sh) is what the owner is showing: its newest frame stands in for the screen unless --whole asks otherwise
SHARE="$DATA/cache/share"
if [ "$1" != "--whole" ] && [ -f "$SHARE/share.json" ] && [ -f "$SHARE/live.jpg" ] && python3 -c 'import json,sys,time; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("state")=="live" and time.time()-float(d.get("last") or 0) < 6 else 1)' "$SHARE/share.json" 2>/dev/null; then
  F="$OUT/$(date +%Y-%m-%d_%H-%M-%S)-share.jpg"; cp "$SHARE/live.jpg" "$F" && { echo "$F"; exit 0; }
fi
[ "$1" = "--whole" ] && shift
F="$OUT/$(date +%Y-%m-%d_%H-%M-%S).png"
/usr/sbin/screencapture -x -C ${1:+-D "$1"} "$F" 2>/dev/null || { echo "screen capture failed (grant Screen Recording to the terminal app in System Settings > Privacy & Security)" >&2; exit 1; }
# shrink for the model: half size, jpeg
/usr/bin/sips -Z 1600 -s format jpeg "$F" --out "${F%.png}.jpg" >/dev/null 2>&1 && rm -f "$F" && F="${F%.png}.jpg"
echo "$F"
