#!/bin/bash
# the agent's eyes: take one photo with the Mac's camera and print its path.
# Runs only when the agent is asked to look; the camera light comes on for a second.
# Photos land in data/blobs/looks/ (local only, never sent anywhere by this script).
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; OUT="$BLOBS/looks"
mkdir -p "$OUT"
F="$OUT/$(date +%Y-%m-%d_%H-%M-%S).jpg"
imagesnap -q -w 1.5 "$F" >/dev/null 2>&1 || { echo "camera capture failed (is imagesnap installed and the camera allowed?)" >&2; exit 1; }
ln -sf "$F" "$OUT/latest.jpg"
echo "$F"
