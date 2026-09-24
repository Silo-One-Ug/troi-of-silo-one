#!/bin/bash
# Resumable download of the larger speech-recognition model (about 1.5 GB).
# Safe to run again at any time: it continues where it stopped. voice.py starts
# using the model on the next launch after the .done marker appears.
source "$(cd "$(dirname "$0")" && pwd)/paths.sh"; M="$MODELS/whisper-medium.en-mlx"
mkdir -p "$M"
URL="https://huggingface.co/mlx-community/whisper-medium.en-mlx/resolve/main"
[ -s "$M/config.json" ] || curl -sL -o "$M/config.json" "$URL/config.json"
until curl -L -C - --retry 20 --retry-delay 5 -o "$M/weights.npz" "$URL/weights.npz"; do sleep 10; done
SIZE=$(stat -f%z "$M/weights.npz")
if [ "$SIZE" -gt 1500000000 ]; then touch "$M/.done"; echo "model complete ($SIZE bytes)"; else echo "model incomplete ($SIZE bytes)"; fi
