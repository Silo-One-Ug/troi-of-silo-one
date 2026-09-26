#!/bin/bash
# brain.sh — the agent picks the brain for the job. Heavy work (code changes, reviews, research reports, long reads,
# server operations) goes to the deep model at a higher effort; everything else stays on the fast model at the resting
# effort. It pulls the voice line's own levers ("switch to the deep model", "back to the fast model", "set effort to X"),
# which the server delivers the moment the voice line is idle, so a switch always lands BETWEEN turns: `for` therefore
# queues the task as the next turn, and the agent's current turn ends with one line about the switch.
#   brain.sh status                                   the fast and deep models, the effort, what the helper remembers
#   brain.sh deep | fast                              the session's model (deep is slower and better; fast is the default)
#   brain.sh model <name>                             a brain by name, for this session; the names are the config's models map
#   brain.sh models                                   the map: name -> model id (backtalk/backtalk.json "models", the ONE list)
#   brain.sh effort low|medium|high|xhigh|max         the effort (the voice line saves it as the default)
#   brain.sh for "<task>" [--deep|--model <name>] [--effort <level>]   remember the setting, switch, then continue <task> on the new brain
#   brain.sh back                                     restore what `for` remembered (the model and the effort)
#   brain.sh rest [<level>]                           show or set the resting effort (default medium)
# The voice line applies these; in a plain terminal session the slash commands /model and /effort are the owner's.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; C="http://127.0.0.1:8796"; J="Content-Type: application/json"
MEM="$ROOT/data/brain.json"; LOG="$ROOT/data/logs/brain.log"; VLOG="$ROOT/backtalk/logs/backtalk.log"
mkdir -p "$(dirname "$LOG")"
mem() { python3 - "$MEM" "$@" <<'PY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]); d = {}
try: d = json.loads(p.read_text())
except Exception: pass
args = sys.argv[2:]
if not args: print(json.dumps(d)); sys.exit()
if args[0] == "get": print(d.get(args[1], "")); sys.exit()
if args[0] == "set":
    for kv in args[1:]:
        k, _, v = kv.partition("="); d[k] = json.loads(v) if v[:1] in "{[" or v in ("null", "true", "false") else v
    p.write_text(json.dumps(d, indent=2) + "\n"); print("ok")
PY
}
cfg() { curl -s -m 6 "$C/config" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$1',''))" 2>/dev/null; }
alive() { curl -s -m 4 -o /dev/null -w '%{http_code}' "$C/state" 2>/dev/null | grep -q 200; }
phrase() { curl -s -m 10 -X POST -H "$J" -H "Origin: $C" -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1], "when": "idle"}))' "$1")" "$C/say" >/dev/null; echo "$(date '+%F %T') sent: $1" >>"$LOG"; }
say_text() { curl -s -m 10 -X POST -H "$J" -H "Origin: $C" -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1], "when": "idle"}))' "$1")" "$C/say" >/dev/null; echo "$(date '+%F %T') queued: ${1:0:80}" >>"$LOG"; }
wait_effort() { for i in $(seq 1 60); do [ "$(cfg effort)" = "$1" ] && return 0; sleep 1; done; return 1; }
wait_log() { for i in $(seq 1 45); do tail -c 4000 "$VLOG" 2>/dev/null | tail -n 12 | grep -q -i "$1" && return 0; sleep 1; done; return 1; }
need_line() { alive || { echo "the voice line is not running (a terminal session): switch with /model and /effort yourself"; exit 2; }; }
lvl_ok() { case "$1" in low|medium|high|xhigh|max) return 0;; *) return 1;; esac; }
models() { python3 -c 'import json,sys
m=json.load(open(sys.argv[1])).get("models") or {}
print("\n".join(f"{k} {v}" for k,v in m.items()))' "$ROOT/backtalk/backtalk.json" 2>/dev/null; }
name_ok() { models | awk '{print $1}' | grep -qx -- "$1"; }
id_of() { models | awk -v n="$1" '$1==n{print $2}'; }
pretty() { local n; n="$(models | awk -v id="$1" '$2==id{print $1}' | head -1)"; [ -n "$n" ] && echo "$n ($1)" || echo "$1"; }
resting() { local r; r="$(mem get resting)"; echo "${r:-medium}"; }

case "$1" in
  status)
    if alive; then echo "fast: $(pretty "$(cfg model)") · deep: $(pretty "$(cfg deep_model)") · effort: $(cfg effort) (saved default)"; else echo "the voice line is not running (a terminal session)"; fi
    echo "session model: $(mem get session_model | sed 's/^$/fast/') · resting effort: $(resting)$( [ -n "$(mem get before)" ] && echo " · remembered for back: $(mem get before)" )";;
  deep|fast)
    need_line; mem set session_model="$1" >/dev/null
    [ "$1" = deep ] && phrase "switch to the deep model" || phrase "back to the fast model"
    echo "the $1 model, from the next turn";;
  models)
    if [ -z "$(models)" ]; then echo "no models map in the voice line's config"; else models | awk '{printf "  %-10s %s\n", $1, $2}'; fi;;
  model)
    name_ok "$2" || { echo "no brain called '$2'; the names: $(models | awk '{print $1}' | tr '\n' ' ')"; exit 1; }
    need_line; mem set session_model="$2" >/dev/null; phrase "switch to $2"; echo "$2 ($(id_of "$2")), from the next turn (this session)";;
  effort)
    lvl_ok "$2" || { echo "brain.sh effort low|medium|high|xhigh|max"; exit 1; }
    need_line; phrase "set effort to $2"; echo "effort $2, from the next turn (the voice line saves it as the default)";;
  rest)
    if [ -n "$2" ]; then lvl_ok "$2" || { echo "brain.sh rest low|medium|high|xhigh|max"; exit 1; }; mem set resting="$2" >/dev/null; echo "resting effort: $2"; alive && phrase "set effort to $2"; else echo "resting effort: $(resting)"; fi;;
  for)
    need_line; task="$2"; shift 2; deep=0; eff=""; name=""
    while [ $# -gt 0 ]; do case "$1" in --deep) deep=1;; --model) name="$2"; shift;; --effort) eff="$2"; shift;; esac; shift; done
    [ -n "$name" ] && ! name_ok "$name" && { echo "no brain called '$name'; the names: $(models | awk '{print $1}' | tr '\n' ' ')"; exit 1; }
    [ -n "$eff" ] && ! lvl_ok "$eff" && { echo "unknown effort $eff"; exit 1; }
    [ -z "$task" ] && { echo "brain.sh for \"<task>\" [--deep] [--effort <level>]"; exit 1; }
    before="{\"model\":\"$(mem get session_model | sed 's/^$/fast/')\",\"effort\":\"$(cfg effort)\"}"; mem set before="$before" task="$task" >/dev/null
    nohup "$0" _run_for "$task" "$deep" "$eff" "$name" >>"$LOG" 2>&1 &
    echo "switching after this turn$( [ $deep = 1 ] && echo " to the deep model" )$( [ -n "$name" ] && echo " to $name" )$( [ -n "$eff" ] && echo " at $eff effort" ); the task continues on the new brain";;
  _run_for)                                  # detached: the levers, one at a time, then the task as the next turn
    task="$2"; deep="$3"; eff="$4"; name="$5"
    if [ -n "$name" ]; then mem set session_model="$name" >/dev/null; phrase "switch to $name"; wait_log "on $name now" || sleep 12;
    elif [ "$deep" = 1 ]; then mem set session_model=deep >/dev/null; phrase "switch to the deep model"; wait_log "deep model online" || sleep 12; fi
    if [ -n "$eff" ]; then phrase "set effort to $eff"; wait_effort "$eff" || echo "$(date '+%F %T') effort $eff not confirmed in time" >>"$LOG"; fi
    say_text "(brain: continuing$( [ "$deep" = 1 ] && echo " on the deep model" )$( [ -n "$name" ] && echo " on $name" )$( [ -n "$eff" ] && echo " at $eff effort" ): $task. When it is done, run brain.sh back.)";;
  back)
    need_line; before="$(mem get before)"
    [ -z "$before" ] && { echo "nothing remembered: the fast model and the resting effort it is"; before="{\"model\":\"fast\",\"effort\":\"$(resting)\"}"; }
    nohup "$0" _run_back "$before" >>"$LOG" 2>&1 &
    echo "back after this turn: $before";;
  _run_back)
    model="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("model","fast"))' "$2")"; eff="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("effort",""))' "$2")"
    [ -z "$eff" ] && eff="$(resting)"
    if [ "$model" = fast ] && [ "$(mem get session_model)" != fast ]; then phrase "back to the fast model"; mem set session_model=fast >/dev/null; wait_log "back on the fast model" || sleep 10; fi
    lvl_ok "$eff" && [ "$(cfg effort)" != "$eff" ] && { phrase "set effort to $eff"; wait_effort "$eff" || true; }
    mem set before= task= >/dev/null;;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0";;
esac
