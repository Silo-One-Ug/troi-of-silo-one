#!/bin/bash
# troi: ONE command that starts everything. The face, the hands board, the
# console page (typing box, transcript, mode switches) and the voice line all
# come up together; from then on everything is done in the console page.
# Nothing in the voice, face or hands repos is modified:
#   - typed text reaches the voice line through a named pipe that is its stdin
#   - voice.py wraps backtalk to add the hands-free wake word
# Ctrl-C in this window stops everything.
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
  # the pipe is left in place on purpose: a newer launch may already own it
  [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] && rm -f "$PIDFILE"
  echo
  echo "agent stopped."
}
trap cleanup EXIT INT TERM

# only one the agent at a time: shut a previous launch down fully before starting,
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
  (cd "$HOME_DIR/barehands" && exec python3 server.py) >/dev/null &
  PIDS+=($!)
  echo "  hands:   starting"
fi

(cd "$HERE" && exec python3 server.py) &
PIDS+=($!)

(cd "$HERE" && exec "$HOME_DIR/backtalk/.venv/bin/python" eyes.py) &
PIDS+=($!)

("$HERE/browser-mcp.sh" bridge >/dev/null 2>&1) &
PIDS+=($!)
echo "  browser: the agent's own Chrome (port 9223), mirrored in the console's Browser pane"
echo "  eyes:    ready (camera stays off until you switch it on in the console)"

echo "  pulse:   reminders, GitHub watch, morning brief (always-on service)"

[ -p "$FIFO" ] || { rm -f "$FIFO"; mkfifo "$FIFO"; }
exec 3<>"$FIFO"   # read-write, so the pipe never reports end-of-file

URL="${TROI_CONSOLE_URL:-http://localhost:3100/}"
# exactly ONE console tab: two board pages would split the board between them
(sleep 2; osascript -e 'tell application "Google Chrome" to close (every tab of every window whose URL contains "127.0.0.1:8796" or URL contains "localhost:3100" or URL contains "127.0.0.1:8794" or URL contains "127.0.0.1:8790")' >/dev/null 2>&1
 if [ -d "/Applications/Google Chrome.app" ]; then open -a "Google Chrome" "$URL"; else open "$URL"; fi) &
echo "  console: $URL   (the agent API: http://127.0.0.1:8796/)"
echo "  voice:   starting (Ctrl-C here stops everything)"

# the same preparation backtalk/run.sh does, then our wrapper instead of backtalk.main
cd "$HOME_DIR/backtalk" || exit 1
if pkill -f "backtalk[.]main|troi-console/voice[.]py" 2>/dev/null; then
  echo "[backtalk] replaced a previous voice session"
  sleep 1
fi
uv sync -q --inexact 2>/dev/null || true
HF_HUB_VERBOSITY=error PYTHONWARNINGS="ignore::FutureWarning,ignore::UserWarning" uv run python "$HERE/voice.py" "$@" <&3 2> >(grep -vi "pkg_resources\|VIRTUAL_ENV\|unauthenticated requests\|Defaulting repo_id" >&2)
