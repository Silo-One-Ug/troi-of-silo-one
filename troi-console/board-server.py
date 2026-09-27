#!/usr/bin/env python3
"""board-server.py: the board's server (Silo One). The board is the agent's show-and-tell surface: a warm white,
full-width page of tiles (cards, pictures, notes from the vault, UI panels) that the owner moves with the mouse. It is
served on the Mac only (127.0.0.1), at the address the console embeds.

  GET  /stage.html, /board.html  the page (board.html, beside board-app.js, board-render.js, board.css, board-ui.css, board-theme.css in troi-console/barehands/)
  GET  /media/*                  the airlock: the only folder pictures and videos ever come from (barehands/media/, or the media orb's path)
  GET  /note?f=<orb>/<rel>       one vault note's text, jailed to the notes folder in barehands.json
  GET  /config                   the board's name (the console's board_label) and its folders
  POST /state                    the page's heartbeat (what is up); the reply carries the queued commands
  GET  /state                    what the page last reported (board-state.sh reads it)
  POST /cmd                      a command for the board (bin/board.sh, show.py, pictures.py, show-image.sh …): add_card, add_img,
                                 hand, give, present, yank, hover, clear, reset, scroll_note, add_ui, ui, layout, tidy; widget,
                                 explode and assemble are accepted and ignored (the ring and the holograms are gone)
  GET  /scene                    the saved scene: the page restores it on load, after a reload or a restart
  GET  /ui?id=<uid>              one UI panel's tree
  POST /event  GET /events       a click on a button, a choice or a placeholder prompt; each reaches the agent as a line
  POST /note                     a checkbox ticked in a note on the board flips the mark on that line of the note

The scene is saved to data/board/scene.json a second after any change. Trees are checked before they render: every
local file must be inside the airlock (a wrong subfolder heals by unique file name), anything remote is https or refused.

  board-server.py [--port N] [--scene FILE] [--ttl SECONDS] [--no-relay] [--relay-url URL]
"""
import argparse
import json
import mimetypes
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402

PAGES = HERE / "barehands"                        # the page and its scripts
HOME = P.BAREHANDS                                # barehands.json (written by setup.py), media/ (the airlock), state/
STATIC = {"/board-app.js": "application/javascript", "/board-render.js": "application/javascript",
          "/board.css": "text/css", "/board-ui.css": "text/css", "/board-theme.css": "text/css"}
PAGE_PATHS = ("/", "/stage.html", "/board.html", "/index.html")

ARGS = None
SCENE_FILE = P.DATA / "board" / "scene.json"    # the scene of the board that is up (the main board's is scene.json, the others' boards/<id>.json)
MAIN_FILE = SCENE_FILE
BOARDS_FILE = P.DATA / "board" / "boards.json"   # the boards, plural: id, name, when; and which one is current (every page shows that one)
BOARDS = {"current": "main", "boards": [{"id": "main", "name": "Main", "created": 0.0}]}
_BV = [1]                                         # the registry's version: a page whose strip is older redraws it
LOCK = threading.Lock()
SCENE = {"items": [], "ui": {}, "t": 0}
SPECS = {}                                        # uid -> {"spec": tree, "v": version}
EVENTS = []
LAST_BEAT = 0.0
_STATE = b"{}"                                    # the page's last heartbeat, as posted
_CMDS = []                                        # queued commands, handed to the page on its next heartbeat
_sig = None
_dirty = threading.Event()
_seq = [0]

ALLOWED = {"add_img", "add_card", "clear", "reset", "hand", "give", "yank", "hover", "scroll_note", "widget", "explode",
           "assemble", "present", "add_ui", "ui", "layout", "tidy"}
KEEP = {"card", "img", "model", "panel", "ui"}
KEYS = ("type", "title", "body", "src", "file", "x", "y", "tw", "th", "iw", "ih", "ui", "uid", "uv", "us", "ua", "ub", "ut", "usf", "sy", "pres", "mm")   # ut, usf: a panel's theme and surface (board-theme.css)


# ---- config and folders (barehands.json: the name the console gave the board, the notes and media folders)
def load_config():
    cfg = {"name": "Assistant", "port": 8794, "orbs": []}
    try:
        cfg.update(json.loads((HOME / "barehands.json").read_text()))
    except Exception:
        pass
    if not cfg.get("orbs"):
        cfg["orbs"] = [{"title": "Notes", "path": str(P.DATA / "vault"), "kind": "notes"}, {"title": "Props", "path": "media", "kind": "media"}]
    return cfg


CONFIG = load_config()


def media_root():
    for orb in CONFIG.get("orbs", []):
        if orb.get("kind") == "media":
            q = Path(str(orb.get("path") or "media")).expanduser()
            return (q if q.is_absolute() else HOME / q).resolve()
    return (HOME / "media").resolve()


def notes_root(i):
    try:
        orb = CONFIG["orbs"][int(i)]
        if orb.get("kind") != "notes":
            return None
        q = Path(str(orb.get("path"))).expanduser()
        return (q if q.is_absolute() else HOME / q).resolve()
    except Exception:
        return None


def new_uid():
    _seq[0] += 1
    return "u%s%x" % (format(int(time.time() * 1000), "x"), _seq[0])


def owner_name():
    try:
        return str(json.loads(P.CONFIG.read_text()).get("owner") or "").strip() or "the owner"
    except Exception:
        return "the owner"


# ---- the scene: a snapshot from the heartbeat, a debounced write, the file back at startup
def load():
    global SCENE, SPECS
    try:
        d = json.loads(SCENE_FILE.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("items"), list):
            SCENE = {"items": d["items"], "ui": d.get("ui") or {}, "t": float(d.get("t") or 0)}
            SPECS = {k: v for k, v in SCENE["ui"].items() if isinstance(v, dict) and isinstance(v.get("spec"), dict)}
    except Exception:
        pass


def flush():
    with LOCK:
        data = json.dumps(SCENE, separators=(",", ":"))
    try:
        SCENE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SCENE_FILE.with_suffix(".json.tmp")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, SCENE_FILE)               # one atomic swap: a reader never sees half a file
    except OSError as e:
        print("board: could not save the scene:", e, file=sys.stderr, flush=True)


def writer():
    while True:
        _dirty.wait()
        time.sleep(1.0)                           # a tile being dragged changes every frame: coalesce
        _dirty.clear()
        flush()


def snapshot(body):
    global _sig, LAST_BEAT
    try:
        st = json.loads(body)
    except ValueError:
        return
    LAST_BEAT = time.time()
    items = []
    for i in st.get("items") or []:
        if not isinstance(i, dict) or i.get("type") not in KEEP:
            continue
        if i.get("type") in ("img", "model") and not i.get("src"):
            continue
        if i.get("type") == "panel" and not i.get("file"):
            continue
        if i.get("type") == "ui" and not i.get("uid"):
            continue
        o = {}
        for k in KEYS:
            v = i.get(k)
            if v is None or v == "":
                continue
            try:
                if k in ("x", "y", "tw", "th", "iw", "ih", "sy"):
                    v = round(float(v), 4)
            except (TypeError, ValueError):
                continue
            o[k] = v
        items.append(o)
    ui = {o["uid"]: SPECS[o["uid"]] for o in items if o.get("type") == "ui" and o.get("uid") in SPECS}
    sig = json.dumps(items, sort_keys=True, separators=(",", ":")) + "|" + ",".join("%s:%s" % (k, v.get("v")) for k, v in sorted(ui.items()))
    with LOCK:
        if sig != _sig:
            _sig = sig
            SCENE.update({"items": items, "ui": ui, "t": time.time()})
            _dirty.set()


def scene_payload():
    with LOCK:
        d = dict(SCENE)
    age = time.time() - LAST_BEAT if LAST_BEAT else None
    d["live"] = age is not None and age < 3.0
    d["age"] = round(age, 1) if age is not None else None
    return d


# ---- the boards, plural: one scene file each, one current; a switch flushes the board that was up, loads the next and tells the pages
def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp"); tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8"); os.replace(tmp, path)


def load_boards():
    """The registry from disk (made with the main board when there is none); the current board's scene loaded."""
    global BOARDS, SCENE_FILE
    try:
        d = json.loads(BOARDS_FILE.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("boards"), list) and d["boards"]:
            BOARDS = {"current": str(d.get("current") or "main"), "boards": [b for b in d["boards"] if isinstance(b, dict) and b.get("id")]}
    except Exception:
        pass
    if not any(b["id"] == "main" for b in BOARDS["boards"]):
        BOARDS["boards"].insert(0, {"id": "main", "name": "Main", "created": time.time()})
    if not board_by(BOARDS["current"]) or board_by(BOARDS["current"]).get("archived"):
        BOARDS["current"] = "main"
    if BOARDS["current"] != "main":
        load_scene(BOARDS["current"])
    save_boards()


def load_scene(bid):
    """That board's scene into memory, from nothing: a missing file means an empty board, never the last board's tiles."""
    global SCENE, SPECS, SCENE_FILE, _sig
    with LOCK:
        SCENE = {"items": [], "ui": {}, "t": 0}; SPECS = {}; _sig = None
    SCENE_FILE = scene_file_for(bid)
    load()


def save_boards():
    try:
        _write_json(BOARDS_FILE, BOARDS)
    except OSError as e:
        print("board: could not save the boards:", e, file=sys.stderr, flush=True)


def scene_file_for(bid):
    return MAIN_FILE if bid == "main" else MAIN_FILE.parent / "boards" / ("%s.json" % bid)


def board_by(ref):
    """A board by id, else by name (case does not matter); None when there is none."""
    ref = str(ref or "").strip()
    if not ref:
        return None
    for b in BOARDS["boards"]:
        if b["id"] == ref:
            return b
    low = ref.lower()
    for b in BOARDS["boards"]:
        if str(b.get("name", "")).strip().lower() == low:
            return b
    return None


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "board"
    base, n = s, 2
    while any(b["id"] == s for b in BOARDS["boards"]):
        s = "%s-%d" % (base, n); n += 1
    return s


def read_scene(bid):
    """A board's saved scene from disk (the current board's comes from memory)."""
    if bid == BOARDS["current"]:
        return scene_payload()
    try:
        d = json.loads(scene_file_for(bid).read_text(encoding="utf-8"))
        items = d.get("items") if isinstance(d, dict) and isinstance(d.get("items"), list) else []
        return {"items": items, "ui": (d.get("ui") or {}) if isinstance(d, dict) else {}, "t": float(d.get("t") or 0) if isinstance(d, dict) else 0, "live": False, "age": None, "board": board_info(bid)}
    except Exception:
        return {"items": [], "ui": {}, "t": 0, "live": False, "age": None, "board": board_info(bid)}


def board_info(bid=None):
    b = board_by(bid or BOARDS["current"]) or {"id": "main", "name": "Main"}
    return {"id": b["id"], "name": b.get("name") or b["id"]}


def board_cmd():
    return {"a": "board", **board_info()}


def boards_cmd():
    return {"a": "boards", **boards_payload()}


def boards_payload():
    """The boards for the strip and the overview: each with its count, when it last changed, and a glimpse of what is on it."""
    out = []
    for b in BOARDS["boards"]:
        sc = scene_payload() if b["id"] == BOARDS["current"] else read_scene(b["id"])
        items = sc.get("items") or []
        preview = [{"type": i.get("type", ""), "title": str(i.get("title") or "")[:40]} for i in items[:6] if isinstance(i, dict)]
        out.append({"id": b["id"], "name": b.get("name") or b["id"], "archived": bool(b.get("archived")), "items": len(items),
                    "updated": float(sc.get("t") or 0), "created": b.get("created", 0), "preview": preview})
    return {"v": _BV[0], "current": BOARDS["current"], "boards": out}


def switch_board(bid):
    """The board that was up is flushed to its file; the next one's scene comes into memory; the pages are told."""
    global SCENE, SPECS, SCENE_FILE, _sig
    b = board_by(bid)
    if not b:
        raise ValueError("no board called %r" % bid)
    if b.get("archived"):
        b.pop("archived", None); b.pop("archived_at", None)
    if b["id"] != BOARDS["current"]:
        flush()
        load_scene(b["id"])
        BOARDS["current"] = b["id"]
    _BV[0] += 1
    save_boards()
    _CMDS.append(board_cmd())
    return b


def create_board(name):
    name = " ".join(str(name or "").split())[:40]
    if len(name) < 1:
        raise ValueError("a board needs a name")
    if board_by(name):
        raise ValueError("a board called %r exists already" % name)
    b = {"id": slug(name), "name": name, "created": time.time()}
    BOARDS["boards"].append(b)
    switch_board(b["id"])
    return b


def rename_board(ref, name):
    b = board_by(ref)
    if not b:
        raise ValueError("no board called %r" % ref)
    name = " ".join(str(name or "").split())[:40]
    if not name:
        raise ValueError("a board needs a name")
    other = board_by(name)
    if other and other is not b:
        raise ValueError("a board called %r exists already" % name)
    b["name"] = name; _BV[0] += 1; save_boards()
    if b["id"] == BOARDS["current"]:
        _CMDS.append(board_cmd())
    return b


def archive_board(ref):
    """Put a board away: off the strip, its scene kept on disk; restore brings it back. The main board stays."""
    b = board_by(ref)
    if not b:
        raise ValueError("no board called %r" % ref)
    if b["id"] == "main":
        raise ValueError("the main board stays")
    if b["id"] == BOARDS["current"]:
        switch_board("main")
    b["archived"] = True; b["archived_at"] = time.time(); _BV[0] += 1; save_boards()
    return b


# ---- the airlock and the trees
def airlock(src):
    """A file really inside the media folder, or a unique file name anywhere in it; back as /media/…"""
    rel = str(src or "").strip().lstrip("/")
    if rel.startswith("media/"):
        rel = rel[6:]
    media = media_root()
    target = (media / rel).resolve() if rel else media
    if media not in target.parents or not target.is_file():
        name = Path(rel).name.lower()
        hits = [p for p in media.rglob("*") if p.is_file() and p.name.lower() == name] if name else []
        if len(hits) != 1:
            raise ValueError("not in the media airlock: %s" % src)
        target = hits[0]
    return "/media/" + target.relative_to(media).as_posix()


ADDR = ("src", "url", "poster")                   # what the page will load
LINKS = ("href", "page")                          # what the page only shows


def fix_tree(node, depth=0):
    if depth > 14:
        raise ValueError("the tree is too deep")
    if isinstance(node, list):
        for x in node:
            fix_tree(x, depth + 1)
    elif isinstance(node, dict):
        for k in list(node.keys()):
            v = node[k]
            if not isinstance(k, str) or k.startswith("on") or k in ("html", "innerHTML", "script", "style", "srcdoc"):
                node.pop(k)
                continue
            if k in ADDR and isinstance(v, str):
                s = v.strip()
                if not s:
                    continue
                low = s.lower()
                if low.startswith("https://"):
                    node[k] = s
                elif low.startswith("http://"):
                    raise ValueError("https only: %s" % s)
                elif low.startswith(("data:", "javascript:", "blob:", "file:", "about:", "vbscript:")):
                    raise ValueError("that kind of address is not allowed: %s" % s[:40])
                else:
                    node[k] = airlock(s)
            elif k in LINKS and isinstance(v, str):
                node[k] = v.strip() if v.strip().lower().startswith("https://") else ""
            else:
                fix_tree(v, depth + 1)


def find_uid(title):
    """The uid of the UI panel called `title` in the last snapshot (exact, then a part of it), else the newest panel."""
    t = str(title or "").strip().lower()
    with LOCK:
        panels = [i for i in SCENE["items"] if i.get("type") == "ui" and i.get("uid")]
    if t:
        for i in panels:
            if str(i.get("title", "")).lower() == t:
                return i["uid"]
        for i in panels:
            if t in str(i.get("title", "")).lower():
                return i["uid"]
        return None
    return panels[-1]["uid"] if panels else None


def prepare(cmd):
    """Check a command and make it safe: the airlock for files, https for the rest, a uid and a version for every tree."""
    a = cmd.get("a")
    if a not in ALLOWED:
        raise ValueError("unknown board command: %s" % a)
    if a in ("add_img", "hand", "give", "present") and cmd.get("src"):
        cmd["src"] = airlock(cmd["src"])
    if a == "add_ui":
        spec = cmd.get("spec")
        if not isinstance(spec, dict) or not spec.get("type"):
            raise ValueError("add_ui needs a spec: a component tree with a type (show.py vocabulary)")
        if len(json.dumps(spec)) > 1_500_000:
            raise ValueError("the tree is too big (1.5 MB)")
        fix_tree(spec)
        uid = str(cmd.get("uid") or "").strip()[:40] or new_uid()
        v = int((SPECS.get(uid) or {}).get("v") or 0) + 1
        SPECS[uid] = {"spec": spec, "v": v}
        cmd["uid"] = uid
        cmd["uv"] = v
        cmd["title"] = str(cmd.get("title") or spec.get("title") or "PANEL")[:80]
    elif a == "ui" and "spec" in cmd:
        spec = cmd["spec"]
        if not isinstance(spec, dict) or not spec.get("type"):
            raise ValueError("ui needs a spec with a type")
        fix_tree(spec)
        uid = str(cmd.get("uid") or "").strip()[:40] or find_uid(cmd.get("title"))
        if not uid:
            raise ValueError("no panel called %r is on the board" % (cmd.get("title") or "?"))
        v = int((SPECS.get(uid) or {}).get("v") or 0) + 1
        SPECS[uid] = {"spec": spec, "v": v}
        cmd["uid"] = uid
        cmd["uv"] = v
    elif a == "layout":
        items = cmd.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("layout needs items: a list of add_ui, add_img or add_card commands")
        if len(items) > 24:
            raise ValueError("a layout takes up to 24 items")
        for it in items:
            if not isinstance(it, dict) or it.get("a") not in ("add_ui", "add_img", "add_card"):
                raise ValueError("layout items are add_ui, add_img or add_card commands")
            if it["a"] == "add_img" and not it.get("src"):
                raise ValueError("add_img needs src")
            if it["a"] == "add_card" and not it.get("title"):
                raise ValueError("add_card needs a title")
            prepare(it)


# ---- events: a click on a button or a choice is an answer; a click on a placeholder prompt is a request
def record_event(ev):
    e = {"t": time.time(), "uid": str(ev.get("uid", ""))[:40], "title": str(ev.get("title", ""))[:80], "kind": str(ev.get("kind", ""))[:16],
         "action": str(ev.get("action", ""))[:80], "label": str(ev.get("label", ""))[:200], "value": str(ev.get("value", ""))[:200]}
    with LOCK:
        if EVENTS and EVENTS[-1]["action"] == e["action"] and EVENTS[-1]["value"] == e["value"] and e["t"] - EVENTS[-1]["t"] < 1.2:
            return                                # a double click is one click
        EVENTS.append(e)
        del EVENTS[:-100]
    if not (ARGS and ARGS.no_relay):
        threading.Thread(target=relay, args=(e,), daemon=True).start()


def relay(e, url=None):
    """One line to the agent through the console server, the way reminders arrive."""
    if e["kind"] == "prompt":
        text = e["label"]                         # the owner clicked a request on the board: it reads as typed
    else:
        what = 'chose "%s"' % e["label"] if e["kind"] == "choice" else 'clicked "%s"' % e["label"]
        action = " (action: %s)" % e["action"] if e["action"] and e["action"] != e["label"] else ""
        text = ('(board: %s %s on the panel "%s"%s. Take it as their answer and act on it; when a word back is all it needs, one short sentence.)'
                % (owner_name(), what, e["title"] or "?", action))
    try:
        req = urllib.request.Request(url or (ARGS.relay_url if ARGS else "http://127.0.0.1:8796/say"), data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="text/plain; charset=utf-8", cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")            # the console page (another port) asks the floater to show
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _file(self, path, ctype=None, cache="no-store"):
        try:
            data = path.read_bytes()
        except OSError:
            return self._send(404, b"not here")
        self._send(200, data, ctype or mimetypes.guess_type(str(path))[0] or "application/octet-stream", cache)

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.send_header("Content-Length", "0"); self.end_headers()

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path, q = u.path, urllib.parse.parse_qs(u.query)
        if path in PAGE_PATHS:
            return self._file(PAGES / "board.html", "text/html; charset=utf-8")
        if path in STATIC:
            return self._file(PAGES / path.lstrip("/"), STATIC[path])
        if path.startswith("/media/"):
            root = media_root()
            rel = urllib.parse.unquote(path[len("/media/"):]).lstrip("/")
            target = (root / rel).resolve()
            if root not in target.parents or not target.is_file():
                return self._send(404, b"not in the media airlock")
            return self._file(target, None, "private, max-age=3600")
        if path == "/floater":
            try: return self._json(json.loads((P.DATA / "cache" / "floater.json").read_text()))
            except Exception: return self._json({"shown": False})
        if path == "/sounds":                                            # the room's soundscape (sounds.py): what plays, the moods on offer
            try:
                import sounds
                return self._json(sounds.status_dict())
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 500)
        if path == "/watches":                                           # the owner's watches (watches.py), for the Routines page
            try:
                import watches
                return self._json({"watches": watches.load()})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 500)
        if path == "/config":
            return self._json({"name": CONFIG.get("name", "Assistant"), "orbs": [{"title": o.get("title", "?"), "kind": o.get("kind", "notes")} for o in CONFIG["orbs"]]})
        if path == "/note":
            rel = (q.get("f") or [""])[0]
            idx, _, rel = rel.partition("/")
            root = notes_root(idx)
            if root is None:
                return self._send(404, b"no such notes folder")
            target = (root / rel).resolve()
            if root not in target.parents or target.suffix != ".md" or not target.is_file():
                return self._send(404, b"no such note")
            return self._send(200, target.read_text(encoding="utf-8", errors="replace").encode())
        if path == "/state":                                             # the page's last report, with which board it is (board-state.sh reads it)
            try:
                d = json.loads(_STATE) if _STATE else {}
            except ValueError:
                d = {}
            if isinstance(d, dict):
                d["board"] = board_info(); d["boards"] = [b["name"] for b in boards_payload()["boards"] if not b["archived"]]
            return self._json(d)
        if path == "/scene":                                             # the current board's scene; ?board=<name|id> reads another's from disk
            ref = (q.get("board") or [""])[0]
            b = board_by(ref) if ref else None
            if b and b["id"] != BOARDS["current"]:
                return self._json(read_scene(b["id"]))
            d = scene_payload(); d["board"] = board_info()
            return self._json(d)
        if path == "/boards":
            return self._json(boards_payload())
        if path == "/ui":
            uid = (q.get("id") or [""])[0]
            rec = SPECS.get(uid)
            return self._json({"uid": uid, "spec": rec["spec"], "v": rec.get("v", 1)}) if rec else self._json({"error": "no such panel"}, 404)
        if path == "/events":
            with LOCK:
                out = list(EVENTS[-50:])
            return self._json({"events": out})
        if path == "/favicon.ico":
            return self._send(204)
        return self._send(404, b"not here")

    def do_POST(self):
        global _STATE
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if 0 < n < 4_000_000 else b"{}"
        if self.path == "/floater":                                    # the desktop conversation panel (ring.py): show or hide it
            try:
                d = json.loads(body) if body.strip() else {}
                f = P.DATA / "cache" / "floater.json"; f.parent.mkdir(parents=True, exist_ok=True)
                cur = {}
                try: cur = json.loads(f.read_text())
                except Exception: pass
                if "shown" in d: cur["shown"] = bool(d["shown"])
                tmp = f.with_suffix(".json.tmp"); tmp.write_text(json.dumps(cur)); os.replace(tmp, f)
                return self._json(cur)
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 400)
        if self.path == "/watches":                                    # a watch on or off from the Routines page (never removed: off keeps it)
            try:
                d = json.loads(body) if body.strip() else {}
                wid = str(d.get("id") or "")
                if not re.fullmatch(r"w\d{1,6}", wid) or not isinstance(d.get("on"), bool):
                    return self._json({"ok": False, "error": "say id and on"}, 400)
                import watches
                items = watches.load(); w = next((x for x in items if str(x.get("id")) == wid), None)
                if not w:
                    return self._json({"ok": False, "error": "no such watch"}, 404)
                w["on"] = d["on"]; watches.save(items)
                return self._json({"ok": True, "id": wid, "on": w["on"]})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 400)
        if self.path == "/sounds":                                     # play a mood, stop, or set the volume: sounds.py does it, detached (making a loop takes a while)
            try:
                d = json.loads(body) if body.strip() else {}
                args = ["stop"] if d.get("stop") else ["play", str(d["mood"])] if d.get("mood") else ["volume", str(int(d["volume"]))] if "volume" in d else None
                if not args:
                    return self._json({"ok": False, "error": "say mood, stop or volume"}, 400)
                if args[0] == "play" and not re.fullmatch(r"[a-z0-9_-]{1,32}", args[1]):
                    return self._json({"ok": False, "error": "no such mood"}, 400)
                import sounds
                making = args[0] == "play" and not sounds.loop_ready(args[1])
                P.LOGS.mkdir(parents=True, exist_ok=True)
                with open(P.LOGS / "sounds.log", "a") as lg:
                    subprocess.Popen([sys.executable, str(HERE / "sounds.py"), *args], stdout=lg, stderr=lg, start_new_session=True, cwd=str(HERE))
                st = sounds.status_dict()                                # the command runs detached: answer with what was asked, not what is read back yet
                return self._json({"ok": True, "making": making, **({"playing": args[1]} if args[0] == "play" and not making else {}),
                                   "volume": int(args[1]) if args[0] == "volume" else st.get("volume")})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 400)
        if self.path == "/state":
            try:
                st = json.loads(body)
            except ValueError:
                st = {}
            if not isinstance(st, dict):
                st = {}
            page_board = str(st.get("board") or "")
            if page_board != BOARDS["current"]:                            # a page on another board, or one too old to say: its items are not this board's; it catches up first
                out = [board_cmd()]
            else:
                _STATE = body
                snapshot(body)
                now = time.time()
                _CMDS[:] = [c for c in _CMDS if not c.get("_t") or now - c["_t"] < 600]        # a command nobody showed for ten minutes is stale
                out = [c for c in _CMDS if c.get("_b") in (None, BOARDS["current"])][:8]       # this board's commands (and the board switches, which are everyone's)
                for c in out:
                    _CMDS.remove(c)
                out = [{k: v for k, v in c.items() if k not in ("_b", "_t")} for c in out]
            try:
                if int(st.get("bv") or 0) != _BV[0]:                       # its strip is older than the registry
                    out.append(boards_cmd())
            except (TypeError, ValueError):
                out.append(boards_cmd())
            return self._json(out)
        if self.path == "/boards":                                     # the boards, plural: create, switch, rename, archive, restore (the strip and boards.sh)
            try:
                d = json.loads(body) if body.strip() else {}
                a = d.get("a"); ref = d.get("ref") or d.get("id") or d.get("name")
                if a == "create":
                    create_board(d.get("name"))
                elif a in ("switch", "use", "restore"):
                    switch_board(board_by(ref)["id"] if board_by(ref) else ref)
                elif a == "rename":
                    rename_board(ref, d.get("name"))
                elif a == "archive":
                    archive_board(ref)
                else:
                    raise ValueError("say create, switch, rename, archive or restore")
                return self._json({"ok": True, **boards_payload()})
            except (ValueError, TypeError) as e:
                return self._json({"ok": False, "error": str(e), **boards_payload()}, 400)
        if self.path == "/cmd":
            try:
                cmd = json.loads(body)
                if not isinstance(cmd, dict):
                    raise ValueError("a command is a JSON object")
                if cmd.get("a") == "board":                                # the agent switches boards (and makes one with "create":1)
                    ref = cmd.get("name") or cmd.get("id")
                    b = board_by(ref)
                    if not b and cmd.get("create"):
                        b = create_board(ref)
                    elif not b:
                        raise ValueError("no board called %r (add \"create\":1 to make it)" % ref)
                    else:
                        switch_board(b["id"])
                    return self._json({"ok": True, "board": board_info(b["id"])})
                target = cmd.pop("board", None)                            # a command for a named board lands there and brings it up
                if target:
                    b = board_by(target)
                    if not b and cmd.get("create"):
                        b = create_board(target)
                    elif not b:
                        raise ValueError("no board called %r" % target)
                    if b["id"] != BOARDS["current"]:
                        switch_board(b["id"])
                cmd.pop("create", None)
                prepare(cmd)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            cmd["_b"] = BOARDS["current"]; cmd["_t"] = time.time()          # for the board that is up now: a page shows it only when on that board
            _CMDS.append(cmd)
            return self._send(204)
        if self.path == "/event":
            try:
                ev = json.loads(body)
            except ValueError:
                return self._send(400)
            record_event(ev if isinstance(ev, dict) else {})
            return self._send(204)
        if self.path == "/note":
            return self.tick_note(body)
        return self._send(404, b"not here")

    def tick_note(self, body):
        """A checkbox ticked in a note on the board: the mark flips on that line of the note itself, nothing else changes."""
        try:
            d = json.loads(body)
            rel, line, done = str(d.get("f", "")), int(d.get("line")), bool(d.get("done"))
        except Exception:
            return self._json({"error": "bad request"}, 400)
        idx, _, rel = rel.partition("/")
        root = notes_root(idx)
        if root is None:
            return self._json({"error": "no such notes folder"}, 404)
        target = (root / rel).resolve()
        if root not in target.parents or target.suffix != ".md" or not target.is_file():
            return self._json({"error": "no such note"}, 404)
        text = target.read_text(encoding="utf-8")
        lines = text.split("\n")
        if not 0 <= line < len(lines):
            return self._json({"error": "no such line"}, 400)
        m = re.match(r"^(\s*(?:[-*+]|\d+[.)])\s+)\[( |x|X)\](\s.*|)$", lines[line])
        if not m:
            return self._json({"error": "that line has no checkbox"}, 400)
        lines[line] = m.group(1) + ("[x]" if done else "[ ]") + m.group(3)
        tmp = target.with_suffix(".md.tmp")
        tmp.write_text("\n".join(lines), encoding="utf-8")
        os.replace(tmp, target)
        return self._json({"ok": True, "done": done, "line": line})


def main():
    global ARGS, SCENE_FILE, MAIN_FILE, BOARDS_FILE
    ap = argparse.ArgumentParser(description="the board's server")
    ap.add_argument("--port", type=int)
    ap.add_argument("--scene")
    ap.add_argument("--ttl", type=float, default=0, help="exit after N seconds (benches)")
    ap.add_argument("--no-relay", action="store_true", help="keep clicks out of the agent's conversation (benches)")
    ap.add_argument("--relay-url", default="http://127.0.0.1:8796/say")
    ARGS = ap.parse_args()
    if ARGS.scene:
        SCENE_FILE = Path(ARGS.scene).expanduser()
        BOARDS_FILE = SCENE_FILE.with_name("boards.json")             # a bench keeps its boards beside its scene
    MAIN_FILE = SCENE_FILE
    load()
    load_boards()                                                    # the boards, and the one that was up when the server last ran
    for d in ("misc", "models", "research", "ui"):
        try:
            (media_root() / d).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    port = ARGS.port or int(CONFIG.get("port", 8794))
    threading.Thread(target=writer, daemon=True).start()
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: (flush(), os._exit(0)))
    if ARGS.ttl:
        threading.Timer(ARGS.ttl, lambda: (flush(), os._exit(0))).start()
    print("board up: http://127.0.0.1:%d/stage.html   scene: %s%s" % (port, SCENE_FILE, "   (clicks stay off the conversation)" if ARGS.no_relay else ""), flush=True)
    QuietServer(("127.0.0.1", port), Handler).serve_forever()


class QuietServer(ThreadingHTTPServer):
    """A page that closes its connection a moment before the answer is written is not news: no traceback for it."""
    daemon_threads = True

    def handle_error(self, request, client_address):
        if sys.exc_info()[0] in (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return
        super().handle_error(request, client_address)


if __name__ == "__main__":
    main()
