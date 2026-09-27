#!/usr/bin/env python3
"""The browser, deeper (Silo One, 2026-09-27): the agent's own Chrome, on its debugging port, seen as tabs, history and bookmarks.

  browse.py tabs                         the open tabs (the console's tab marked; the working tab first)
  browse.py dupes [--close]              tabs on the same page; --close closes the spares (never the first of a group, never the
                                         console's tab), and only at the owner's word
  browse.py open <https-url>             a tab of the agent's own
  browse.py history <words> [--days 30]  the agent's Chrome history by title or address; a copy of the History file is read, never the live one
  browse.py bookmark add <url> [--title "…"] [--tags a,b]     the agent's own bookmarks (data/bookmarks.json); the page's title is fetched when none is given
  browse.py bookmark list | find <words> | tag <n> <tags>

The owner's own browser (Comet, or their Chrome) is theirs: nothing here reads its history or bookmarks. Stdlib only; the
port is the bridge's (9223, browser-mcp.sh). Closing a tab is the one thing here that changes anything, and it needs --close.
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

PORT = 9223
PROFILE = P.DATA / "browser" / "Default"
BOOKMARKS = P.DATA / "bookmarks.json"
CONSOLE = re.compile(r"^https?://(localhost|127\.0\.0\.1):3100(/|$)")


def cdp(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=8) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip().startswith(("[", "{")) else body


def pages():
    try:
        t = cdp("/json/list")
    except Exception:
        print("my browser is not up on its port; browser-mcp.sh open starts it"); sys.exit(1)
    return [x for x in t if x.get("type") == "page" and not str(x.get("url", "")).startswith(("chrome://", "devtools://", "chrome-extension://"))]


def short(u, n=90):
    u = re.sub(r"^https?://(www\.)?", "", str(u))
    return u if len(u) <= n else u[:n - 1] + "…"


def cmd_tabs():
    ps = pages()
    if not ps:
        print("no tabs open"); return 0
    for i, p in enumerate(ps, 1):
        mark = "  (the console)" if CONSOLE.match(p.get("url", "")) else ""
        print(f"{i:>2}. {str(p.get('title') or '')[:60]:<60}  {short(p.get('url', ''))}{mark}")
    return 0


def norm_url(u):
    u = str(u).strip()
    u = re.sub(r"#.*$", "", u); u = re.sub(r"^https?://(www\.)?", "", u).rstrip("/")
    return u.lower()


def cmd_dupes(close):
    ps = pages(); groups = {}
    for p in ps:
        groups.setdefault(norm_url(p.get("url", "")), []).append(p)
    dup = {k: v for k, v in groups.items() if len(v) > 1 and k}
    if not dup:
        print(f"no duplicate tabs among {len(ps)}"); return 0
    spare = sum(len(v) - 1 for v in dup.values())
    print(f"{len(dup)} page{'s' if len(dup) != 1 else ''} open more than once, {spare} spare tab{'s' if spare != 1 else ''}:")
    closed = 0
    for k, v in dup.items():
        print(f"  x{len(v)}  {str(v[0].get('title') or '')[:50]}  {short(k)}")
        if close:
            for p in v[1:]:
                if CONSOLE.match(p.get("url", "")):
                    continue
                try:
                    cdp(f"/json/close/{p['id']}"); closed += 1
                except Exception as e:
                    print(f"      could not close one: {str(e)[:80]}")
    if close:
        print(f"closed {closed} spare tab{'s' if closed != 1 else ''}; the first of each page stays")
    else:
        print("nothing closed: browse.py dupes --close closes the spares, at the owner's word")
    return 0


def cmd_open(url):
    if not str(url).lower().startswith("https://"):
        print("https only"); return 2
    try:
        t = cdp("/json/new?" + urllib.parse.quote(url, safe=":/?&=%#"), method="PUT")
    except Exception as e:
        print(f"could not open a tab: {str(e)[:120]}"); return 1
    print(f"opened: {short(url)}" + (f"  (tab {t.get('id', '')[:8]})" if isinstance(t, dict) else "")); return 0


def chrome_time(us):
    """Chrome's clock: microseconds since 1601-01-01."""
    try:
        return datetime(1601, 1, 1) + timedelta(microseconds=int(us))
    except Exception:
        return None


def cmd_history(words, days):
    src = PROFILE / "History"
    if not src.exists():
        print("no history yet: my browser has not been used"); return 0
    tmp = Path(tempfile.mkdtemp())
    try:
        shutil.copy2(src, tmp / "History")
        for extra in ("History-wal", "History-journal"):
            if (src.parent / extra).exists():
                shutil.copy2(src.parent / extra, tmp / extra)
        con = sqlite3.connect(str(tmp / "History"))
        since = int((datetime.utcnow() - datetime(1601, 1, 1) - timedelta(days=days)).total_seconds() * 1_000_000)
        like = "%" + "%".join(words) + "%"
        rows = con.execute("select url, title, last_visit_time, visit_count from urls where (lower(title) like lower(?) or lower(url) like lower(?)) and last_visit_time >= ? "
                           "order by last_visit_time desc limit 40", (like, like, since)).fetchall()
        con.close()
    except Exception as e:
        print(f"the history could not be read: {str(e)[:120]}"); return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not rows:
        print(f"nothing in my history for \"{' '.join(words)}\" in the last {days} days"); return 0
    print(f"{len(rows)} page{'s' if len(rows) != 1 else ''} in my history for \"{' '.join(words)}\":")
    for url, title, t, n in rows:
        when = chrome_time(t); ago = when.strftime("%a %d %b %H:%M") if when else "?"
        print(f"  {ago}  {str(title or '')[:50]:<50}  {short(url, 70)}" + (f"  x{n}" if n and n > 1 else ""))
    return 0


def load_bm():
    try:
        d = json.loads(BOOKMARKS.read_text())
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_bm(items):
    BOOKMARKS.parent.mkdir(parents=True, exist_ok=True)
    BOOKMARKS.write_text(json.dumps(items, indent=2, ensure_ascii=False))


def fetch_title(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) Troi"})
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read(200_000).decode("utf-8", "replace")
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        return " ".join(m.group(1).split())[:120] if m else ""
    except Exception:
        return ""


def cmd_bookmark(a):
    a = list(a)
    if not a:
        print('browse.py bookmark add <url> [--title "…"] [--tags a,b] | list | find <words> | tag <n> <tags>'); return 2
    if a[0] == "add":
        title = tags = None
        if "--title" in a:
            i = a.index("--title"); title = a[i + 1]; del a[i:i + 2]
        if "--tags" in a:
            i = a.index("--tags"); tags = a[i + 1]; del a[i:i + 2]
        if len(a) < 2 or not a[1].lower().startswith("https://"):
            print("browse.py bookmark add <https-url> [--title …] [--tags a,b]"); return 2
        url = a[1].strip(); items = load_bm()
        if any(norm_url(b.get("url")) == norm_url(url) for b in items):
            print("already bookmarked: " + short(url)); return 0
        title = title or fetch_title(url) or short(url, 60)
        items.append({"url": url, "title": title, "tags": [t.strip() for t in (tags or "").split(",") if t.strip()], "added": time.time()})
        save_bm(items); print(f"bookmarked #{len(items)}: {title}  {short(url)}" + (f"  [{tags}]" if tags else "")); return 0
    if a[0] == "list":
        items = load_bm()
        if not items:
            print("no bookmarks yet"); return 0
        for i, b in enumerate(items, 1):
            if b.get("archived") and "--all" not in a:
                continue
            print(f"{i:>3}. {str(b.get('title') or '')[:55]:<55}  {short(b.get('url', ''), 60)}" + (f"  [{', '.join(b.get('tags') or [])}]" if b.get("tags") else "") + ("  (archived)" if b.get("archived") else ""))
        return 0
    if a[0] == "archive" and len(a) > 1:                             # the undo of a bookmark: kept, out of the list (nothing is deleted)
        items = load_bm(); n = int(a[1]) - 1
        if not (0 <= n < len(items)):
            print("no such bookmark"); return 2
        items[n]["archived"] = True; save_bm(items); print(f"#{n + 1} archived: {items[n].get('title', '')[:60]}"); return 0
    if a[0] == "find" and len(a) > 1:
        words = [w.lower() for w in a[1:]]; hits = []
        for i, b in enumerate(load_bm(), 1):
            hay = " ".join([str(b.get("title") or ""), str(b.get("url") or ""), " ".join(b.get("tags") or [])]).lower()
            if all(w in hay for w in words):
                hits.append((i, b))
        if not hits:
            print("no bookmark matches " + " ".join(a[1:])); return 0
        for i, b in hits:
            print(f"{i:>3}. {str(b.get('title') or '')[:55]:<55}  {short(b.get('url', ''), 60)}" + (f"  [{', '.join(b.get('tags') or [])}]" if b.get("tags") else ""))
        return 0
    if a[0] == "tag" and len(a) > 2:
        items = load_bm(); n = int(a[1]) - 1
        if not (0 <= n < len(items)):
            print("no such bookmark"); return 2
        new = [t.strip() for t in " ".join(a[2:]).split(",") if t.strip()]
        items[n]["tags"] = sorted(set((items[n].get("tags") or []) + new)); save_bm(items)
        print(f"#{n + 1} tagged: {', '.join(items[n]['tags'])}"); return 0
    print('browse.py bookmark add <url> [--title "…"] [--tags a,b] | list | find <words> | tag <n> <tags>'); return 2


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "tabs":
        return cmd_tabs()
    if a[0] == "dupes":
        return cmd_dupes("--close" in a)
    if a[0] == "open" and len(a) > 1:
        return cmd_open(a[1])
    if a[0] == "history" and len(a) > 1:
        days = 30
        if "--days" in a:
            i = a.index("--days"); days = int(a[i + 1]); del a[i:i + 2]
        return cmd_history(a[1:], days)
    if a[0] == "bookmark":
        return cmd_bookmark(a[1:])
    print("browse.py tabs | dupes [--close] | open <url> | history <words> [--days 30] | bookmark add|list|find|tag"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
