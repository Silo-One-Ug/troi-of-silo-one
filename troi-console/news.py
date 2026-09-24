#!/usr/bin/env python3
"""News research: Uganda first, then the world. Sources live in news.json (websites' feeds,
Google News, YouTube channels, and the social handles for the browser).

  news.py brief [uganda|world|all] [--n 4] [--hours 36] [--show]   the latest headlines per source (--show: a front page of cards on the board)
  news.py topic "<words>" [--n 8] [--hours 72]                     everything the sources have on a subject, plus a Google News search for Uganda
  news.py read <url> [--chars 6000]                                the article's text, for reading and summarising
  news.py videos <source> [--n 5]                                  the outlet's latest YouTube videos
  news.py social <source>                                          its handles (X, Facebook, YouTube), for the browser
  news.py sources                                                  what is configured, and which feeds answered last time

Standard library only; fetched feeds are cached for five minutes in data/cache/news.json.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
CFG = HERE / "news.json"
CACHE = P.CACHE / "news.json"
YTIDS = P.CACHE / "youtube-ids.json"
BOARD = HOME / "barehands" / "bin" / "board.sh"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) SiloOne/1.0 news reader", "Accept-Language": "en"}


def cfg():
    return json.loads(CFG.read_text())


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def when(s):
    """Feed dates in either RFC 822 or ISO form → epoch seconds (0 if unreadable)."""
    if not s:
        return 0
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def strip(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def parse_feed(data, source):
    """RSS 2.0 or Atom → [{title, link, time, summary, source}]."""
    items = []
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return items
    ns = {"a": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
    for it in root.iter("item"):
        title = strip(it.findtext("title")); link = (it.findtext("link") or "").strip()
        if not link:
            g = it.find("guid"); link = (g.text or "").strip() if g is not None and (g.text or "").startswith("http") else ""
        items.append({"title": title, "link": link, "time": when(it.findtext("pubDate") or it.findtext("{http://purl.org/dc/elements/1.1/}date")),
                      "summary": strip(it.findtext("description"))[:300], "source": source})
    for e in root.iter("{http://www.w3.org/2005/Atom}entry"):
        l = e.find("a:link", ns); link = l.get("href") if l is not None else ""
        items.append({"title": strip(e.findtext("a:title", default="", namespaces=ns)), "link": link, "time": when(e.findtext("a:published", default="", namespaces=ns) or e.findtext("a:updated", default="", namespaces=ns)),
                      "summary": strip(e.findtext("a:summary", default="", namespaces=ns) or e.findtext("media:group/media:description", default="", namespaces=ns))[:300], "source": source})
    return [i for i in items if i["title"]]


def gnews_url(query):
    return "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-UG&gl=UG&ceid=UG:en"


def fetch_source(src):
    urls = []
    if src.get("rss"):
        urls.append(src["rss"])
    if src.get("gnews"):
        urls.append(gnews_url(src["gnews"]))
    out, ok = [], False
    for u in urls:
        try:
            out += parse_feed(get(u), src["name"]); ok = True
        except Exception:
            pass
    return src["name"], out, ok


def load_all(groups, max_age=300):
    """All sources of the requested groups, from the cache when it is fresh."""
    c = cfg(); srcs = [s for g in groups for s in c.get(g, [])]
    try:
        cache = json.loads(CACHE.read_text())
    except Exception:
        cache = {"at": 0, "items": [], "ok": {}}
    if time.time() - cache.get("at", 0) < max_age and all(s["name"] in cache.get("ok", {}) for s in srcs):
        return [i for i in cache["items"] if i["source"] in {s["name"] for s in srcs}], cache["ok"]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch_source, srcs))
    items, ok = [], dict(cache.get("ok", {}))
    for name, its, good in results:
        ok[name] = good; items += its
    seen, uniq = set(), []
    for i in sorted(items, key=lambda i: -i["time"]):
        k = re.sub(r"\W+", "", i["title"].lower())[:60]
        if k in seen:
            continue
        seen.add(k); uniq.append(i)
    keep = [i for i in cache.get("items", []) if i["source"] not in {s["name"] for s in srcs}]
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps({"at": time.time(), "items": keep + uniq, "ok": ok}))
    return uniq, ok


def ago(t):
    if not t:
        return ""
    s = time.time() - t
    return f"{int(s // 60)}m ago" if s < 3600 else f"{int(s // 3600)}h ago" if s < 86400 else f"{int(s // 86400)}d ago"


def brief(groups, n, hours, show):
    items, ok = load_all(groups)
    cutoff = time.time() - hours * 3600
    by = {}
    for i in items:
        if i["time"] and i["time"] < cutoff:
            continue
        by.setdefault(i["source"], []).append(i)
    order = [s["name"] for g in groups for s in cfg().get(g, [])]
    lines, cards = [], []
    for name in order:
        its = by.get(name, [])[:n]
        if not its:
            older = [i for i in items if i["source"] == name][:2]
            if not older:
                lines.append(f"{name}: " + ("nothing found" if ok.get(name) else "feed did not answer")); continue
            lines.append(f"{name} (nothing in the last {hours}h; the newest it has)")
            for i in older:
                lines.append(f"  - {i['title']}  ({ago(i['time'])})  {i['link']}")
            continue
        lines.append(name)
        for i in its:
            lines.append(f"  - {i['title']}  ({ago(i['time'])})  {i['link']}")
        cards.append((name, [i["title"] for i in its[:3]]))
    print("\n".join(lines))
    try:
        c = P.CACHE; c.mkdir(exist_ok=True)
        items = [{"title": i["title"], "source": i["source"], "url": i["link"], "when": ago(i["time"]) if i.get("time") else "", "summary": (i.get("summary") or "")[:200]} for name in order for i in by.get(name, [])[:n]]
        with (c / "cards.jsonl").open("a") as f:
            f.write(json.dumps({"name": "silo.headlines", "value": {"scope": " · ".join(groups), "topic": "", "items": items[:12]}, "t": time.time()}) + "\n")
    except Exception:
        pass
    if show and cards:
        front_page(cards[:6], " · ".join(g.title() for g in groups))


def front_page(cards, title):
    """One card per outlet on the board, laid out as a grid, headlines as the body."""
    import math
    def send(o):
        try:
            return subprocess.run([str(BOARD), json.dumps(o)], capture_output=True, text=True, timeout=15).returncode == 0
        except Exception:
            return False
    send({"a": "clear"}); send({"a": "widget", "w": "ring"})
    n = len(cards); cols = 2 if n <= 4 else 3; rows = math.ceil(n / cols)
    xs = [0.5 + (c - (cols - 1) / 2) * (0.9 / cols) for c in range(cols)]
    ys = [0.36] if rows == 1 else [0.2 + (r + 0.5) * (0.6 / rows) for r in range(rows)]
    ok = 0
    for i, (name, heads) in enumerate(cards):
        r, c = divmod(i, cols)
        ok += send({"a": "add_card", "title": name.upper()[:30], "body": "\n".join("• " + h[:90] for h in heads), "x": round(xs[c], 3), "y": round(ys[r], 3)})
    send({"a": "add_card", "title": ("NEWS · " + title)[:40], "body": datetime.now().strftime("%A %-d %B, %H:%M"), "x": 0.5, "y": 0.92})
    print(f"{ok} of {n} front-page cards on the board" if ok else "the hands board is not up")


def topic(words, n, hours):
    items, _ = load_all(["uganda", "world"])
    terms = [w.lower() for w in re.findall(r"\w+", words) if len(w) > 2]
    cutoff = time.time() - hours * 3600
    hits = [i for i in items if (not i["time"] or i["time"] >= cutoff) and all(t in (i["title"] + " " + i["summary"]).lower() for t in terms)]
    try:
        hits += [dict(i, source="Google News · " + i["source"]) for i in parse_feed(get(gnews_url(words)), "search")[:n]]
    except Exception:
        pass
    if not hits:
        print("nothing on that in the last " + str(hours) + " hours"); return
    for i in hits[:n]:
        print(f"- [{i['source']}] {i['title']}  ({ago(i['time'])})  {i['link']}")
        if i["summary"]:
            print("    " + i["summary"][:200])


def read(url, chars):
    """The readable text of an article: the paragraphs, headings kept, boilerplate mostly gone."""
    try:
        h = get(url, timeout=25).decode("utf-8", "replace")
    except Exception as e:
        print(f"could not fetch it: {e}"); return
    h = re.sub(r"<(script|style|nav|footer|aside|header|form)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    title = strip((re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I) or [None, ""])[1]) if re.search(r"<title", h, re.I) else ""
    paras = [strip(p) for p in re.findall(r"<(?:p|h1|h2|h3|li)[^>]*>(.*?)</(?:p|h1|h2|h3|li)>", h, flags=re.S | re.I)]
    paras = [p for p in paras if len(p) > 40 and not re.search(r"cookie|subscribe|sign up|advertis|all rights reserved", p, re.I)]
    text = "\n\n".join(paras)
    print(title + "\n" + url + "\n\n" + text[:chars] + ("\n\n[… trimmed]" if len(text) > chars else ""))


def youtube_id(handle):
    try:
        ids = json.loads(YTIDS.read_text())
    except Exception:
        ids = {}
    if handle in ids:
        return ids[handle]
    try:
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--timeout=20000", "--dump-dom", f"https://www.youtube.com/{handle}/videos"], capture_output=True, text=True, timeout=60).stdout
        m = re.search(r"channel/(UC[A-Za-z0-9_-]{20,})", dom)
        cid = m.group(1) if m else ""
    except Exception:
        cid = ""
    if cid:
        ids[handle] = cid; YTIDS.parent.mkdir(exist_ok=True); YTIDS.write_text(json.dumps(ids, indent=1))
    return cid


def find_source(name):
    c = cfg(); key = name.lower()
    for g in ("uganda", "world"):
        for s in c.get(g, []):
            if key in s["name"].lower() or any(key in str(v).lower() for k, v in s.items() if k in ("youtube", "x", "facebook")):
                return s
    return None


def videos(name, n):
    s = find_source(name)
    if not s or not s.get("youtube"):
        print("no YouTube channel configured for that outlet (news.json)"); return
    cid = youtube_id(s["youtube"])
    if not cid:
        print(f"could not resolve {s['youtube']} to a channel; open https://www.youtube.com/{s['youtube']} in the browser"); return
    its = []
    try:
        its = parse_feed(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"), s["name"])
    except Exception:
        its = []
    if not its:
        # the feed endpoint is not always served; read the rendered channel page instead
        try:
            dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--timeout=25000", "--dump-dom", f"https://www.youtube.com/{s['youtube']}/videos"], capture_output=True, text=True, timeout=70).stdout
            seen = set()
            for m in re.finditer(r'<a href="/watch\?v=([A-Za-z0-9_-]{11})"[^>]*class="ytLockupMetadataViewModelTitle"[^>]*aria-label="([^"]*)"', dom):
                vid, label = m.group(1), html.unescape(m.group(2))
                title = re.sub(r"\s+\d+\s+(seconds?|minutes?|hours?)(, \d+ (seconds?|minutes?))?$", "", label).strip()
                if vid in seen:
                    continue
                seen.add(vid); its.append({"title": title, "link": "https://www.youtube.com/watch?v=" + vid, "time": 0, "when": "", "source": s["name"]})
        except Exception as e:
            print(f"could not read the channel: {e}"); return
    if not its:
        print(f"no videos found; open https://www.youtube.com/{s['youtube']} in the browser"); return
    for i in its[:n]:
        print(f"- {i['title']}  ({i.get('when') or ago(i['time'])})  {i['link']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("brief"); b.add_argument("group", nargs="?", default="uganda", choices=["uganda", "world", "all"]); b.add_argument("--n", type=int, default=4); b.add_argument("--hours", type=int, default=36); b.add_argument("--show", action="store_true")
    t = sub.add_parser("topic"); t.add_argument("words"); t.add_argument("--n", type=int, default=8); t.add_argument("--hours", type=int, default=72)
    r = sub.add_parser("read"); r.add_argument("url"); r.add_argument("--chars", type=int, default=6000)
    v = sub.add_parser("videos"); v.add_argument("source"); v.add_argument("--n", type=int, default=5)
    so = sub.add_parser("social"); so.add_argument("source")
    sub.add_parser("sources")
    a = ap.parse_args()
    if a.cmd == "brief":
        brief(["uganda", "world"] if a.group == "all" else [a.group], a.n, a.hours, a.show)
    elif a.cmd == "topic":
        topic(a.words, a.n, a.hours)
    elif a.cmd == "read":
        read(a.url, a.chars)
    elif a.cmd == "videos":
        videos(a.source, a.n)
    elif a.cmd == "social":
        s = find_source(a.source)
        print(json.dumps({k: v for k, v in (s or {}).items() if k in ("name", "site", "x", "facebook", "youtube", "note")}, indent=1) if s else "no such outlet in news.json")
    elif a.cmd == "sources":
        c = cfg()
        try:
            ok = json.loads(CACHE.read_text()).get("ok", {})
        except Exception:
            ok = {}
        for g in ("uganda", "world"):
            print(g.upper())
            for s in c.get(g, []):
                print(f"  {s['name']:<28} {'feed ok' if ok.get(s['name']) else ('feed failed' if s['name'] in ok else 'not fetched yet'):<15} {s.get('note', '')}")
    else:
        print(__doc__)
