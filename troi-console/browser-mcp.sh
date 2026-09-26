#!/bin/bash
# The agent's browser tools (Playwright MCP) drive ONE visible browser over a debugging port, the same one the
# console's Browser page mirrors. With Arc installed that browser is Arc, and it is the owner's Arc too: Arc runs one
# instance only, so the agent cannot keep a second Arc of its own the way it keeps a second Chrome. Arc is started on
# its own profile with its debugging port (Arc, unlike Chrome, allows that on its normal profile); if the owner opened
# Arc from the Dock first, it is asked to quit and comes back with the port, its tabs and spaces intact.
# Without Arc, the browser is a second Chrome of the agent's own (its own profile in data/browser), as before.
# Used by the repo's .mcp.json; start.sh runs "browser-mcp.sh bridge" (the console's live view), and the server
# runs "browser-mcp.sh chrome" when the Browser page asks to open the browser.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/paths.sh"
PORT=9223
ARC="/Applications/Arc.app"; CHROME="/Applications/Google Chrome.app"
if [ -d "$ARC" ] && [ "${TROI_BROWSER:-arc}" != "chrome" ]; then APP="$ARC"; NAME="Arc"; PROFILE=""; else APP="$CHROME"; NAME="Google Chrome"; PROFILE="$BROWSER"; fi
export TROI_BROWSER_APP="$NAME"
NODE_DIR="$(ls -d "$HOME/Library/Application Support/Herd/config/nvm/versions/node/"*/bin 2>/dev/null | tail -1)"
[ -n "$NODE_DIR" ] && export PATH="$NODE_DIR:$PATH"

cdp_up() { curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null; }

ensure_browser() {
  cdp_up && return 0
  if [ "$NAME" = "Arc" ] && pgrep -xq Arc; then
    # Arc is open without its port (started from the Dock): a polite quit; it restores its tabs and spaces on the way back
    osascript -e 'tell application "Arc" to quit' >/dev/null 2>&1
    for i in $(seq 1 40); do pgrep -xq Arc || break; sleep 0.5; done
    pgrep -xq Arc && { echo "Arc did not quit; it needs its debugging port (quit Arc, then try again)" >&2; return 1; }
  fi
  if [ -n "$PROFILE" ]; then
    # a second Chrome of the agent's own: its own profile, its own window
    mkdir -p "$PROFILE"
    open -na "$APP" --args --remote-debugging-port=$PORT --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
      --window-size=1280,900 --window-position=80,60 "about:blank" 2>/dev/null
  else
    # the owner's Arc: the port and nothing else, so it comes back with its own windows and spaces, not one more of ours
    open -na "$APP" --args --remote-debugging-port=$PORT --no-first-run --no-default-browser-check 2>/dev/null
  fi
  for i in $(seq 1 80); do cdp_up && { open -a "$APP" 2>/dev/null; return 0; }; sleep 0.5; done   # activated once: Arc shows its window only then
  echo "$NAME did not answer on port $PORT" >&2; return 1
}

case "${1:-mcp}" in
  chrome|open) ensure_browser && echo "the agent's browser ($NAME) is up on port $PORT";;
  which)  echo "$NAME";;
  bridge) ensure_browser; exec node "$HERE/browser.js";;
  *)      ensure_browser; exec npx -y @playwright/mcp@latest --cdp-endpoint "http://127.0.0.1:$PORT";;
esac
