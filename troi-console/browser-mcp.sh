#!/bin/bash
# The agent's browser tools (Playwright MCP) drive ONE visible Chrome of the agent's own: its own
# profile (data/browser), a debugging port, the same instance the console's Browser pane
# shows. This wrapper makes sure that Chrome is up, then hands over to the MCP server pointed at it.
# Used by the repo's .mcp.json; start.sh also calls "browser-mcp.sh chrome" to open the browser early.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/paths.sh"
PORT=9223
CHROME="/Applications/Google Chrome.app"
NODE_DIR="$(ls -d "$HOME/Library/Application Support/Herd/config/nvm/versions/node/"*/bin 2>/dev/null | tail -1)"
[ -n "$NODE_DIR" ] && export PATH="$NODE_DIR:$PATH"

ensure_chrome() {
  if ! curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null; then
    open -na "$CHROME" --args --remote-debugging-port=$PORT --user-data-dir="$BROWSER" --no-first-run --no-default-browser-check \
      --window-size=1280,900 --window-position=80,60 "about:blank" 2>/dev/null
    for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null && break; sleep 0.5; done
  fi
}

case "${1:-mcp}" in
  chrome) ensure_chrome; echo "the agent's browser is up on port $PORT";;
  bridge) ensure_chrome; exec node "$HERE/browser.js";;
  *)      ensure_chrome; exec npx -y @playwright/mcp@latest --cdp-endpoint "http://127.0.0.1:$PORT";;
esac
