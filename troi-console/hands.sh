#!/bin/bash
# the agent's native hands (see hands.py for the commands and the guards). "hands.sh mcp" is the tool server the
# brain talks to (listed in the repo's .mcp.json); anything else is the command line.
D="$(cd "$(dirname "$0")" && pwd)"; PY="$D/../backtalk/.venv/bin/python"
[ -x "$PY" ] || { echo '{"ok": false, "error": "backtalk/.venv is missing; run ./install.sh"}'; exit 1; }
case "${1:-}" in
  mcp) exec "$PY" "$D/hands-mcp.py";;
  *)   exec "$PY" "$D/hands.py" "$@";;
esac
