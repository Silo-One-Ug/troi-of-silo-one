#!/bin/bash
# Where everything lives (see paths.py). Source it: ROOT, C (this folder), DATA, BLOBS, LOGS, CACHE, PRINTS, BROWSER, MODELS.
_P="${BASH_SOURCE[0]}"; C="$(cd "$(dirname "$_P")" && pwd)"; ROOT="$(cd "$C/.." && pwd)"
DATA="${TROI_DATA:-$ROOT/data}"; BLOBS="$DATA/blobs"; LOGS="$DATA/logs"; CACHE="$DATA/cache"; PRINTS="$DATA/prints"
BROWSER="$DATA/browser"; MODELS="$DATA/models"; CONFIG="$DATA/console.json"
mkdir -p "$BLOBS" "$LOGS" "$CACHE" "$PRINTS/voice" "$PRINTS/face" "$BROWSER" "$MODELS" "$ROOT/barehands/media/"{misc,models,research} "$ROOT/barehands/state" 2>/dev/null
export HF_HOME="${HF_HOME:-$MODELS/hf}" TORCH_HOME="${TORCH_HOME:-$MODELS/torch}"
