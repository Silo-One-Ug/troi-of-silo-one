#!/bin/bash
# board-state.sh — the agent's EYES on the hands board (Silo One's version of barehands' script, copied over it by
# patch-board.sh so an upstream update keeps it). Read-only; reaches nothing but localhost; changes nothing.
#
#   board-state.sh            what is on the board now, one line per item: cards, pictures, notes, UI panels (with the
#                             parts inside); when the page is not open, the saved scene instead
#   board-state.sh events     the last taps on buttons and choices in UI panels (newest last)
#   board-state.sh json       the raw scene as JSON
#
# Based on the upstream board-state.sh by Jared Rhodenizer (AGPL-3.0-or-later).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYBIN=""
for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "pass" >/dev/null 2>&1; then
        PYBIN="$c"; break
    fi
done
if [ -z "$PYBIN" ] && [ -x "$DIR/../backtalk/.venv/bin/python" ]; then
    PYBIN="$DIR/../backtalk/.venv/bin/python"
fi
if [ -z "$PYBIN" ]; then
    echo "No working Python found (tried python3, python, py)." >&2
    exit 1
fi
PORT=$("$PYBIN" -c "import json;print(json.load(open('$DIR/barehands.json')).get('port',8794))" 2>/dev/null || echo 8794)
PORT="${BOARD_PORT:-$PORT}"
MODE="${1:-items}"
STATE=$(curl -sS --max-time 3 "http://127.0.0.1:$PORT/state" 2>/dev/null) || {
    echo "The board is dark — the board server isn't running."; exit 1; }
SCENE=$(curl -sS --max-time 3 "http://127.0.0.1:$PORT/scene" 2>/dev/null || echo "{}")
EVENTS=$(curl -sS --max-time 3 "http://127.0.0.1:$PORT/events" 2>/dev/null || echo "{}")
export STATE SCENE EVENTS MODE
"$PYBIN" <<'PY'
import json, os, time

def load(s):
    try:
        return json.loads(s) or {}
    except ValueError:
        return {}

state, scene, events, mode = load(os.environ["STATE"]), load(os.environ["SCENE"]), load(os.environ["EVENTS"]), os.environ["MODE"]
specs = scene.get("ui") or {}

if mode == "json":
    print(json.dumps({"live": bool(state.get("items")), "items": state.get("items") or scene.get("items") or [], "ui": specs}, indent=1))
    raise SystemExit

if mode == "events":
    ev = events.get("events") or []
    if not ev:
        print("No taps on the board's panels yet."); raise SystemExit
    print(f"TAPS ON THE BOARD — the last {len(ev)}:")
    for e in ev:
        when = time.strftime("%H:%M:%S", time.localtime(e.get("t", 0)))
        verb = "chose" if e.get("kind") == "choice" else "tapped"
        extra = f" (action: {e['action']})" if e.get("action") and e.get("action") != e.get("label") else ""
        print(f'  {when}  {verb} "{e.get("label", "")}" on "{e.get("title", "")}"{extra}')
    raise SystemExit

items = state.get("items") or []
live = bool(items)
saved = scene.get("items") or []
if not live and saved:
    items = saved
if not items:
    print("The board is EMPTY" + (" (as of the tracker's last heartbeat)." if state else ": the page has not connected yet and nothing is saved."))
    raise SystemExit

def zone(x, y):
    h = "left" if x < 0.33 else ("center" if x < 0.67 else "right")
    v = "top" if y < 0.33 else ("middle" if y < 0.67 else "bottom")
    return "center" if (h == "center" and v == "middle") else f"{v}-{h}"

def parts(node, out, depth=0):
    """The component types inside a tree, with a size where it matters."""
    if not isinstance(node, dict) or depth > 10:
        return out
    t = node.get("type")
    if t:
        n = node.get("items") if isinstance(node.get("items"), list) else node.get("rows") if isinstance(node.get("rows"), list) else node.get("data") if isinstance(node.get("data"), list) else None
        label = t
        if t == "chart":
            label = f"{node.get('kind', 'line')} chart"
        if n is not None and t in ("table", "chart", "gallery", "slideshow", "carousel", "list", "tabs", "accordion", "steps", "timeline", "kv", "avatars", "choice", "tags"):
            label += f"({len(n)})"
        if t in ("stat", "progress", "gauge", "badge", "button", "countdown", "clock", "heading") and node.get("label") or node.get("text") and t in ("heading", "badge", "button", "callout"):
            label += f' "{str(node.get("label") or node.get("text") or "")[:24]}"'
        out.append(label)
    for c in node.get("children") or []:
        parts(c, out, depth + 1)
    if isinstance(node.get("child"), dict):
        parts(node["child"], out, depth + 1)
    for it in node.get("items") or []:
        if isinstance(it, dict) and isinstance(it.get("child"), dict):
            parts(it["child"], out, depth + 1)
    return out

head = f"ON THE BOARD — {len(items)} item(s), " + ("last tracker heartbeat:" if live else "the SAVED scene (the board page is not open; it comes back when it is):")
print(head)
for i in items:
    t = i.get("type", "?")
    title = i.get("title") or ""
    src = os.path.basename(i.get("src") or "")
    if i.get("ui"):
        spec = (specs.get(i.get("uid")) or {}).get("spec")
        inside = parts(spec, []) if spec else []
        desc = f'UI panel "{title}"'
        if inside:
            shown = inside[1:] if len(inside) > 1 and inside[0] in ("stack", "grid", "card", "row", "columns") else inside
            desc += " — " + ", ".join(shown[:12]) + (" …" if len(shown) > 12 else "")
        us = i.get("us") or {}
        if isinstance(us, dict) and us:
            desc += "  [state: " + ", ".join(f"{k}={v}" for k, v in list(us.items())[:4]) + "]"
    elif t == "card":
        body = (i.get("body") or "").replace("\n", " ")[:70]
        desc = f'card "{title}"' + (f" — {body}" if body else "")
    elif t == "img":
        desc = f"image {src}" + (f' "{title}"' if title else "") + (" (fx, frameless)" if i.get("fxf") else "") + (" (video)" if i.get("vd") else "")
    elif t == "model":
        mode_ = "hologram wireframe" if i.get("mm") == "holo" else "solid"
        desc = f"3D model {src} ({mode_})"
        ex = i.get("ex") or 0
        if ex > 0.02:
            desc += f", EXPLODED {round(ex * 100)}%"
    elif t == "panel":
        desc = f'open note "{title}"'
    elif t == "browser":
        desc = f'file browser "{title}"'
    elif t == "widget":
        desc = "a widget"
    elif t == "orb":
        desc = f'orb "{title}"'
    else:
        desc = f'{t} "{title or src}"'
    flags = []
    if i.get("g"):
        flags.append("IN THE USER'S HAND")
    if i.get("pres"):
        flags.append("SPOTLIT")
    sc = i.get("scale") or 1
    if sc >= 1.6:
        flags.append("blown up large")
    elif sc <= 0.55:
        flags.append("shrunk small")
    op = i.get("op", 1)
    if op is not None and op < 0.5:
        flags.append("faded out")
    pos = zone(i.get("x") or 0.5, i.get("y") or 0.5)
    line = f"  - {desc} @ {pos}"
    if flags:
        line += "  [" + ", ".join(flags) + "]"
    print(line)
ev = [e for e in (events.get("events") or []) if time.time() - e.get("t", 0) < 900]
if ev:
    print(f"TAPS in the last 15 minutes: " + "; ".join(f'"{e.get("label", "")}" on "{e.get("title", "")}"' for e in ev[-5:]))
PY
