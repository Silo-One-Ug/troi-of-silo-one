#!/bin/bash
# share.sh — the owner shares a screen or a window with the agent, as in a call: the Mac's own picker asks which, the pick
# streams at two frames a second into data/cache/share/live.jpg, and share.json says what is shared. The agent's screen
# sight (look-screen.sh) shows the shared content while a share is live, and the hands click on it with space "share".
#   share.sh start     open the picker (the owner picks a display, a window or an app); prints what was picked once it streams
#   share.sh stop      end the share (the menu bar's Stop Sharing and the picker's cancel end it too)
#   share.sh status    what is shared, since when, the last frame's age; or "not sharing"
#   share.sh build     compile the helper (share/share.swift) with Xcode's command line tools; start does it when missing
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; BIN="$HERE/share/share"; DIR="$DATA/cache/share"; INFO="$DIR/share.json"
mkdir -p "$DIR" "$DATA/logs"
build() { command -v xcrun >/dev/null || { echo "no Xcode command line tools: xcode-select --install"; return 1; }
  (cd "$HERE/share" && xcrun swiftc -O -swift-version 5 -framework ScreenCaptureKit -framework AppKit -framework CoreImage -framework CoreMedia share.swift -o share) || return 1; }
info() { python3 - "$INFO" <<'PY'
import json, sys, time
try: d = json.load(open(sys.argv[1]))
except Exception: print("not sharing"); sys.exit(1)
st = d.get("state", "")
what = d.get("title") or d.get("kind") or "content"; app = d.get("app") or ""
if st == "ended": print(f"not sharing (the last share ended: {d.get('why', '')})"); sys.exit(1)
if st in ("picking", "starting"): print("the picker is open, waiting for a pick"); sys.exit(2)
age = time.time() - float(d.get("last") or 0); since = time.strftime("%H:%M", time.localtime(float(d.get("since") or time.time())))
b = d.get("bounds") or {}; f = d.get("frame") or {}
print(f"sharing {d.get('kind','')} {what!r}{' of ' + app if app else ''} since {since}; last frame {age:.1f} s ago, {f.get('w','?')}x{f.get('h','?')} px of {int(b.get('w',0))}x{int(b.get('h',0))} points at {int(b.get('x',0))},{int(b.get('y',0))}")
sys.exit(0 if age < 5 else 3)
PY
}
alive() { [ -f "$INFO" ] && python3 -c 'import json,sys,time; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("state") in ("live","picking","starting") and time.time()-float(d.get("last") or d.get("since") or 0) < 10 else 1)' "$INFO" 2>/dev/null; }
case "${1:-status}" in
  build)  build && echo "built $BIN";;
  start)
    if alive; then info; exit 0; fi
    [ -x "$BIN" ] || build || exit 1
    nohup "$BIN" start "$DIR" >>"$DATA/logs/share.log" 2>&1 &
    sleep 1.5; info; rc=$?
    [ $rc = 2 ] && echo "say what to share in the picker; the agent sees it once it streams"
    exit 0;;
  stop)
    if alive; then
      touch "$DIR/stop"; for i in 1 2 3 4 5 6; do sleep 0.5; python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("state")=="ended" else 1)' "$INFO" 2>/dev/null && break; done
      info; echo "the share is over"
    else echo "nothing was being shared"; fi;;
  status) info;;
  *) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0";;
esac
