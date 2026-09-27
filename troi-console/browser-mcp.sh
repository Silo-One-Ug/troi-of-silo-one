#!/bin/bash
# The agent's browser tools (Playwright MCP) drive ONE browser. Since 2026-09-27 that browser is Google Chrome, in one of
# three ways, chosen once and kept in data/browser-choice (TROI_BROWSER in the environment overrides):
#   own    (the default) a Chrome of the agent's own: its own profile in data/browser, its own window, and the debugging
#          port 9223 that the console's Browser page mirrors. The owner logs in there when a site needs it, and it sticks.
#   yours  the owner's own Chrome, logins included, through the Playwright extension (Chrome 136 and later refuse the
#          debugging port on a normal profile, so the extension is the only door). Chosen by itself when the extension
#          is installed in the owner's Chrome (auto). No port, so no live view on the console: the first tool call opens
#          a page in Chrome where the owner picks the tab the agent may use and approves the connection.
#   arc    the old way: the owner's Arc on its debugging port (Arc allows it on its normal profile). By choice only.
#   browser-mcp.sh                        the MCP itself (.mcp.json runs this)
#   browser-mcp.sh open|chrome            start the browser if it is not up (the server does this when the Browser page asks)
#   browser-mcp.sh console [url]          the console in the agent's browser, in ONE tab: an existing one reused, spares closed,
#                                         a blank tab taken, else a new one; the window comes forward (start.sh does this)
#   browser-mcp.sh which                  the browser's name ("Google Chrome" or "Arc"; start.sh and the server read it)
#   browser-mcp.sh describe               the browser in words: which, whose, how
#   browser-mcp.sh status                 the choice, the browser, the extension, who answers on the port
#   browser-mcp.sh use own|yours|arc|auto keep the choice (auto: yours when the extension is there, else own)
#   browser-mcp.sh bridge                 the console's live view (browser.js), where there is a port to watch
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"; source "$HERE/paths.sh"
PORT=9223
ARC="/Applications/Arc.app"; CHROME="/Applications/Google Chrome.app"; CHOICE="$DATA/browser-choice"
CONSOLE_URL="${TROI_CONSOLE_URL:-http://localhost:3100/}"
EXT_ID="mmlmfjhmonkocbjadbfplnigmagldckm"                      # the Playwright extension, Chrome Web Store
EXT_URL="https://chromewebstore.google.com/detail/playwright-extension/$EXT_ID"
NODE_DIR="$(ls -d "$HOME/Library/Application Support/Herd/config/nvm/versions/node/"*/bin 2>/dev/null | tail -1)"
[ -n "$NODE_DIR" ] && export PATH="$NODE_DIR:$PATH"

extension_installed() { ls -d "$HOME/Library/Application Support/Google/Chrome/"*/Extensions/"$EXT_ID" >/dev/null 2>&1; }
choice() { local c="${TROI_BROWSER:-$(cat "$CHOICE" 2>/dev/null)}"; c="$(printf '%s' "${c:-auto}" | tr -d '[:space:]')"; [ "$c" = chrome ] && c=own; echo "$c"; }
mode() {
  case "$(choice)" in
    arc)   [ -d "$ARC" ] && echo arc || echo own;;
    yours) echo yours;;
    own)   echo own;;
    *)     if extension_installed; then echo yours; else echo own; fi;;
  esac
}
MODE="$(mode)"
case "$MODE" in
  arc) APP="$ARC"; NAME="Arc"; PROFILE="";;
  *)   APP="$CHROME"; NAME="Google Chrome"; PROFILE="$BROWSER";;
esac
export TROI_BROWSER_APP="$NAME"

cdp_up() { curl -s -m 2 "http://127.0.0.1:$PORT/json/version" >/dev/null; }
port_owner() { local pid; pid="$(lsof -t -i ":$PORT" -sTCP:LISTEN 2>/dev/null | head -1)"; [ -n "$pid" ] && ps -o comm= -p "$pid" | sed 's#.*/##'; }
quit_arc() { osascript -e 'tell application "Arc" to quit' >/dev/null 2>&1; for i in $(seq 1 40); do pgrep -xq Arc || return 0; sleep 0.5; done; return 1; }
describe() {
  case "$MODE" in
    own)   echo "Google Chrome, the agent's own (profile $PROFILE, port $PORT; the console's Browser page mirrors it)";;
    yours) echo "Google Chrome, yours, through the Playwright extension (your logins; no port, so no live view on the console)";;
    arc)   echo "Arc, yours, on port $PORT (the old way)";;
  esac
}

ensure_browser() {
  if [ "$MODE" = yours ]; then pgrep -xq "Google Chrome" || open -a "$CHROME" 2>/dev/null; return 0; fi
  if cdp_up; then
    local who; who="$(port_owner)"
    case "$MODE:$who" in
      own:*Chrome*|arc:Arc) return 0;;                                                 # the right browser holds the port
      own:Arc) quit_arc || { echo "Arc holds port $PORT and did not quit; quit it yourself, then try again" >&2; return 1; };;   # the old browser: a polite quit; its tabs come back when it is next opened
      *) echo "port $PORT is held by ${who:-something else}; the browser tools take it as they find it" >&2; return 0;;
    esac
  fi
  if [ "$MODE" = arc ] && pgrep -xq Arc; then
    # Arc is open without its port (started from the Dock): a polite quit; it restores its tabs and spaces on the way back
    quit_arc || { echo "Arc did not quit; it needs its debugging port (quit Arc, then try again)" >&2; return 1; }
  fi
  if [ -n "$PROFILE" ]; then
    # a Chrome of the agent's own: its own profile, its own window (a second instance beside the owner's Chrome, if that is open);
    # its first tab is the console when the console already answers, so the window never opens empty
    mkdir -p "$PROFILE"
    local first="about:blank"; curl -s -m 1 -o /dev/null "$CONSOLE_URL" && first="$CONSOLE_URL"
    open -na "$APP" --args --remote-debugging-port=$PORT --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
      --window-size=1280,900 --window-position=80,60 "$first" 2>/dev/null
  else
    # the owner's Arc: the port and nothing else, so it comes back with its own windows and spaces, not one more of ours
    open -na "$APP" --args --remote-debugging-port=$PORT --no-first-run --no-default-browser-check 2>/dev/null
  fi
  for i in $(seq 1 80); do cdp_up && { open -a "$APP" 2>/dev/null; return 0; }; sleep 0.5; done
  echo "$NAME did not answer on port $PORT" >&2; return 1
}

# the console's tab in the agent's browser, exactly one: over the debugging protocol (node's own WebSocket for the navigation),
# because `open <url>` goes to the Mac's default browser and `open -a` cannot pick the tab
console_tab() {
  local url="${1:-$CONSOLE_URL}"
  for i in $(seq 1 120); do curl -s -m 1 -o /dev/null "$url" && break; sleep 0.5; done          # the console app first
  if [ "$MODE" = yours ]; then open -a "$CHROME" "$url" 2>/dev/null; echo "the console is open in your Chrome: $url"; return 0; fi
  ensure_browser || return 1
  node - "http://127.0.0.1:$PORT" "$url" <<'JS'
const [CDP, TARGET] = process.argv.slice(2);
const mine = u => /\/\/(localhost|127\.0\.0\.1):(3100|8796|8794|8790)\b/.test(u) || u === TARGET;
(async () => {
  const tabs = (await (await fetch(CDP + "/json/list")).json()).filter(t => t.type === "page");
  const ours = tabs.filter(t => mine(t.url)), blank = tabs.find(t => t.url === "about:blank" || t.url === "chrome://newtab/");
  const navigate = async t => { const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
    ws.send(JSON.stringify({ id: 1, method: "Page.navigate", params: { url: TARGET } })); await new Promise(ok => { ws.onmessage = ok; setTimeout(ok, 3000); }); ws.close(); };
  let keep = ours[0];
  if (keep) { await navigate(keep); for (const t of ours.slice(1)) await fetch(CDP + "/json/close/" + t.id); }   // one console tab: the first stays and reloads, the spares go
  else if (blank) { keep = blank; await navigate(blank); }
  else { keep = await (await fetch(CDP + "/json/new?" + encodeURIComponent(TARGET), { method: "PUT" })).json(); }
  await fetch(CDP + "/json/activate/" + keep.id);
  console.log(`the console tab: ${TARGET} (${ours.length > 1 ? ours.length - 1 + " spare tab(s) closed" : ours.length ? "reused" : blank ? "took the blank tab" : "a new tab"})`);
})().catch(e => { console.error("console tab: " + e.message); process.exit(1); });
JS
  open -a "$APP" 2>/dev/null
}

case "${1:-mcp}" in
  chrome|open) ensure_browser && echo "the agent's browser is up: $(describe)";;
  console) console_tab "$2";;
  which)  echo "$NAME";;
  describe) describe;;
  status)
    echo "choice: $(choice) -> $MODE"; echo "browser: $(describe)"
    echo "Playwright extension in your Chrome: $(extension_installed && echo yes || echo "no ($EXT_URL)")"
    if cdp_up; then echo "port $PORT: $(port_owner) answers"; else echo "port $PORT: nothing"; fi
    pgrep -xq "Google Chrome" && echo "Chrome: running" || echo "Chrome: not running";;
  use)
    case "$2" in
      own|yours|arc|auto)
        mkdir -p "$DATA"; printf '%s\n' "$2" >"$CHOICE"
        echo "kept: $2 -> $("$0" describe). It takes effect when the browser tools next start (the next troi)."
        [ "$2" = yours ] && ! extension_installed && echo "the Playwright extension is not in your Chrome yet: $EXT_URL"
        [ "$2" = arc ] && [ ! -d "$ARC" ] && echo "Arc is not installed; the agent's own Chrome it is"
        true;;
      *) echo "browser-mcp.sh use own|yours|arc|auto"; exit 1;;
    esac;;
  bridge)
    if [ "$MODE" = yours ]; then echo "no live view: your own Chrome has no debugging port (the Browser page mirrors only the agent's own Chrome)"; exit 0; fi
    ensure_browser; exec node "$HERE/browser.js";;
  *)
    ensure_browser
    if [ "$MODE" = yours ]; then exec npx -y @playwright/mcp@latest --extension; fi
    exec npx -y @playwright/mcp@latest --cdp-endpoint "http://127.0.0.1:$PORT";;
esac
