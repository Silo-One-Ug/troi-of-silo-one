#!/bin/bash
# Put an image (or a .glb model) on the hands board:  show-image.sh <file> [title] [x] [y]
# The board only stages files inside barehands/media/ (the board's airlock), so the
# file is COPIED there first (media/misc for images, media/models for models).
F="$1"; T="${2:-$(basename "${F%.*}")}"; X="${3:-0.5}"; Y="${4:-0.45}"
[ -f "$F" ] || { echo "no such file: $F" >&2; exit 1; }
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; M="$ROOT/barehands/media"; ext="$(echo "${F##*.}" | tr 'A-Z' 'a-z')"
case "$ext" in glb|gltf) sub=models;; *) sub=misc;; esac
name="$(basename "$F" | tr ' ' '_')"
command cp -f "$F" "$M/$sub/$name" </dev/null
CMD=$(python3 -c 'import json,sys; print(json.dumps({"a":"add_img","title":sys.argv[1],"src":sys.argv[2],"x":float(sys.argv[3]),"y":float(sys.argv[4])}))' "$T" "$sub/$name" "$X" "$Y")
"$ROOT/barehands/bin/board.sh" "$CMD" >/dev/null </dev/null && echo "on the board: $T ($sub/$name)"
