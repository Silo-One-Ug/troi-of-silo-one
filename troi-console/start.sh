#!/bin/bash
# The agent's own processes, started by the root start.sh (which serves the console app on :3100 first):
# the agent's server (the API on :8796), the face, the hands board, the eyes, the browser bridge, and the
# voice line in the foreground:
#   - typed text reaches the voice line through a named pipe that is its stdin
#   - voice.py wraps backtalk (the wake word, voice ID, the guard, the welcome's quiet)
# Ctrl-C in this window stops everything; the background services keep running.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/paths.sh"
HOME_DIR="$(dirname "$HERE")"
FIFO="$HERE/.typed"
PIDS=()

PIDFILE="$HERE/.pid"

cleanup() {
  trap - EXIT INT TERM
  for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
  pkill -P $$ 2>/dev/null
  exec 3>&- 2>/dev/null
  printf off > "$HOME_DIR/backtalk/.voice_state" 2>/dev/null   # the globe and the face show the agent is off
  # the pipe is left in place on purpose: a newer launch may already own it
  [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] && rm -f "$PIDFILE"
  echo
  echo "agent stopped."
}
trap cleanup EXIT INT TERM

# only one agent at a time: shut a previous launch down fully before starting,
# so two launchers never fight over the ports or the typing pipe
OLD="$(cat "$PIDFILE" 2>/dev/null)"
if [ -n "$OLD" ] && [ "$OLD" != "$$" ] && kill -0 "$OLD" 2>/dev/null; then
  echo "troi: stopping the previous session first"
  pkill -f "troi-console/voice[.]py" 2>/dev/null
  pkill -P "$OLD" 2>/dev/null
  kill "$OLD" 2>/dev/null
  for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$OLD" 2>/dev/null || break; sleep 0.5; done
fi
echo $$ > "$PIDFILE"

# the agent's own servers from an earlier or hand-started run must not keep the
# ports: stop them (only processes running one of OUR server.py files).
free_port() {
  for p in $(lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null); do
    case "$(ps -o command= -p "$p")" in *"$HOME_DIR"/*server.py*|*server.py*) kill "$p" 2>/dev/null;; esac
  done
}
free_port 8790; free_port 8794; free_port 8796; sleep 0.5

echo "troi: starting everything from $HOME_DIR"
"$HERE/doctor.sh" 2>/dev/null | grep -E "✗|!" | grep -v "start the agent\|eyes daemon\|typing pipe\|no shared session" | sed 's/^/  doctor: /' || true   # what is about to start is not news
"$HERE/patch-board.sh" >/dev/null 2>&1 || true   # cursor control on the board survives updates

(cd "$HOME_DIR/ai-visualizer" && exec python3 server.py --no-open) &
PIDS+=($!)
echo "  face:    starting"

if [ -d "$HOME_DIR/barehands" ]; then
  (cd "$HOME_DIR/barehands" && exec python3 "$HERE/board-server.py") >>"$LOGS/board.log" 2>&1 &   # barehands' server plus the saved scene, the UI panels and taps
  PIDS+=($!)
  echo "  hands:   starting"
fi

(cd "$HERE" && exec python3 server.py) &
PIDS+=($!)

(cd "$HERE" && exec "$HOME_DIR/backtalk/.venv/bin/python" eyes.py) &
PIDS+=($!)

("$HERE/browser-mcp.sh" bridge >/dev/null 2>&1) &
PIDS+=($!)
echo "  browser: $("$HERE/browser-mcp.sh" describe)"
echo "  eyes:    ready (camera stays off until you switch it on in the console)"

echo "  pulse:   reminders, GitHub watch, morning brief (always-on service)"

[ -p "$FIFO" ] || { rm -f "$FIFO"; mkfifo "$FIFO"; }
exec 3<>"$FIFO"   # read-write, so the pipe never reports end-of-file

URL="${TROI_CONSOLE_URL:-http://localhost:3100/}"
# exactly ONE console tab, in the agent's browser (never the Mac's default browser): browser-mcp.sh console waits for the
# console app and the browser, reuses a console tab or takes the blank one, closes spares (two board pages would split the
# board between them) and brings the window forward
("$HERE/browser-mcp.sh" console "$URL" >>"$LOGS/browser.log" 2>&1) &
echo "  console: $URL   (the agent API: http://127.0.0.1:8796/)"
echo "  voice:   starting (Ctrl-C here stops everything)"

# the voice line: backtalk's environment, then our wrapper (voice.py) instead of backtalk.main
cd "$HOME_DIR/backtalk" || exit 1
if pkill -f "backtalk[.]main|troi-console/voice[.]py" 2>/dev/null; then
  echo "[backtalk] replaced a previous voice session"
  sleep 1
fi
uv sync -q --inexact 2>/dev/null || true
HF_HUB_VERBOSITY=error PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning" uv run python "$HERE/voice.py" "$@" <&3 2> >(grep -vi "pkg_resources\|VIRTUAL_ENV\|unauthenticated requests\|Defaulting repo_id" >&2)
