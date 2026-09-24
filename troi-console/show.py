#!/usr/bin/env python3
"""show.py: draw on the console's conversation. Stdlib only.
The agent hands over a component tree (JSON) and the console renders it as interface: cards, stats, progress,
tables, charts (line, bar, area, pie), lists, key-values, badges, callouts, images and galleries, links, tabs,
a YouTube or Vimeo player, a map by coordinates. No HTML files, no screenshots of them.

  show.py '<json tree>' [--title "..."]      one tree, e.g. '{"type":"grid","cols":3,"children":[{"type":"stat","label":"Rain","value":"42 mm"}]}'
  show.py --file tree.json [--title "..."]   the tree from a file
  show.py chart line|bar|area|pie "<title>" "<x key>" "<series keys, comma>" '<data json>'   a chart in one line
  show.py table "<title>" "<columns, comma>" '<rows json>'                                  a table in one line
  show.py vocabulary                                                                          the components and their fields

Components: stack (children, gap) · grid (cols 1-4, children) · card (title, subtitle, children, footer) · heading (text, level)
· text (text; **bold**, *italic*; muted) · badge (text, tone ok|note|warn) · link (text, href) · divider · image (url, title, credit, href)
· gallery (items [{url, title, credit, href}]) · stat (label, value, delta, tone, note) · progress (label, value 0-100)
· kv (items [{k, v}]) · list (items, ordered) · table (columns, rows, caption) · chart (kind line|bar|area|pie, data [{...}], x, series [keys], title)
· tabs (items [{label, child}]) · embed (url: YouTube/Vimeo link or https page) · map (lat, lon, zoom, label) · callout (text, tone, title)
Local pictures: url may be a file path under data/blobs or the vault; the console serves it.
"""
import json
import sys
import time
import urllib.parse
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
TYPES = {"stack", "grid", "card", "heading", "text", "badge", "link", "divider", "image", "gallery", "stat", "progress", "kv", "list", "table", "chart", "tabs", "embed", "video", "audio", "map", "callout"}


def clean(node, depth=0):
    if depth > 8 or not isinstance(node, dict) or node.get("type") not in TYPES:
        return None
    out = {k: v for k, v in node.items() if k not in ("children", "items", "child")}
    for k in ("url", "href"):
        if k in out and isinstance(out[k], str):
            u = out[k].strip()
            if u.startswith("/") or u.startswith("~"):                     # a file on this Mac: served by the console
                u = "/img?p=" + urllib.parse.quote(str(Path(u).expanduser()))
            elif not u.startswith(("https://", "http://", "/img?")):
                u = ""
            out[k] = u
    if isinstance(node.get("children"), list):
        out["children"] = [c for c in (clean(c, depth + 1) for c in node["children"]) if c]
    if "child" in node:
        out["child"] = clean(node["child"], depth + 1)
    if isinstance(node.get("items"), list):
        items = []
        for it in node["items"][:80]:
            if isinstance(it, dict):
                it = dict(it)
                for k in ("url", "href"):
                    if k in it and isinstance(it[k], str):
                        u = it[k].strip()
                        if u.startswith("/") or u.startswith("~"):
                            u = "/img?p=" + urllib.parse.quote(str(Path(u).expanduser()))
                        elif not u.startswith(("https://", "http://", "/img?")):
                            u = ""
                        it[k] = u
                if "child" in it:
                    it["child"] = clean(it["child"], depth + 1)
                items.append(it)
            elif isinstance(it, (str, int, float)):
                items.append(it)
        out["items"] = items
    return out


def count(n):
    return 1 + sum(count(c) for c in n.get("children", []) or []) + (count(n["child"]) if n.get("child") else 0) + sum(count(i["child"]) for i in (n.get("items") or []) if isinstance(i, dict) and i.get("child"))


def show(tree, title=""):
    spec = clean(tree)
    if not spec:
        print("nothing to show: no known component in the tree (show.py vocabulary)"); return 1
    c = P.CACHE; c.mkdir(exist_ok=True)
    with (c / "cards.jsonl").open("a") as f:
        f.write(json.dumps({"name": "silo.ui", "value": {"title": title, "spec": spec}, "t": time.time()}) + "\n")
    print(f"on the console: {count(spec)} components{' · ' + title if title else ''}. Say a line about it; do not repeat it as text.")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    title = ""
    if "--title" in a:
        i = a.index("--title"); title = a[i + 1] if i + 1 < len(a) else ""; a = a[:i] + a[i + 2:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if a[0] == "vocabulary":
        print(__doc__.split("Components:", 1)[1]); sys.exit(0)
    if a[0] == "--file":
        sys.exit(show(json.loads(Path(a[1]).read_text()), title))
    if a[0] == "chart" and len(a) >= 6:
        sys.exit(show({"type": "chart", "kind": a[1], "title": a[2], "x": a[3], "series": [s.strip() for s in a[4].split(",") if s.strip()], "data": json.loads(a[5])}, title))
    if a[0] == "table" and len(a) >= 4:
        sys.exit(show({"type": "table", "caption": a[1], "columns": [c.strip() for c in a[2].split(",")], "rows": json.loads(a[3])}, title))
    try:
        sys.exit(show(json.loads(a[0]), title))
    except json.JSONDecodeError as e:
        print(f"that is not JSON: {e}"); sys.exit(2)
