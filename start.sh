#!/bin/bash
# Troi of Silo One: the one command that starts everything. The console app (http://localhost:3100), the agent's
# API and tools, the face, the hands board, the eyes, the voice line; the background services are (re)started so
# fresh secrets load. The first run opens the welcome; after that, the conversation. Ctrl-C here stops everything
# (the background services keep running: pulse, the globe, Telegram, the nightly backups).
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"; C="$ROOT/troi-console"; source "$C/paths.sh"
NODE_DIR="$(ls -d "$HOME/Library/Application Support/Herd/config/nvm/versions/node/"*/bin 2>/dev/null | tail -1)"
command -v node >/dev/null 2>&1 || { [ -n "$NODE_DIR" ] && export PATH="$NODE_DIR:$PATH"; }
command -v node >/dev/null 2>&1 || { echo "troi: node is missing; run ./install.sh first"; exit 1; }
[ -x "$ROOT/backtalk/.venv/bin/python" ] || { echo "troi: not installed yet; run ./install.sh first"; exit 1; }
[ -f "$ROOT/CLAUDE.md" ] && [ -f "$CONFIG" ] || /usr/bin/python3 "$C/setup.py" render >/dev/null
/usr/bin/python3 "$C/setup.py" services restart >/dev/null 2>&1 || true
# the console app: built once (again only when its code changed), served on :3100 for as long as this runs
CON="$ROOT/console"
for p in $(lsof -nP -t -iTCP:3100 -sTCP:LISTEN 2>/dev/null); do kill "$p" 2>/dev/null; done
if [ ! -f "$CON/.next/BUILD_ID" ] || [ -n "$(find "$CON/app" "$CON/components" "$CON/lib" -newer "$CON/.next/BUILD_ID" -type f 2>/dev/null | head -1)" ]; then
  echo "troi: building the console…"; (cd "$CON" && npm run build >"$LOGS/console-build.log" 2>&1) || { echo "troi: the console did not build (see $LOGS/console-build.log)"; exit 1; }
fi
(cd "$CON" && exec node "$CON/node_modules/next/dist/bin/next" start -p 3100 >"$LOGS/console-app.log" 2>&1) &
exec "$C/start.sh" "$@"                                       # its cleanup (Ctrl-C) stops its children, the console app among them
