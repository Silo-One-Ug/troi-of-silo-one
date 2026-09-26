#!/bin/bash
# Put a picture (or a video) on the board:  show-image.sh <file> [title] [x] [y]
# The board only shows files inside barehands/media/ (its airlock), so the file is COPIED there first (media/misc; a .glb
# goes to media/models, though 3D models are not drawn on the board). Without x and y the board places it in free space.
F="$1"; T="${2:-$(basename "${F%.*}")}"; X="${3:-}"; Y="${4:-}"
[ -f "$F" ] || { echo "no such file: $F" >&2; exit 1; }
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; M="$ROOT/barehands/media"; ext="$(echo "${F##*.}" | tr 'A-Z' 'a-z')"
case "$ext" in glb|gltf) sub=models;; *) sub=misc;; esac
name="$(basename "$F" | tr ' ' '_')"
command cp -f "$F" "$M/$sub/$name" </dev/null
CMD=$(python3 -c 'import json,sys; c={"a":"add_img","title":sys.argv[1],"src":sys.argv[2]}
if sys.argv[3]: c["x"]=float(sys.argv[3])
if sys.argv[4]: c["y"]=float(sys.argv[4])
print(json.dumps(c))' "$T" "$sub/$name" "$X" "$Y")
"$ROOT/barehands/bin/board.sh" "$CMD" >/dev/null </dev/null && echo "on the board: $T ($sub/$name)"
