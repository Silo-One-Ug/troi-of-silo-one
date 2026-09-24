#!/usr/bin/env python3
"""Pictures for research: find them, fetch them, put them on the board.

  pictures.py search "city skyline at dusk" [--n 6] [--show] [--topic slug]   free, credited pictures from Wikimedia Commons, Openverse and Wikipedia
  pictures.py page https://example.com/article [--n 4] [--show]           the pictures a web page leads with (og:image, the large ones)
  pictures.py shot https://example.com [--show]                           a screenshot of the page itself
  pictures.py board <title> <file> [file ...]                             put files that are already here on the board, as a numbered grid, with a caption
  pictures.py focus 2 | focus <word>                                     spotlight one picture (others dim); pictures.py unfocus brings them all back
  pictures.py clear                                                      sweep the board (the ring stays); --add on any command keeps what is up

Everything lands in data/blobs/research/<topic>/ with a credits.json beside the files
(source, page, licence, author), so a picture can always be traced and credited. --show stages
them on the hands board: a caption card plus the pictures in a row. Standard library only; the
system python runs it. No keys.
"""
import argparse
import html
import json
import time
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
OUT = P.blob_dir("research")
MEDIA = HOME / "barehands" / "media" / "research"
BOARD = HOME / "barehands" / "bin" / "board.sh"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = {"User-Agent": "SiloOne/1.0 (personal research assistant; contact: local user)"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48] or "topic"


def get(url, timeout=25, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        return data if binary else data.decode("utf-8", "replace")


def get_json(url):
    return json.loads(get(url))


# ---------------------------------------------------------------- sources
def commons(q, n):
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=" + str(n * 2)
         + "&gsrsearch=" + urllib.parse.quote(q + " filetype:bitmap") + "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=1280")
    out = []
    try:
        pages = get_json(u).get("query", {}).get("pages", {})
    except Exception:
        return out
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata", {}) or {}
        url = ii.get("thumburl") or ii.get("url", "")
        if not url or not any(url.lower().split("?")[0].endswith(e) for e in IMG_EXT):
            continue
        out.append({"url": url, "page": ii.get("descriptionurl", ""), "title": re.sub(r"^File:", "", p.get("title", "")),
                    "author": re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()[:80], "license": md.get("LicenseShortName", {}).get("value", ""), "source": "Wikimedia Commons"})
        if len(out) >= n:
            break
    return out


def openverse(q, n):
    u = "https://api.openverse.org/v1/images/?q=" + urllib.parse.quote(q) + "&page_size=" + str(n) + "&mature=false"
    out = []
    try:
        for r in get_json(u).get("results", []):
            out.append({"url": r.get("url", ""), "page": r.get("foreign_landing_url", ""), "title": (r.get("title") or "")[:80],
                        "author": (r.get("creator") or "")[:80], "license": (r.get("license") or "").upper(), "source": r.get("source") or "Openverse"})
    except Exception:
        pass
    return [o for o in out if o["url"]][:n]


def wikipedia(q, n):
    u = ("https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrlimit=" + str(n) + "&gsrsearch=" + urllib.parse.quote(q)
         + "&prop=pageimages|info&piprop=original|thumbnail&pithumbsize=1280&inprop=url")
    out = []
    try:
        for p in get_json(u).get("query", {}).get("pages", {}).values():
            src = (p.get("original") or p.get("thumbnail") or {}).get("source", "")
            if src and any(src.lower().split("?")[0].endswith(e) for e in IMG_EXT):
                out.append({"url": src, "page": p.get("fullurl", ""), "title": p.get("title", ""), "author": "", "license": "see page", "source": "Wikipedia"})
    except Exception:
        pass
    return out[:n]


def page_images(url, n):
    """The pictures a page leads with: og:image / twitter:image first, then the largest <img> by declared size."""
    try:
        h = get(url)
    except Exception as e:
        return [], f"could not fetch the page: {e}"
    found = []
    for m in re.finditer(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', h, re.I):
        found.append((10 ** 9, m.group(1)))
    for m in re.finditer(r"<img[^>]+>", h, re.I):
        tag = m.group(0); src = re.search(r'\ssrc=["\']([^"\']+)', tag, re.I)
        if not src:
            continue
        w = re.search(r'\swidth=["\']?(\d+)', tag, re.I); hh = re.search(r'\sheight=["\']?(\d+)', tag, re.I)
        area = (int(w.group(1)) if w else 300) * (int(hh.group(1)) if hh else 200)
        found.append((area, src.group(1)))
    seen, out = set(), []
    for area, src in sorted(found, key=lambda t: -t[0]):
        full = urllib.parse.urljoin(url, html.unescape(src))
        if full in seen or full.startswith("data:") or area < 40000:
            continue
        seen.add(full)
        out.append({"url": full, "page": url, "title": "", "author": "", "license": "from the page", "source": urllib.parse.urlparse(url).netloc})
        if len(out) >= n:
            break
    return out, ""


# ---------------------------------------------------------------- fetching and showing
def card(name, value):
    """A card for the console's conversation (and any AG-UI client): appended to cache/cards.jsonl."""
    try:
        c = P.CACHE; c.mkdir(exist_ok=True)
        with (c / "cards.jsonl").open("a") as f:
            f.write(json.dumps({"name": name, "value": value, "t": time.time()}) + "\n")
    except Exception:
        pass


def remember(saved, query):
    try:
        sys.path.insert(0, str(HERE)); import db
        for it in saved:
            db.picture_add("research", it["file"], url=it.get("url", ""), title=it.get("title", ""), query=query, source=it.get("source", ""), author=it.get("author", ""), license=it.get("license", ""), page=it.get("page", ""))
    except Exception:
        pass
    card("silo.pictures", {"query": query, "items": [{"url": "/img?p=" + urllib.parse.quote(it["file"]), "page": it.get("page", ""), "title": it.get("title", ""), "author": it.get("author", ""), "license": it.get("license", ""), "source": it.get("source", "")} for it in saved]})


def fetch(items, topic):
    d = OUT / slug(topic); d.mkdir(parents=True, exist_ok=True)
    start = len([f for f in d.iterdir() if f.suffix.lower() in IMG_EXT]) if d.exists() else 0
    saved, credits = [], []
    try:
        credits = json.loads((d / "credits.json").read_text())
    except Exception:
        credits = []
    for i, it in enumerate(items):
        try:
            data = get(it["url"], timeout=40, binary=True)
        except Exception:
            continue
        if len(data) < 4000:
            continue
        ext = Path(urllib.parse.urlparse(it["url"]).path).suffix.lower() or ".jpg"
        if ext not in IMG_EXT:
            ext = ".jpg"
        p = d / f"{start + i + 1:02d}-{slug(it.get('source') or 'web')}{ext}"
        p.write_bytes(data)
        it = dict(it, file=str(p)); saved.append(it); credits.append(it)
    (d / "credits.json").write_text(json.dumps(credits, indent=1))
    remember(saved, topic)
    return saved


def board_cmd(obj):
    try:
        r = subprocess.run([str(BOARD), json.dumps(obj)], capture_output=True, text=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def board(title, files, credits=None, fresh=True):
    """The pictures laid out as a grid on the hands board, numbered, with one caption card underneath.
    fresh=True sweeps the board first (the ring stays), so a new topic never piles on the old one."""
    import math
    MEDIA.mkdir(parents=True, exist_ok=True)
    files = [f for f in files if Path(f).is_file()][:9]
    if not files:
        return "nothing to show"
    if fresh:
        board_cmd({"a": "clear"}); board_cmd({"a": "widget", "w": "ring"})     # everything off, the ring back: both land at once
    n = len(files)
    cols = 1 if n == 1 else 2 if n <= 4 else 3
    rows = math.ceil(n / cols)
    # the grid: centres spread across the middle of the stage, sizes so nothing overlaps
    w = round(min(0.30, 0.86 / cols - 0.03), 2); h = round(min(0.40, 0.66 / rows - 0.04), 2)
    xs = [0.5] if cols == 1 else [0.5 + (c - (cols - 1) / 2) * (0.88 / cols) for c in range(cols)]
    ys = [0.40] if rows == 1 else [0.16 + (r + 0.5) * (0.62 / rows) for r in range(rows)]
    ok = 0
    for i, f in enumerate(files):
        name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(f).name)
        subprocess.run(["cp", "-f", str(f), str(MEDIA / name)], capture_output=True)
        cred = credits[i] if credits and i < len(credits) else {}
        cap = (cred.get("title") or cred.get("source") or Path(f).stem)[:36]
        r, c = divmod(i, cols)
        last_row = n - r * cols if r == rows - 1 else cols
        x = xs[c] if last_row == cols else 0.5 + (c - (last_row - 1) / 2) * (0.88 / cols)
        ok += board_cmd({"a": "add_img", "title": f"#{i + 1} {cap}", "src": "research/" + name, "x": round(x, 3), "y": round(ys[r], 3), "w": w, "h": h})
    body = title[:160]
    if credits:
        srcs = sorted({c.get("source", "") for c in credits if c.get("source")})
        if srcs: body += "\n" + ", ".join(srcs)[:120]
    board_cmd({"a": "add_card", "title": title[:40].upper(), "body": body, "x": 0.5, "y": 0.9})
    return f"{ok} of {n} pictures on the board in a {cols}x{rows} grid" if ok else "the hands board is not up"


def focus(which):
    """Spotlight one picture on the board: by its number (#2), a word from its caption, or part of its file name."""
    key = f"#{which} " if str(which).isdigit() else str(which)
    return "focused: " + key.strip() if board_cmd({"a": "present", "title": key}) else "the hands board is not up"


def unfocus():
    return "all pictures back" if board_cmd({"a": "present", "unfocus": 1, "title": "-"}) else "the hands board is not up"


def shot(url, topic):
    d = OUT / slug(topic); d.mkdir(parents=True, exist_ok=True)
    p = d / (f"{len(list(d.glob('*.png'))) + 1:02d}-shot-{slug(urllib.parse.urlparse(url).netloc)}.png")
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,900", "--timeout=15000", f"--screenshot={p}", url], capture_output=True, timeout=60)
    except Exception as e:
        return None, str(e)
    return (str(p), "") if p.exists() and p.stat().st_size > 5000 else (None, "the screenshot failed (Chrome could not render the page in time)")


def describe(saved):
    lines = []
    for it in saved:
        lines.append(f"{it['file']}  ({it.get('source','')}{' · ' + it['license'] if it.get('license') else ''}{' · ' + it['author'] if it.get('author') else ''}{' · ' + it['page'] if it.get('page') else ''})")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    s1 = sub.add_parser("search"); s1.add_argument("query"); s1.add_argument("--n", type=int, default=6); s1.add_argument("--show", action="store_true"); s1.add_argument("--add", action="store_true", help="keep what is already on the board"); s1.add_argument("--topic", default="")
    s2 = sub.add_parser("page"); s2.add_argument("url"); s2.add_argument("--n", type=int, default=4); s2.add_argument("--show", action="store_true"); s2.add_argument("--add", action="store_true", help="keep what is already on the board"); s2.add_argument("--topic", default="")
    s3 = sub.add_parser("shot"); s3.add_argument("url"); s3.add_argument("--show", action="store_true"); s3.add_argument("--add", action="store_true", help="keep what is already on the board"); s3.add_argument("--topic", default="")
    s4 = sub.add_parser("board"); s4.add_argument("title"); s4.add_argument("files", nargs="+"); s4.add_argument("--add", action="store_true", help="keep what is already on the board")
    s5 = sub.add_parser("focus"); s5.add_argument("which", help="a number (2), a caption word, or part of the file name")
    sub.add_parser("unfocus"); sub.add_parser("clear")
    a = ap.parse_args()
    if a.cmd == "search":
        n = a.n; items = []
        for src in (commons, wikipedia, openverse):
            items += src(a.query, max(2, n // 2))
        seen, uniq = set(), []
        for it in items:
            if it["url"] not in seen:
                seen.add(it["url"]); uniq.append(it)
        saved = fetch(uniq[:n], a.topic or a.query)
        if not saved:
            print("no pictures found for that; try other words"); sys.exit(1)
        print(describe(saved))
        if a.show:
            print(board(a.query, [s["file"] for s in saved], saved, fresh=not a.add))
    elif a.cmd == "page":
        items, err = page_images(a.url, a.n)
        if err:
            print(err); sys.exit(1)
        saved = fetch(items, a.topic or urllib.parse.urlparse(a.url).netloc)
        if not saved:
            print("that page has no pictures large enough to show"); sys.exit(1)
        print(describe(saved))
        if a.show:
            print(board(a.url[:60], [s["file"] for s in saved], saved, fresh=not a.add))
    elif a.cmd == "shot":
        p, err = shot(a.url, a.topic or urllib.parse.urlparse(a.url).netloc)
        if not p:
            print(err); sys.exit(1)
        print(p)
        if a.show:
            print(board(a.url[:60], [p], fresh=not a.add))
    elif a.cmd == "board":
        print(board(a.title, a.files, fresh=not a.add))
    elif a.cmd == "focus":
        print(focus(a.which))
    elif a.cmd == "unfocus":
        print(unfocus())
    elif a.cmd == "clear":
        print("board swept (the ring stays)" if (board_cmd({"a": "clear"}) and board_cmd({"a": "widget", "w": "ring"})) else "the hands board is not up")
    else:
        print(__doc__)
