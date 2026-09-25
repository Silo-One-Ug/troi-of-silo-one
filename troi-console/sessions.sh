#!/bin/bash
# the agent's sessions: the record's conversations, listed; a deletion is only a REQUEST (the owner approves it on the
# console or on Telegram; the agent never deletes one itself, and the session in use cannot go); a title on request.
#   sessions.sh list [--deleted]       id, last spoken, lines, title (the ones the owner took off the list with --deleted)
#   sessions.sh delete <id> ["why"]    -> a request; the owner decides
#   sessions.sh title <id> <words...>  name a session (the id, or the start of it, as list prints it)
C="http://127.0.0.1:8796"; J="Content-Type: application/json"; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
j() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' "$@"; }
case "$1" in
  list)    python3 "$HERE/db.py" sessions ${2:+"$2"};;
  delete)  [ -n "$2" ] || { echo "sessions.sh delete <id> [\"why\"]"; exit 1; }; curl -s -m 30 -X POST -H "$J" -d "$(j request_delete "$2" why "${3:-}")" "$C/sessions"; echo;;
  title)   [ -n "$3" ] || { echo "sessions.sh title <id> <words...>"; exit 1; }; id="$2"; shift 2; python3 "$HERE/db.py" title "$id" "$@";;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0";;
esac
