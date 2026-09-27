#!/bin/bash
# boards.sh — the boards, plural (Silo One): the agent's hands on which board is up. Each board is a scene of its own; one is
# current, and every screen that shows the board follows it (the console's Hands view, the phone, the floating conversation).
# Talks to the board server on the Mac (127.0.0.1:8794). A board that is put away is kept on disk and comes back with restore.
#   boards.sh list                      the boards, the current one marked, with how many items each holds
#   boards.sh current                   the current board's name
#   boards.sh new "<name>"              a new board, made current
#   boards.sh use "<name>"              switch to a board (by name or id); an archived one comes back
#   boards.sh rename "<name>" "<new>"   rename one
#   boards.sh archive "<name>"          put one away (the main board stays)
#   boards.sh restore "<name>"          bring one back and switch to it
# A board command may carry the board instead: board.sh '{"a":"add_card","title":"…","board":"Research"}' lands there and
# brings it up; board.sh '{"a":"board","name":"Research","create":1}' switches (and makes it). board-state.sh names the board.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('port',8794))" "$ROOT/barehands/barehands.json" 2>/dev/null || echo 8794)"
B="http://127.0.0.1:${BOARD_PORT:-$PORT}"
show() { python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: print("the board server is not answering (is Troi up?)"); sys.exit(2)
if d.get("ok") is False: print("no: " + str(d.get("error", "?"))); sys.exit(1)
cur = d.get("current"); bs = d.get("boards") or []
if sys.argv[1] == "current":
    print(next((b["name"] for b in bs if b["id"] == cur), cur)); sys.exit()
for b in bs:
    mark = "*" if b["id"] == cur else " "
    print(f"{mark} {b['"'"'name'"'"']:<24} {b['"'"'items'"'"']:>3} item(s)  id {b['"'"'id'"'"']}" + ("  (put away)" if b.get("archived") else ""))
' "$1"; }
post() { curl -s -m 8 -X POST -H 'Content-Type: application/json' -d "$1" "$B/boards"; }
j() { python3 -c 'import json,sys; print(json.dumps({k: v for k, v in zip(sys.argv[1::2], sys.argv[2::2]) if v != ""}))' "$@"; }
case "${1:-list}" in
  list)     curl -s -m 5 "$B/boards" | show list;;
  current)  curl -s -m 5 "$B/boards" | show current;;
  new)      [ -n "$2" ] || { echo 'boards.sh new "<name>"'; exit 1; }; post "$(j a create name "$2")" | show list;;
  use)      [ -n "$2" ] || { echo 'boards.sh use "<name>"'; exit 1; }; post "$(j a switch ref "$2")" | show list;;
  rename)   [ -n "$3" ] || { echo 'boards.sh rename "<name>" "<new>"'; exit 1; }; post "$(j a rename ref "$2" name "$3")" | show list;;
  archive)  [ -n "$2" ] || { echo 'boards.sh archive "<name>"'; exit 1; }; post "$(j a archive ref "$2")" | show list;;
  restore)  [ -n "$2" ] || { echo 'boards.sh restore "<name>"'; exit 1; }; post "$(j a restore ref "$2")" | show list;;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0";;
esac
