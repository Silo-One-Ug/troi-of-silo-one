#!/usr/bin/env python3
"""show.py: draw interface from data, in the console's conversation or on the hands board. Stdlib only.
The agent hands over a component tree (JSON) and it is rendered as interface, never as an HTML file or a screenshot.
One vocabulary, two surfaces: the conversation (the console's own components) and the board (a white, full-width page of
tiles the owner moves with the mouse; a tile can be dragged, resized, spotlit and clicked).

  show.py '<json tree>' [--title "..."]                          in the conversation
  show.py '<json tree>' --board [--title "..."] [--x 0.5 --y 0.45] [--w 0.3] [--h 0.6] [--aspect 16:9] [--scroll] [--present] [--hand] [--clear] [--hidebar]
  show.py '<json tree>' --both [...]                              both at once
  show.py --file tree.json [...]                                  the tree from a file
  show.py chart line|bar|area|pie|donut "<title>" "<x key>" "<series keys, comma>" '<data json>' [--board]     a chart in one line
  show.py table "<title>" "<columns, comma>" '<rows json>' [--board]                                          a table in one line
  show.py board "<title>" next|prev|goto N|play|pause|toggle|mute|unmute|seek S|scroll up|down|top|bottom|close|present|unpresent|hover [--id part]
  show.py board tidy | clear                                      line every tile up | put everything away
  show.py board "<title>" set '<json tree>'                       a new tree in the same panel (a live dashboard)
  show.py board "<title>" state '<json>'                          set tabs, slides or choices by key
  show.py board "<title>" move --x 0.7 --y 0.4  |  size --w 0.4  |  rename "<new title>"
  show.py vocabulary                                              the components and their fields

Board sizes are fractions of the screen: --w is the tile's width (default 0.3; 1 = the full width), --h its height (its body
scrolls; --scroll asks for that), --aspect fixes its shape. Without --x and --y a tile flows into the first free space, in
reading order; `show.py board tidy` lines everything up. A tile's body scrolls by itself when the tree is taller than the screen.

Components (both surfaces unless marked):
  layout    stack (children, gap sm|lg) · row (children, align, justify, wrap) · grid (cols 1-6, children) · columns (weights [2,1], children)
            card (title, subtitle, footer, tone, children) · group (title, children) · tabs (items [{label, child}], active)
            accordion (items [{label, child|text, note, open}], single) · slideshow (items [{url, caption}|component], interval s, autoplay, aspect, fit, title)
            steps (items [{title, body, status done|current|todo}], current) · timeline (items [{time, title, body, tone}])
            divider (label) · spacer (h px) · aspect (ratio, child) · hero (src, title, subtitle, kicker, aspect)
  text      heading (text, level 1-4, align) · text (text with **bold** *italic* `code` [link](https://…); size sm|md|lg|xl, muted, align, mono)
            md (text: block markdown with headings, lists, checklists, quotes, fences, pipe tables) · quote (text, cite) · code (text, lang, title)
            kbd (keys) · badge (text, tone ok|note|warn|bad|muted) · tags (items, tone) · callout (title, text, tone) · link (text, href)
  data      stat (label, value, unit, delta, tone, note, spark [numbers]) · progress (label, value, max, tone, text) · gauge (value, min, max, unit, label, tone)
            kv (items [{k, v}] or {k: v}) · list (items [text | {text, done, note}], ordered, check) · table (columns [name | {label, key, align}], rows, caption, highlight [row indexes], footer, zebra, compact)
            chart (kind line|bar|area|pie|donut|scatter, data [{...}], x, series [keys], stacked, colors, title, unit, height, ymin, ymax, legend, center)
            sparkline (data, label, tone) · rating (value, max, label) · countdown (to ISO time, label, done) · clock (tz, label, seconds, h12)
            calendar (month YYYY-MM, marks [{date, label, tone}], title)
  media     image (url|src, fit cover|contain, aspect, radius, caption, credit) · gallery (items [{url, title, credit}], cols, aspect, fit, numbered)
            video (src, poster, autoplay, loop, muted, controls, aspect, fit, caption, id) · youtube (url|id, start, autoplay, mute, loop, aspect, name)
            vimeo (url|id, autoplay, loop, aspect, name) · audio (src, title, loop, id) · embed (url https, aspect, height, title) · map (lat, lon, zoom, label, aspect)
            avatar (url|name, initials, size, sub, tone) · avatars (items, max, size, label) · skeleton (lines)
  answer    button (label, action, tone, primary) · choice (label, options [label | {label, value}], value, action)   — a click reaches the agent as a "(board: …)" line
Pictures, video and audio on the board come from https or from files on this Mac (copied into the board's airlock); http links are refused.
"""
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
TYPES = {"stack", "row", "grid", "columns", "card", "group", "tabs", "accordion", "slideshow", "carousel", "steps", "timeline", "divider", "spacer", "aspect", "hero",
         "heading", "text", "md", "markdown", "quote", "code", "kbd", "badge", "tags", "callout", "link",
         "stat", "progress", "gauge", "meter", "kv", "list", "table", "chart", "sparkline", "rating", "countdown", "clock", "calendar",
         "image", "gallery", "video", "youtube", "vimeo", "audio", "embed", "web", "map", "avatar", "avatars", "skeleton", "button", "choice", "empty"}
ADDR = ("url", "src", "poster", "href", "page")
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".mp4", ".webm", ".mov", ".m4v", ".mp3", ".m4a", ".wav", ".ogg", ".oga", ".flac", ".glb", ".gltf"}
AIRLOCK = P.BAREHANDS / "media"


def board_port():
    try:
        import os
        if os.environ.get("BOARD_PORT"):
            return int(os.environ["BOARD_PORT"])
        return int(json.loads((P.BAREHANDS / "barehands.json").read_text()).get("port", 8794))
    except Exception:
        return 8794


def stage_file(path):
    """A file on this Mac into the board's airlock (media/ui/<day>/), so the board may show it; its airlock address back."""
    p = Path(path).expanduser()
    if not p.is_file() or p.suffix.lower() not in MEDIA_EXT:
        return ""
    try:
        d = AIRLOCK / "ui" / time.strftime("%Y-%m-%d"); d.mkdir(parents=True, exist_ok=True)
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in p.name)
        dst = d / name
        if not dst.exists() or dst.stat().st_size != p.stat().st_size:
            subprocess.run(["cp", "-f", str(p), str(dst)], check=True, capture_output=True)
        return "ui/" + d.name + "/" + name
    except Exception:
        return ""


def fix_addr(u, key, board):
    """Where a picture, a video or a link may come from: https, or a file on this Mac (served by the console, or staged into the airlock)."""
    u = str(u).strip()
    if not u:
        return ""
    if u.startswith("/") or u.startswith("~"):
        if key in ("href", "page"):
            return ""
        return stage_file(u) if board else "/img?p=" + urllib.parse.quote(str(Path(u).expanduser()))
    if u.startswith(("https://", "http://")):
        return u
    if u.startswith("/img?") and not board:
        return u
    if board and not u.startswith(("data:", "javascript:")):
        return u                                               # an airlock path such as misc/logo.png: the server checks it
    return ""


def clean(node, depth=0, board=False):
    if depth > 10 or not isinstance(node, dict) or node.get("type") not in TYPES:
        return None
    out = {}
    for k, v in node.items():
        if k in ("children", "items", "child"):
            continue
        if k in ADDR and isinstance(v, str):
            v = fix_addr(v, k, board)
        out[k] = v
    if isinstance(node.get("children"), list):
        out["children"] = [c for c in (clean(c, depth + 1, board) for c in node["children"][:200]) if c]
    if "child" in node:
        out["child"] = clean(node["child"], depth + 1, board)
    if isinstance(node.get("items"), list):
        items = []
        for it in node["items"][:600]:
            if isinstance(it, dict):
                if it.get("type") in TYPES and node.get("type") in ("slideshow", "carousel"):
                    c = clean(it, depth + 1, board)
                    if c:
                        items.append(c)
                    continue
                it = dict(it)
                for k in ADDR:
                    if k in it and isinstance(it[k], str):
                        it[k] = fix_addr(it[k], k, board)
                if "child" in it:
                    it["child"] = clean(it["child"], depth + 1, board)
                items.append(it)
            elif isinstance(it, (str, int, float)):
                items.append(it)
        out["items"] = items
    return out


def count(n):
    if not isinstance(n, dict):
        return 0
    return 1 + sum(count(c) for c in n.get("children", []) or []) + (count(n["child"]) if n.get("child") else 0) \
        + sum(count(i["child"]) if isinstance(i, dict) and i.get("child") else (count(i) if isinstance(i, dict) and i.get("type") else 0) for i in (n.get("items") or []))


def to_console(tree, title=""):
    spec = clean(tree)
    if not spec:
        print("nothing to show: no known component in the tree (show.py vocabulary)"); return 1
    c = P.CACHE; c.mkdir(exist_ok=True)
    with (c / "cards.jsonl").open("a") as f:
        f.write(json.dumps({"name": "silo.ui", "value": {"title": title, "spec": spec}, "t": time.time()}) + "\n")
    print(f"on the console: {count(spec)} components{' · ' + title if title else ''}. Say a line about it; do not repeat it as text.")
    return 0


def board_send(cmd):
    req = urllib.request.Request(f"http://127.0.0.1:{board_port()}/cmd", data=json.dumps(cmd).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status < 300, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body).get("error", body)
        except ValueError:
            pass
        return False, body.strip() or f"the board said {e.code}"
    except Exception:
        return False, "the hands board is not up"


def to_board(tree, title, opt):
    spec = clean(tree, board=True)
    if not spec:
        print("nothing to show: no known component in the tree (show.py vocabulary)"); return 1
    if opt.get("clear"):
        board_send({"a": "clear"})
    cmd = {"a": "add_ui", "title": title or spec.get("title") or "PANEL", "spec": spec}
    for k in ("x", "y", "w", "h"):
        if opt.get(k) is not None:
            cmd[k] = float(opt[k])
    if opt.get("aspect"):
        cmd["aspect"] = opt["aspect"]
    for k in ("scroll", "present", "hand", "hidebar"):
        if opt.get(k):
            cmd[k] = 1
    ok, err = board_send(cmd)
    if not ok:
        print(f"the board refused it: {err}"); return 1
    print(f"on the board: \"{cmd['title']}\" ({count(spec)} components{', spotlit' if opt.get('present') else ''}). Say a line about it; console.sh view hands shows the board.")
    return 0


def board_op(title, op, arg, opt):
    cmd = {"a": "ui", "title": title}
    if op in ("next", "prev", "play", "pause", "toggle", "mute", "unmute", "close", "present", "unpresent", "hover"):
        cmd["op"] = op
    elif op == "goto":
        cmd["op"] = "goto"; cmd["i"] = int(arg or 0)
    elif op == "seek":
        cmd["op"] = "seek"; cmd["t"] = float(arg or 0)
    elif op == "scroll":
        cmd["op"] = "scroll"; cmd["dir"] = arg or "down"
    elif op == "set":
        spec = clean(json.loads(arg), board=True)
        if not spec:
            print("nothing to set: no known component in the tree"); return 1
        cmd["spec"] = spec
    elif op == "state":
        cmd["state"] = json.loads(arg)
    elif op == "rename":
        cmd["name"] = arg or ""
    elif op in ("move", "size"):
        pass
    else:
        print(f"unknown board op: {op}"); return 2
    for k in ("x", "y", "w"):
        if opt.get(k) is not None:
            cmd[k] = float(opt[k])
    if opt.get("id"):
        cmd["id"] = opt["id"]
    ok, err = board_send(cmd)
    print(f"board: {op} on \"{title}\"" if ok else f"the board refused it: {err}")
    return 0 if ok else 1


def parse(argv):
    """Flags out, positionals left: {--title T, --x N, ...}, [positionals]."""
    opt, pos, i = {}, [], 0
    valued = {"--title", "--x", "--y", "--w", "--h", "--aspect", "--id", "--file"}
    flags = {"--board", "--both", "--scroll", "--present", "--hand", "--clear", "--hidebar"}
    while i < len(argv):
        a = argv[i]
        if a in valued and i + 1 < len(argv):
            opt[a[2:]] = argv[i + 1]; i += 2
        elif a in flags:
            opt[a[2:]] = True; i += 1
        else:
            pos.append(a); i += 1
    return opt, pos


def main(argv):
    opt, a = parse(argv)
    title = opt.get("title", "")
    if (not a and not opt.get("file")) or (a and a[0] in ("-h", "--help")):
        print(__doc__); return 0
    if a and a[0] == "vocabulary":
        print(__doc__.split("Components (both surfaces unless marked):", 1)[1]); return 0
    if a and a[0] == "board":
        if len(a) == 2 and a[1] in ("tidy", "clear"):
            ok, err = board_send({"a": a[1]})
            print("board: " + ("tidied" if a[1] == "tidy" else "cleared") if ok else f"the board refused it: {err}"); return 0 if ok else 1
        if len(a) < 3:
            print('usage: show.py board "<title>" <op> [arg]   |   show.py board tidy|clear'); return 2
        return board_op(a[1], a[2], a[3] if len(a) > 3 else None, opt)
    if opt.get("file"):
        tree = json.loads(Path(opt["file"]).read_text())
    elif a[0] == "chart" and len(a) >= 6:
        tree = {"type": "chart", "kind": a[1], "title": a[2], "x": a[3], "series": [s.strip() for s in a[4].split(",") if s.strip()], "data": json.loads(a[5])}
        title = title or a[2]
    elif a[0] == "table" and len(a) >= 4:
        tree = {"type": "table", "caption": a[1], "columns": [c.strip() for c in a[2].split(",")], "rows": json.loads(a[3])}
        title = title or a[1]
    else:
        try:
            tree = json.loads(a[0])
        except json.JSONDecodeError as e:
            print(f"that is not JSON: {e}"); return 2
    if opt.get("board"):
        return to_board(tree, title, opt)
    if opt.get("both"):
        r1 = to_console(tree, title); r2 = to_board(tree, title, opt)
        return r1 or r2
    return to_console(tree, title)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
