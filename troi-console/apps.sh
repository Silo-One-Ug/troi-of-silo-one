#!/bin/bash
# the agent's application hands:  apps.sh list | running | open <name> | focus <name> | quit <name> | kill <name> ["why"]
# open / focus / quit act directly (quit is polite: the app may ask to save). kill = force quit, which
# only FILES a request for the owner's approval (console card or Telegram "approve").
C="http://127.0.0.1:8796"; J="Content-Type: application/json"
case "$1" in
  list|running) python3 "$(dirname "$0")/apps.py" "$1";;
  open|focus|quit) curl -s -m 40 -X POST -H "$J" -d "$(python3 -c 'import json,sys; print(json.dumps({"op":sys.argv[1],"name":sys.argv[2]}))' "$1" "$2")" "$C/app"; echo;;
  kill) curl -s -m 20 -X POST -H "$J" -d "$(python3 -c 'import json,sys; print(json.dumps({"op":"kill","name":sys.argv[1],"why":sys.argv[2] if len(sys.argv)>2 else ""}))' "$2" "${3:-}")" "$C/app"; echo;;
  *) sed -n 2,4p "$0";;
esac
