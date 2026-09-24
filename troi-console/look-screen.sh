#!/bin/bash
# the agent's screen sight: capture the screen (or one display) and print the path.
# Needs Screen Recording permission for the terminal app the first time.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; OUT="$BLOBS/screens"; mkdir -p "$OUT"
F="$OUT/$(date +%Y-%m-%d_%H-%M-%S).png"
/usr/sbin/screencapture -x -C ${1:+-D "$1"} "$F" 2>/dev/null || { echo "screen capture failed (grant Screen Recording to the terminal app in System Settings > Privacy & Security)" >&2; exit 1; }
# shrink for the model: half size, jpeg
/usr/bin/sips -Z 1600 -s format jpeg "$F" --out "${F%.png}.jpg" >/dev/null 2>&1 && rm -f "$F" && F="${F%.png}.jpg"
echo "$F"
