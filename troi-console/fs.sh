#!/bin/bash
# the agent's file hands. Everything stays inside the folders the agent may see; nothing is ever overwritten.
#   fs.sh move   <src> <dst-folder-or-path>     fs.sh copy <src> <dst>
#   fs.sh rename <src> <new name>               fs.sh mkdir <new folder path>
#   fs.sh trash  <path> ["why"]     -> only a REQUEST; the owner approves on the console or Telegram
#   fs.sh undo                       fs.sh reveal <path>   (show in Finder)      fs.sh pending
#   fs.sh open <path> [app]          open a file in its default app (or the named app)
C="http://127.0.0.1:8796"; J="Content-Type: application/json"
j() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' "$@"; }
case "$1" in
  move|copy) curl -s -m 30 -X POST -H "$J" -d "$(j op "$1" src "$2" dst "$3")" "$C/fs";;
  rename)    curl -s -m 30 -X POST -H "$J" -d "$(j op rename src "$2" name "$3")" "$C/fs";;
  mkdir)     curl -s -m 30 -X POST -H "$J" -d "$(j op mkdir src "$2")" "$C/fs";;
  trash)     curl -s -m 30 -X POST -H "$J" -d "$(j op trash src "$2" why "${3:-}")" "$C/fs";;
  reveal)    curl -s -m 30 -X POST -H "$J" -d "$(j op reveal src "$2")" "$C/fs";;
  undo)      curl -s -m 30 -X POST -H "$J" -d '{"op":"undo"}' "$C/fs";;
  pending)   curl -s -m 10 "$C/pending";;
  open)      curl -s -m 30 -X POST -H "$J" -d "$(python3 -c 'import json,sys; d={"path":sys.argv[1]}; (len(sys.argv)>2) and d.update(app=sys.argv[2]); print(json.dumps(d))' "$2" ${3:+"$3"})" "$C/open";;
  *) sed -n 2,7p "$0";;
esac; echo
