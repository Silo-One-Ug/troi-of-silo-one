#!/usr/bin/env python3
"""The agent's server: the API the console app (http://localhost:3100) and the tools talk to, on 127.0.0.1:8796 only.

Standard library only.
  - the transcript is read from backtalk's own log (backtalk/logs/backtalk.log) and kept in data/troi.db
  - typed text is written into a named pipe (.typed) that start.sh hands to the voice line as its stdin,
    the same path a line typed in its terminal takes
  - settings live in data/console.json; protected ones wait for the owner (the PIN, the face, Telegram)

A few of its routes:
  GET  /config, /state   the agent, its settings and what it is doing now
  GET  /history, /transcript?pos=N, /events   the conversation (AG-UI on POST /agent)
  POST /say              {"text": "..."} -> sent to the agent as a typed line
  GET  /find?q=          files and folders under the file roots whose name contains q (the console's @ picker)
  GET  /agents           the brain's delegations this session (the Agent tool's calls, each one's activity) for the Agents page
  POST /voice            a voice note from the console page -> {"text": the words}, through the agent's own ears
  POST /upload           a file from the console page: X-Kind: uploads keeps it in data/blobs/uploads for the agent
  POST /settings         {"wake_word": true|false, ...} -> data/console.json, read live by voice.py
  POST /ui               a directive for the console (console.sh), followed at GET /ui?since=N
  GET  /                 sends a browser on to the console app
"""
import json
import os
import re
import urllib.parse
import ipaddress
import select
import sys
import time
import shutil
import signal
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import keychain as KC  # noqa: E402

import sys as _sp, os as _osp; _sp.path.insert(0, _osp.path.dirname(_osp.path.abspath(__file__))); import paths as _Pa  # noqa: E402


def _cfg_names():
    """The agent's name (backtalk.json) and the owner's name (console.json)."""
    import json as _j, os as _o
    b = str(_Pa.BACKTALK / "backtalk.json"); c = str(_Pa.CONFIG)
    try: name = _j.load(open(b)).get("name", "Assistant")
    except Exception: name = "Assistant"
    try: owner = _j.load(open(c)).get("owner", "the owner")
    except Exception: owner = "the owner"
    return name, owner
AGENT, OWNER = _cfg_names()

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
LOG = HOME / "backtalk" / "logs" / "backtalk.log"
FIFO = HERE / ".typed"
SETTINGS = P.CONFIG
SETTING_DEFAULTS = {"wake_word": True, "eyes": "off", "voice_id": "off", "brief_time": "08:00", "tts": "kokoro", "elevenlabs_voice": "", "welcomed": False, "lan": False, "hands": {"pinch_close": .32, "pinch_open": .48, "ext": 1.45, "dwell_ms": 1300, "magnet": 16}, "wake_names": ["troi", "troy", "troye", "troie"]}
PORT = int(os.environ.get("TROI_PORT", 8796))
START_POS = LOG.stat().st_size if LOG.exists() else 0  # only this session's lines


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


BT = _read_json(HOME / "backtalk" / "backtalk.json")
VIS = _read_json(HOME / "ai-visualizer" / "ai-visualizer.json")
HANDS = _read_json(HOME / "barehands" / "barehands.json")
NAME = BT.get("name", "Assistant")

LINE = re.compile(r"^(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d) \[([^\]]+)\]\s+(.*)$")
TIMING = re.compile(r"^\(\d+(\.\d+)?s to first\)\s*")
DIRECTIONS = re.compile(r"\s*<directions:.*>$")


def transcript(pos, raw=False):
    """Parsed log lines from byte offset pos. Returns (items, new_pos). raw=True: from wherever pos says, even 0."""
    if not LOG.exists():
        return [], 0
    size = LOG.stat().st_size
    if pos > size:  # log was rotated or truncated
        pos = 0
    if pos == 0 and START_POS <= size and not raw:
        pos = START_POS
    with LOG.open("rb") as f:
        f.seek(pos)
        data = f.read()
    # hold back a partial last line until it is complete
    cut = data.rfind(b"\n") + 1
    items = []
    for raw in data[:cut].decode("utf-8", "replace").splitlines():
        m = LINE.match(raw)
        if not m:
            continue
        _, clock, who, text = m.groups()
        if who == "you" and text.startswith("(camera watch:"):
            role, text = "note", f"Camera: the view changed; {AGENT} is taking a look"
        elif who == "you" and text.startswith("(session start"):
            role, text = "note", "Session started"
        elif who == "you" and text.startswith("(written:"):
            role, text = "note", f"{AGENT} is writing: " + text[9:].strip().split(":")[0][:80]
        elif who == "you" and text.startswith(("(reminder", "(github watch", "(scheduled morning")):
            role, text = "note", {"(r": "Reminder due", "(g": "GitHub: a build changed state", "(s": "Morning brief time"}[text[:2]]
        elif who == "you" and text.startswith(("(via telegram)", "(via call)")):
            role = "you"; text = ("📱 " if "telegram" in text[:14] else "📞 ") + re.sub(r"\s*\((This arrived on Telegram|[^)]*is talking to you on a voice call)[^)]*\)\s*$", "", text.split(")", 1)[1].strip())
        elif who == "you":
            role = "you"
        elif who == NAME:
            role = "agent"
            text = DIRECTIONS.sub("", TIMING.sub("", text)).replace("⏎", "\n")          # a reply's lines, as the voice line logged them
            if text.strip().lower().rstrip(".!") == "noted":
                continue
        elif who == "perm" and text.startswith("asking:"):
            role, text = "note", "Permission asked: " + text[len("asking:"):].strip()
        elif who == "voice-id" and text.startswith("ignored"):
            m2 = re.search(r"(\d\.\d\d)\)", text)
            items.append({"t": clock[:5], "role": "ignored", "why": ("not your voice" if "short" not in text else "too short to identify") + (f" ({m2.group(1)})" if m2 else ""), "text": ""})
            continue
        elif who == "voice-id" and text.startswith(("learning", "voice print")):
            role, text = "note", "Voice ID: " + text
        elif who == "pulse" and text.startswith(("reminder", "github", "morning")):
            role, text = "note", "Pulse: " + text
        elif who == "eyes":
            role, text = "note", "Camera " + text
        elif who == "wake":
            why = "my own voice" if "own voice" in text else "name only" if "name only" in text else "no wake word"
            items.append({"t": clock[:5], "role": "ignored", "why": why, "text": text.split(":", 1)[-1].strip()})
            continue
        elif who == "console" and "->" in text:
            # live mode flips: the page reads these to keep its switches honest
            key, _, val = text.partition("->")
            items.append({"t": clock[:5], "role": "ctl", "key": key.strip(),
                          "val": val.split()[0] if val.split() else "", "text": ""})
            continue
        elif who == "backtalk" and text.startswith(("up ", "hung up")):
            role, text = "note", "Voice line started" if text.startswith("up") else "Voice line stopped"
        else:
            continue
        if text:
            items.append({"t": clock[:5], "role": role, "text": text})
    return items, pos + cut


IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".glb", ".gltf"}
NOT_UPLOADED = {".app", ".pkg", ".dmg", ".command", ".scpt", ".exe", ".msi"}     # things the conversation does not take as files
def image_roots():
    """Where the console may serve pictures from: the blob store, the vault, the board's airlock, the live frame."""
    vault = settings().get("vault") or HANDS.get("orbs", [{}])[0].get("path", "")
    return [("Blobs", P.BLOBS), ("Vault", Path(vault) if vault else P.BLOBS), ("Board", HOME / "barehands" / "media"), ("Live", P.CACHE)]


WHERE = {"looks": "Camera", "screens": "Screen", "research": "Research", "imagined": "Imagined", "telegram": "Telegram", "uploads": "Uploads", "board": "Board"}


def list_images():
    """The Library: pictures and models from the blob index (newest first), with their titles and credits."""
    out = []
    for b in DB.blobs(limit=600):
        pth = Path(b["path"])
        if pth.suffix.lower() not in IMG_EXTS or not pth.exists():
            continue
        m = b.get("meta") or {}
        out.append({"id": b["id"], "path": b["path"], "name": b["title"] or pth.name, "where": WHERE.get(b["kind"], b["kind"].title()), "kind": "model" if pth.suffix.lower() in (".glb", ".gltf") else "image",
                    "t": int(b["t"] or 0), "starred": bool(b["starred"]), "credit": " · ".join(x for x in (m.get("source"), m.get("author"), m.get("license")) if x)})
    return out[:300]


def allowed_image(path):
    p = Path(path).expanduser().resolve()
    return p.is_file() and p.suffix.lower() in IMG_EXTS and any(str(p).startswith(str(r.resolve()) + "/") for _, r in image_roots() if r.exists())


UI = []                                   # (old name, unused) the page directives are the numbered feed below
UI_FEED = []                              # {"seq", "t", ...directive}: what the agent asked the console to do, newest last
UI_SEQ = {"n": 0}


def ui_push(d):
    UI_SEQ["n"] += 1
    UI_FEED.append({"seq": UI_SEQ["n"], "t": time.time(), **d}); del UI_FEED[:-200]
    return UI_SEQ["n"]


def ui_since(n):
    return [u for u in UI_FEED if u["seq"] > n and time.time() - u["t"] < 120]

# ---- the agent's memory of what happened (db.py, SQLite): the voice log is tailed into it as it grows, cards too,
#      so the console can show the conversation back after a reload and anything can read the record.
import db as DB                                                   # noqa: E402
import threading                                                  # noqa: E402
CARDS = P.CACHE / "cards.jsonl"
TAIL = {"pos": int(DB.kv_get("log_pos", 0) or 0), "cpos": int(DB.kv_get("cards_pos", 0) or 0), "lock": threading.Lock()}


def current_session():
    try:
        return (HOME / "backtalk" / ".backtalk_session").read_text().strip()[:64]
    except Exception:
        return ""


# ---- a title for every session, written once by a small model from what was said (the agent or the owner can rename it)
_SUMM = {"lock": threading.Lock(), "busy": set(), "tried": {}}
CLAUDE_CLI = shutil.which("claude") or str(HOME / "backtalk" / ".venv" / "lib" / "python3.12" / "site-packages" / "claude_agent_sdk" / "_bundled" / "claude")


def summarise_sessions(rows, current):
    """Start a title for one session that has none yet: at least four lines, and either not the one in use or quiet for ten
    minutes. One at a time, in the background; a failure is tried again an hour later."""
    now = time.time()
    with _SUMM["lock"]:
        if _SUMM["busy"]:
            return
        due = [s for s in rows if not s.get("summary") and s.get("n", 0) >= 4 and (s["id"] != current or (s.get("last") or 0) < now - 600)
               and _SUMM["tried"].get(s["id"], 0) < now - 3600]
        if not due:
            return
        sid = due[0]["id"]; _SUMM["busy"].add(sid); _SUMM["tried"][sid] = now
    threading.Thread(target=_summarise, args=(sid,), daemon=True).start()


def _summarise(sid):
    try:
        text = DB.session_text(sid)
        if len(text) < 80:
            return
        prompt = ("Below is a conversation between an owner and their chief-of-staff agent. Give it a title of at most eight words saying what it was "
                  "about, the way a file in a cabinet is labelled: specific, plain words, no quotes, no full stop. Reply with the title only.\n\n"
                  "<conversation>\n" + text + "\n</conversation>")
        cwd = P.CACHE / "summaries"; cwd.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([CLAUDE_CLI, "-p", "--no-session-persistence", "--model", "claude-haiku-4-5-20251001", "--output-format", "text", prompt],
                           capture_output=True, text=True, timeout=120, cwd=str(cwd))
        title = " ".join((r.stdout or "").strip().splitlines()[:1]).strip().strip('"\'').rstrip(".").strip()
        if r.returncode == 0 and 2 < len(title) <= 100:
            DB.session_title(sid, title); fslog(f"session titled {sid[:8]}: {title}")
        else:
            fslog(f"session title not written for {sid[:8]}: {(r.stderr or r.stdout).strip()[-160:]}")
    except Exception as e:
        fslog(f"session title failed {sid[:8]}: {e}")
    finally:
        with _SUMM["lock"]:
            _SUMM["busy"].discard(sid)


def read_cards(cpos):
    """Cards appended by the tools (cache/cards.jsonl) from byte offset cpos. Returns (cards, new_pos)."""
    if not CARDS.exists():
        return [], 0
    size = CARDS.stat().st_size
    if cpos > size:
        cpos = 0
    with CARDS.open("rb") as f:
        f.seek(cpos); data = f.read()
    cut = data.rfind(b"\n") + 1
    out = []
    for raw in data[:cut].decode("utf-8", "replace").splitlines():
        try:
            c = json.loads(raw)
            if c.get("name"):
                out.append(c)
        except Exception:
            pass
    return out, cpos + cut


def tail_once():
    """Move what the log and the cards file gained into the database."""
    with TAIL["lock"]:
        size = LOG.stat().st_size if LOG.exists() else 0
        if TAIL["pos"] > size:
            TAIL["pos"] = 0
        items, newpos = transcript(TAIL["pos"], raw=True)
        sess = current_session()
        for it in items:
            if it.get("role") in ("you", "agent", "note", "ignored"):
                DB.add_message(sess, it["role"], it["text"], {k: v for k, v in it.items() if k not in ("role", "text", "t")}, clock=it.get("t", ""))
        if newpos != TAIL["pos"]:
            TAIL["pos"] = newpos; DB.kv_set("log_pos", newpos)
        cards, cnew = read_cards(TAIL["cpos"])
        for c in cards:
            DB.add_message(sess, "card", c.get("name", ""), c, clock=time.strftime("%H:%M:%S", time.localtime(c.get("t") or time.time())), t=c.get("t"))
        if cnew != TAIL["cpos"]:
            TAIL["cpos"] = cnew; DB.kv_set("cards_pos", cnew)


def tail_forever():
    n = 0
    while True:
        try:
            tail_once()
        except Exception:
            pass
        if n % 30 == 0:                                            # every half minute: new files in data/blobs join the index
            try:
                DB.blob_index()
            except Exception:
                pass
        n += 1
        time.sleep(1.0)


threading.Thread(target=tail_forever, daemon=True).start()


def vault_candidates():
    """Folders in the home (two levels down) that already hold a vault: the welcome offers them by name."""
    out = []
    for pat in ("*/VAULT-INDEX.md", "*/*/VAULT-INDEX.md"):
        for f in Path.home().glob(pat):
            if f.parent == P.ROOT / "vault-template":                 # the repo's own template is never a vault
                continue
            if not any(part.startswith(".") or part in ("Library", "node_modules") for part in f.parts):
                out.append(str(f.parent))
    d = P.DATA / "vault"
    if (d / "VAULT-INDEX.md").exists(): out.append(str(d))
    return sorted(set(out))[:8]


def folder_candidates():
    """For onboarding: the usual home folders and the mounted drives, offered as places the agent may organise."""
    out = [str(Path.home() / d) for d in ("Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music", "Projects") if (Path.home() / d).is_dir()]
    try:
        out += sorted(str(v) for v in Path("/Volumes").iterdir() if v.is_dir() and not v.is_symlink() and not v.name.startswith("."))
    except OSError:
        pass
    return out


def telegram_state():
    """For onboarding: is there a bot token, is a phone paired, and the code to pair one (the bridge makes it)."""
    st = {}
    try:
        st = json.loads(DB.doc("telegram").read_text())
    except Exception:
        st = {}
    bot = ""
    tok = KC.get("telegram")
    if tok:
        try:
            import urllib.request as _u
            with _u.urlopen(f"https://api.telegram.org/bot{tok}/getMe", timeout=6) as r:
                bot = json.loads(r.read().decode()).get("result", {}).get("username", "")
        except Exception:
            bot = ""
    return {"token": bool(tok), "bot": bot, "paired": bool(st.get("owner")), "code": st.get("code", "") if not st.get("owner") else ""}


def restart_voice():
    """Start the voice line over in place (voice.py re-executes itself on SIGUSR1), so it reads the settings, the boot file
    and the vault written since it was launched. Only the process named in data/cache/voice.pid, and only if it is voice.py."""
    try:
        pid = int((P.CACHE / "voice.pid").read_text().strip())
        cmd = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
        if "troi-console/voice.py" not in cmd or "uv run" in cmd:
            return False
        os.kill(pid, signal.SIGUSR1)
        return True
    except (OSError, ValueError):
        return False


def keychain_has(name, account=None):
    return KC.has(name)


def keychain_get(name, account=None):
    return KC.get(name)


def keychain_set(name, value):
    """Keep a secret in the login Keychain (troi-of-silo-one.<name>); never in a file. Only the agent's own names."""
    return KC.put(name, value)


_VOICES = {"at": 0.0, "data": None}


def elevenlabs_voices_cached(max_age=600):
    if _VOICES["data"] is None or time.time() - _VOICES["at"] > max_age:
        _VOICES["data"] = elevenlabs_voices(); _VOICES["at"] = time.time()
    return _VOICES["data"]


def elevenlabs_voice_name(voice_id):
    if not voice_id or not KC.has("elevenlabs"):
        return ""
    d = elevenlabs_voices_cached()
    return next((v["name"] for v in (d.get("voices") or []) if v["voice_id"] == voice_id), "")


def elevenlabs_voices():
    key = KC.get("elevenlabs") or os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        return {"ok": False, "error": "no ElevenLabs key in the Keychain yet"}
    import urllib.request
    try:
        req = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": f"ElevenLabs did not answer: {str(e)[:120]}"}
    voices = []
    for v in data.get("voices", []):
        lab = v.get("labels") or {}
        voices.append({"voice_id": v.get("voice_id", ""), "name": v.get("name", ""), "labels": " · ".join(str(lab[k]) for k in ("gender", "accent", "age", "description") if lab.get(k)), "category": v.get("category", "")})
    voices.sort(key=lambda v: (v["category"] != "cloned", v["name"].lower()))
    return {"ok": True, "voices": voices}


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def doctor():
    """doctor.sh, as rows the welcome page can show."""
    try:
        r = subprocess.run([str(HERE / "doctor.sh")], capture_output=True, text=True, timeout=90)
        out = ANSI.sub("", r.stdout)
    except Exception as e:
        return {"lines": [], "error": str(e)[:200]}
    lines, section = [], ""
    for raw in out.splitlines():
        if not raw.strip() or raw.startswith("AGENT DOCTOR"):
            continue
        m = re.match(r"^\s+([✓!✗])\s+(.*)$", raw)
        if m:
            lines.append({"k": {"✓": "ok", "!": "warn", "✗": "bad"}[m.group(1)], "section": section, "text": m.group(2).strip()})
        elif not raw.startswith(" "):
            section = raw.strip()
    ok = lambda word: any(l["k"] == "ok" and word in l["text"] for l in lines)
    return {"lines": lines, "screen": ok("Screen Recording"), "accessibility": ok("Accessibility"), "voice_line": ok("voice line"), "all_green": "all green" in out}
import threading


def ask_live(text, timeout=240):
    """One turn with the LIVE voice-line brain (the single shared session): send the line,
    then read the agent's reply sentences from the log until the line goes idle. None if the
    voice line is not running."""
    if not FIFO.exists():
        return None
    # wait for the line to be free, then mark where the log ends
    t0 = time.time()
    while time.time() - t0 < 120:
        try:
            st = (HOME / "backtalk" / ".voice_state").read_text().strip()
        except Exception:
            st = "idle"
        if st == "idle" and not voice_busy():
            break
        time.sleep(0.5)
    start = LOG.stat().st_size if LOG.exists() else 0
    ok, err = say(text)
    if not ok:
        return None
    reply, seen_you, t1 = [], False, time.time()
    while time.time() - t1 < timeout:
        time.sleep(0.6)
        with LOG.open("rb") as f:
            f.seek(start); chunk = f.read().decode("utf-8", "replace")
        reply, seen_you = [], False                  # rebuilt from the whole chunk every pass
        for raw in chunk.splitlines():
            m = LINE.match(raw)
            if not m:
                continue
            _, _, who, txt = m.groups()
            if who == "you" and text[:40] in txt:
                seen_you = True
            elif who == NAME and seen_you:
                reply.append(DIRECTIONS.sub("", TIMING.sub("", txt)).replace("⏎", "\n"))
        try:
            st = (HOME / "backtalk" / ".voice_state").read_text().strip()
        except Exception:
            st = "idle"
        if reply and st == "idle" and time.time() - t1 > 3:
            break
    return " ".join(reply) if reply else None


def say_when_idle(text, timeout=90):
    """Send a typed line only once the voice line is idle, so a mode phrase
    the agent sends from inside its own turn never interrupts that turn."""
    def run():
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                st = (HOME / "backtalk" / ".voice_state").read_text().strip()
            except Exception:
                st = "idle"
            if st == "idle" and not voice_busy():
                time.sleep(1.0)
                say(text); return
            time.sleep(0.5)
    threading.Thread(target=run, daemon=True).start()


SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", ".Trash", "Library", ".next", "dist", "build",
             "vendor", ".idea", ".vscode", "Pods", "DerivedData", ".gradle", "target", ".dart_tool"}
EXT_KIND = {}
for kind, exts in {"code": "py js ts tsx jsx go php dart java rb rs c cpp h hpp swift kt kts m mm sh zsh bash lua scala cs vue svelte",
                   "web": "html htm css scss sass less", "data": "json yaml yml toml csv tsv xml sql graphql proto",
                   "doc": "md txt pdf doc docx rtf odt pages", "image": "png jpg jpeg gif webp svg heic bmp tiff",
                   "audio": "mp3 wav ogg m4a flac aac", "video": "mp4 mov webm mkv avi", "archive": "zip tar gz tgz bz2 7z rar dmg iso",
                   "config": "env ini cfg conf lock gitignore editorconfig dockerfile plist", "model": "glb gltf obj fbx",
                   "sheet": "xlsx xls numbers", "slides": "pptx key"}.items():
    for e in exts.split():
        EXT_KIND[e] = kind


def file_roots():
    return [Path(os.path.expanduser(r)) for r in settings().get("file_roots", [])]


def inside_roots(path):
    p = Path(path).resolve()
    return any(p == r.resolve() or str(p).startswith(str(r.resolve()) + "/") for r in file_roots() if r.exists())


# ---- the brain's delegations: the Agent tool's calls and results in Claude Code's own transcript of the session, and
#      each subagent's transcript beside it (<project>/<session>/subagents/agent-<id>.jsonl). Read incrementally, never
#      whole; the brain names each one in the call's description, which is the name the console shows.
_AGENTS = {"file": "", "size": 0, "tasks": {}, "order": []}
NOTE_TOOL = {"Bash": "running a command", "Read": "reading a file", "Write": "writing a file", "Edit": "editing a file", "Glob": "looking through files",
             "Grep": "searching files", "WebSearch": "searching the web", "WebFetch": "reading a page", "Agent": "delegating", "Task": "delegating"}


def brain_paths():
    """The brain's session id, its transcript, and the folder of its subagents' transcripts."""
    try:
        sid = (HOME / "backtalk" / ".backtalk_session").read_text().strip()
    except Exception:
        sid = ""
    proj = Path.home() / ".claude" / "projects" / str(HOME).replace("/", "-")
    return sid, (proj / f"{sid}.jsonl" if sid else None), (proj / sid / "subagents" if sid else None)


def _ts(s):
    import datetime as _dt
    try:
        return _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def _blocks(rec):
    c = (rec.get("message") or {}).get("content")
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def _text_of(rec):
    c = (rec.get("message") or {}).get("content")
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in _blocks(rec) if b.get("type") == "text")


def _tool_note(name):
    return NOTE_TOOL.get(name, ("in the browser" if name.startswith("mcp__playwright") else "using " + name.replace("mcp__", "").replace("__", " ")) if name else "")


def agents_scan():
    """Bring the picture of the session's delegations up to date from the transcript's new bytes."""
    sid, f, _ = brain_paths(); st = _AGENTS
    if not f or not f.exists():
        st.update(file="", size=0, tasks={}, order=[]); return
    if st["file"] != str(f) or f.stat().st_size < st["size"]:
        st.update(file=str(f), size=0, tasks={}, order=[])
    with f.open("rb") as fh:
        fh.seek(st["size"]); chunk = fh.read()
    cut = chunk.rfind(b"\n")                                        # whole lines only; a half-written one waits
    if cut < 0:
        return
    st["size"] += cut + 1
    for line in chunk[:cut].split(b"\n"):
        if b"Agent" not in line and b"task-notification" not in line and b"toolUseResult" not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("type") == "assistant":
            for b in _blocks(rec):
                if b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                    inp = b.get("input") or {}
                    st["tasks"][b["id"]] = {"id": b["id"], "name": str(inp.get("description") or "an agent").strip()[:80], "type": str(inp.get("subagent_type") or "general-purpose"),
                                            "prompt": str(inp.get("prompt") or "").strip()[:400], "started": _ts(rec.get("timestamp")), "ended": 0, "status": "active", "agent_id": "", "result": ""}
                    st["order"].append(b["id"])
        elif rec.get("type") == "user":
            for b in _blocks(rec):
                if b.get("type") == "tool_result" and b.get("tool_use_id") in st["tasks"]:
                    task = st["tasks"][b["tool_use_id"]]; tr = rec.get("toolUseResult")
                    if isinstance(tr, dict) and tr.get("agentId"):
                        task["agent_id"] = str(tr["agentId"])
                    if not (isinstance(tr, dict) and tr.get("status") == "async_launched"):          # a blocking agent: this is its report
                        c = b.get("content"); text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""
                        task.update(status="failed" if b.get("is_error") else "done", ended=_ts(rec.get("timestamp")), result=text.strip()[:300])
        txt = _text_of(rec) if rec.get("type") in ("user", "assistant") else (rec.get("content") if isinstance(rec.get("content"), str) else "")
        if "<task-notification>" in txt:                                                            # an agent that ran in the background reported (queued, then delivered)
            if True:
                m_id = re.search(r"<task-id>([^<]+)</task-id>", txt); m_st = re.search(r"<status>([^<]+)</status>", txt); m_sum = re.search(r"<summary>([^<]+)</summary>", txt)
                for task in st["tasks"].values():
                    if m_id and task["agent_id"] == m_id.group(1).strip() and task["status"] == "active":
                        task.update(status="done" if not m_st or m_st.group(1).strip() == "completed" else "failed", ended=_ts(rec.get("timestamp")))
                        if m_sum:
                            task["result"] = m_sum.group(1).strip()[:300]


def agent_activity(agent_id, subdir):
    """What a subagent is doing, from the tail of its own transcript: its last tool, its last words, its turns."""
    f = (subdir / f"agent-{agent_id}.jsonl") if subdir and agent_id else None
    if not f or not f.exists():
        return {}
    try:
        size = f.stat().st_size
        with f.open("rb") as fh:
            fh.seek(max(0, size - 65536)); tail = fh.read().decode("utf-8", "replace").split("\n")
        tool, detail, said, turns = "", "", "", 0
        for line in tail:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "assistant":
                continue
            turns += 1
            for b in _blocks(rec):
                if b.get("type") == "tool_use":
                    inp = b.get("input") or {}; tool = b.get("name", "")
                    detail = str(inp.get("description") or inp.get("command") or inp.get("file_path") or inp.get("pattern") or inp.get("url") or inp.get("query") or "")[:90]
                elif b.get("type") == "text" and b.get("text", "").strip():
                    said = b["text"].strip()[:220]; tool = ""; detail = ""
        return {"doing": _tool_note(tool), "detail": detail, "said": said, "turns": turns, "seen": f.stat().st_mtime}
    except Exception:
        return {}


def agents_archived():
    """The delegations the owner has archived off the chart (their ids), kept in the record's small documents."""
    try:
        return set(json.loads(DB.doc("agents-archived").read_text()))
    except Exception:
        return set()


def agents_archive(ids):
    cur = agents_archived() | set(ids); DB.doc("agents-archived").write_text(json.dumps(sorted(cur))); return cur


def agents_snapshot(light=False):
    """The session's delegations, newest first: name, type, status, times; with each one's activity unless light."""
    agents_scan()
    _, _, subdir = brain_paths(); now = time.time(); out = []; gone = agents_archived()
    for tid in reversed(_AGENTS["order"]):
        t = dict(_AGENTS["tasks"][tid]); t["archived"] = tid in gone
        if not light:
            t.update(agent_activity(t["agent_id"], subdir))
            if t["status"] == "active" and t.get("seen") and now - t["seen"] > 1800:
                t["status"] = "quiet"                                                              # not a word in half an hour
        out.append(t)
    return out


def brain_now():
    """The brain itself: its state and the tool in its hands, for the top of the Agents page."""
    try:
        st = (HOME / "backtalk" / ".voice_state").read_text().strip() or "idle"
    except Exception:
        st = "off"
    if st == "idle" and voice_busy():
        st = "working"
    ti = voice_tool_info() or {}
    return {"name": AGENT, "state": st if FIFO.exists() else "off", "doing": _tool_note(ti.get("name", "")), "detail": ti.get("detail", "")}


# ---- voice notes from the console page: the agent's own ears, in a resident worker (stt.py --serve) that keeps the
#      model loaded and leaves ten minutes after the last note
_STT = {"proc": None, "lock": threading.Lock(), "timer": None}
STT_PY = HOME / "backtalk" / ".venv" / "bin" / "python"


def _stt_stop():
    with _STT["lock"]:
        p = _STT["proc"]; _STT["proc"] = None
        if p and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass


def stt_text(path, timeout=150):
    """Words from an audio file. Raises when the ears do not answer."""
    with _STT["lock"]:
        p = _STT["proc"]
        if p is None or p.poll() is not None:
            p = subprocess.Popen([str(STT_PY), str(HERE / "stt.py"), "--serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
            _STT["proc"] = p
        try:
            p.stdin.write(json.dumps({"path": str(path)}) + "\n"); p.stdin.flush()
            r, _, _ = select.select([p.stdout], [], [], timeout)
            line = p.stdout.readline() if r else ""
            if not line:
                raise RuntimeError("the ears did not answer")
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
            _STT["proc"] = None
            raise
        if _STT["timer"]:
            _STT["timer"].cancel()
        _STT["timer"] = threading.Timer(600, _stt_stop); _STT["timer"].daemon = True; _STT["timer"].start()
    d = json.loads(line or "{}")
    if d.get("error"):
        raise RuntimeError(d["error"])
    return str(d.get("text", "")).strip()


_FIND = {"at": 0.0, "roots": None, "items": []}
FIND_SKIP = SKIP_DIRS | {"site-packages", "anaconda3", "miniconda3", "conda", "envs", "Caches", "Photos Library.photoslibrary"}


def _find_walk(roots):
    """Every entry under the roots, cached for a minute and capped in size and time (the fallback and the empty query)."""
    key = [str(r) for r in roots]
    if _FIND["roots"] != key or time.time() - _FIND["at"] > 60:
        items, deadline = [], time.time() + 2.0
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in FIND_SKIP)
                base = Path(dirpath)
                items += [(d, str(base / d), "dir") for d in dirnames]
                items += [(f, str(base / f), "file") for f in sorted(filenames) if not f.startswith(".")]
                if len(items) > 60000 or time.time() > deadline:
                    break
        _FIND.update(at=time.time(), roots=key, items=items)
    return _FIND["items"]


def find_files(q, limit=25):
    """Files and folders under the file roots (and the conversation's uploads) whose name contains q: the console's @
    picker. Spotlight answers a name search (complete and quick, whatever the size of the roots); the walk answers the
    empty query with the roots' own entries, and stands in when Spotlight has nothing."""
    roots = [P.blob_dir("uploads")] + [r for r in file_roots() if r.exists()]   # the uploads first: small, and walked before the cap can bite
    ql = q.lower().strip()
    if not ql:
        tops = {str(r) for r in roots}
        hits = sorted((it for it in _find_walk(roots) if str(Path(it[1]).parent) in tops), key=lambda it: (it[2] != "dir", it[0].lower()))
    else:
        hits, seen = [], set()
        safe = ql.replace("\\", "").replace('"', "").replace("*", "")
        try:
            cmd = ["mdfind"] + sum([["-onlyin", str(r)] for r in roots], []) + [f'kMDItemFSName == "*{safe}*"cd']
            found = subprocess.run(cmd, capture_output=True, text=True, timeout=4).stdout.splitlines()
        except Exception:
            found = []
        for pth in found + [it[1] for it in _find_walk(roots) if ql in it[0].lower()]:
            fp = Path(pth)
            if pth in seen or fp.name.startswith(".") or any(part in FIND_SKIP or part.startswith(".") for part in fp.parts):
                continue
            seen.add(pth)
            if fp.is_dir(): hits.append((fp.name, pth, "dir"))
            elif fp.is_file(): hits.append((fp.name, pth, "file"))
        hits.sort(key=lambda it: (0 if it[0].lower().startswith(ql) else 1, it[1].count("/"), it[2] != "dir", it[0].lower()))
    return [{"name": n, "path": pth, "kind": k, "ext": Path(n).suffix.lower().lstrip(".")} for n, pth, k in hits[:limit]]


def node(p, with_children=False, limit=80):
    ext = p.suffix.lower().lstrip(".")
    if p.is_dir():
        n = {"name": p.name or str(p), "path": str(p), "kind": "dir"}
        if with_children:
            kids, skipped = [], 0
            try:
                entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                entries = []
            for e in entries:
                if e.name.startswith(".") or e.name in SKIP_DIRS:
                    skipped += 1; continue
                if len(kids) >= limit:
                    skipped += 1; continue
                kids.append(node(e))
            n["children"] = kids; n["skipped"] = skipped
            n["related"] = related_links(p, kids)
        return n
    try:
        size = p.stat().st_size
    except OSError:
        size = 0
    return {"name": p.name, "path": str(p), "kind": EXT_KIND.get(ext, "file"), "ext": ext, "size": size}


def related_links(d, kids):
    """Faint links between files that belong together: same stem (app.ts / app.test.ts /
    app.css), a README and its folder, and [[wikilinks]] / relative links in markdown."""
    links = []
    by_stem = {}
    for k in kids:
        if k["kind"] != "dir":
            stem = k["name"].split(".")[0].lower()
            by_stem.setdefault(stem, []).append(k["path"])
    for stem, paths in by_stem.items():
        for a in paths[1:]:
            links.append({"a": paths[0], "b": a, "why": "same name"})
    names = {k["name"].rsplit(".", 1)[0].lower(): k["path"] for k in kids if k["kind"] != "dir"}
    for k in kids:
        if k.get("ext") == "md" and k["size"] < 400_000:
            try:
                text = Path(k["path"]).read_text(errors="ignore")
            except Exception:
                continue
            for m in re.findall(r"\[\[([^\]|#]+)", text):
                t = names.get(m.strip().lower())
                if t and t != k["path"]:
                    links.append({"a": k["path"], "b": t, "why": "wikilink"})
            for m in re.findall(r"\]\(([^)#?]+)", text):
                t = (Path(k["path"]).parent / m.strip()).resolve()
                if t.exists() and str(t) != k["path"] and str(t.parent) == str(d.resolve()):
                    links.append({"a": k["path"], "b": str(t), "why": "link"})
    return links[:200]


# ---------------- file operations (move / rename / copy / mkdir / trash-with-approval) ----------------
FSLOG = P.LOGS / "fs.log"
PENDING = []            # requests waiting for the owner: {"id", "kind", "src", "why", "at", ...}; kept in troi.db too


def file_request(req):
    """File a request for the owner: waiting here, and in the record with everything needed to carry it out later."""
    PENDING.append(req); DB.approval_add(req["id"], req.get("kind", "trash"), req.get("src", ""), req.get("why", ""), req.get("at"), req)


def restore_requests():
    """At start: requests still open in the record wait again. A risky click is not restored (the screen has moved on)."""
    try:
        for row in DB.approvals_open():
            try:
                req = json.loads(row.get("meta") or "{}")
            except Exception:
                req = {}
            if row.get("kind") in ("trash", "kill", "setting", "session") and req.get("id") == row["id"]:
                PENDING.append(req)
            else:
                DB.approval_expire(row["id"])
    except Exception:
        pass
HISTORY = []            # done operations, newest last, for undo


def fslog(line):
    FSLOG.parent.mkdir(exist_ok=True)
    with FSLOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


def fs_op(body):
    """One file operation. Everything stays inside file_roots; nothing is ever overwritten;
    'trash' only queues a request (the owner approves it elsewhere)."""
    op = body.get("op"); src = body.get("src", ""); dst = body.get("dst", "")
    if op == "undo":
        if not HISTORY:
            return {"ok": False, "error": "nothing to undo"}
        last = HISTORY.pop()
        if last["op"] in ("move", "rename"):
            if Path(last["to"]).exists() and not Path(last["from"]).exists():
                shutil.move(last["to"], last["from"]); fslog(f"undo: {last['to']} -> {last['from']}")
                return {"ok": True, "done": f"moved back to {last['from']}"}
        if last["op"] == "copy" and Path(last["to"]).exists():
            return {"ok": False, "error": f"a copy is not undone automatically; ask the owner to trash {last['to']} if unwanted"}
        if last["op"] == "mkdir" and Path(last["to"]).is_dir() and not any(Path(last["to"]).iterdir()):
            Path(last["to"]).rmdir(); fslog(f"undo mkdir: {last['to']}"); return {"ok": True, "done": "empty folder removed"}
        return {"ok": False, "error": "that step can't be undone automatically"}
    if not src or not inside_roots(src) or (op != "mkdir" and not Path(src).exists()):
        return {"ok": False, "error": "the source is not in a folder the agent may touch"}
    S = Path(src)
    if op == "reveal":
        subprocess.run(["open", "-R", src]); return {"ok": True, "done": "shown in Finder"}
    if op == "mkdir":
        if not inside_roots(str(S.parent)) or S.exists():
            return {"ok": False, "error": "already exists or outside the allowed folders"}
        S.mkdir(parents=False); HISTORY.append({"op": "mkdir", "to": str(S)}); fslog(f"mkdir {S}"); return {"ok": True, "done": f"created {S}"}
    if op in ("move", "copy"):
        if not dst or not inside_roots(dst):
            return {"ok": False, "error": "the destination is not in a folder the agent may touch"}
        D = Path(dst)
        if D.is_dir():
            D = D / S.name
        if D.exists():
            return {"ok": False, "error": f"{D.name} already exists there; nothing is ever overwritten"}
        if str(D).startswith(str(S) + "/"):
            return {"ok": False, "error": "cannot move a folder into itself"}
        if op == "move":
            shutil.move(str(S), str(D)); HISTORY.append({"op": "move", "from": str(S), "to": str(D)}); fslog(f"move {S} -> {D}")
        else:
            (shutil.copytree if S.is_dir() else shutil.copy2)(str(S), str(D)); HISTORY.append({"op": "copy", "from": str(S), "to": str(D)}); fslog(f"copy {S} -> {D}")
        return {"ok": True, "done": f"{'moved' if op == 'move' else 'copied'} to {D}", "to": str(D)}
    if op == "rename":
        name = re.sub(r"[/\\]", "", body.get("name", "")).strip()
        if not name:
            return {"ok": False, "error": "no name given"}
        D = S.parent / name
        if D.exists():
            return {"ok": False, "error": f"{name} already exists"}
        S.rename(D); HISTORY.append({"op": "rename", "from": str(S), "to": str(D)}); fslog(f"rename {S} -> {D}")
        return {"ok": True, "done": f"renamed to {name}", "to": str(D)}
    if op == "trash":
        rid = f"{int(time.time())}-{len(PENDING) + 1}"
        file_request({"id": rid, "kind": "trash", "src": src, "why": body.get("why", ""), "at": time.time()})
        fslog(f"trash requested {rid}: {src} ({body.get('why', '')})")
        try:
            subprocess.Popen([str(HOME / "backtalk" / ".venv" / "bin" / "python"), str(HERE / "telegram.py"), "send",
                              f"{AGENT} wants to move to the Trash: {src}\n{body.get('why', '')}\nReply 'approve' or 'reject' (or use the console)."],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return {"ok": True, "pending": rid, "done": "waiting for the owner's approval"}
    return {"ok": False, "error": "unknown operation"}


def fs_approve(rid, ok):
    global PENDING
    match = [p for p in PENDING if p["id"] == rid] if rid else PENDING[-1:]
    if not match:
        return {"ok": False, "error": "no such pending request"}
    req = match[0]; PENDING = [p for p in PENDING if p is not req]; DB.approval_decide(req["id"], ok)
    if not ok:
        fslog(f"rejected {req['id']}: {req['src']}"); return {"ok": True, "done": "rejected"}
    src = req["src"]
    if req.get("kind") == "session":                                    # the agent asked; the owner said yes: off the list, its lines kept
        done = DB.session_delete(req.get("session", "")); fslog(f"session deleted {req['id']}: {src} (approved by the owner)")
        return {"ok": bool(done), "done": f"deleted the session: {src}" if done else "", "error": "" if done else "no such session"}
    if req.get("kind") == "click":
        act = req.get("action") or {}
        verb = {"click": "c", "double": "dc", "right": "rc"}.get(act.get("kind"), "c")
        r = subprocess.run(["/opt/homebrew/bin/cliclick", f"{verb}:{act.get('x')},{act.get('y')}"], capture_output=True, text=True, timeout=20)
        fslog(f"clicked {req['id']}: {req['src']} (approved by the owner)")
        return {"ok": r.returncode == 0, "done": f"clicked {req['src']}", "error": r.stderr.strip()[:200]}
    if req.get("kind") == "kill":
        r = APPS.do("kill", src); fslog(f"force-quit {req['id']}: {src} (approved by the owner)"); return r
    if req.get("kind") == "setting":
        ap = req.get("apply") or {}
        if ap.get("settings"):
            cur = apply_settings(ap["settings"], settings())
            SETTINGS.write_text(json.dumps(cur, indent=2), encoding="utf-8")
            fslog(f"setting applied {req['id']}: {src} (approved by the owner)")
            return {"ok": True, "done": f"applied: {src}"}
        if ap.get("phrase"):
            ok, err = say("(verified) " + ap["phrase"])
            fslog(f"verb released {req['id']}: {ap['phrase']} (approved by the owner)")
            return {"ok": ok, "done": f"sent to the voice line: {ap['phrase']}" if ok else "", "error": err}
        return {"ok": False, "error": "nothing to apply"}
    if not inside_roots(src) or not Path(src).exists():
        return {"ok": False, "error": "it is gone already or outside the allowed folders"}
    # the macOS Trash, so it can be put back from the Finder like anything else
    r = subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{src}"'], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {"ok": False, "error": "Finder refused: " + r.stderr.strip()[:200]}
    fslog(f"trashed {req['id']}: {src} (approved by the owner)")
    return {"ok": True, "done": f"moved to the Trash: {src}"}


import importlib.util as _ilu
_apps_spec = _ilu.spec_from_file_location("apps", HERE / "apps.py"); APPS = _ilu.module_from_spec(_apps_spec); _apps_spec.loader.exec_module(APPS)


def settings():
    return {**SETTING_DEFAULTS, **_read_json(SETTINGS)}


def say(text):
    """Write one line into the pipe backtalk reads. Never blocks."""
    text = " ".join(text.split())
    if not text:
        return False, "empty"
    if not FIFO.exists():
        return False, "the voice line is not running with the console (start it with the Desktop shortcut)"
    try:
        fd = os.open(str(FIFO), os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        return False, "the voice line is not listening yet"
    try:
        os.write(fd, (text + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return True, ""


# ---- the settings guard: protected changes need the PIN (console unlock), the owner's Telegram approve,
#      or, for spoken orders, the owner's verified voice (checked in voice.py). The PIN lives in the
#      Keychain (troi-of-silo-one.pin, set by onboarding or `keychain.py set pin`), never in a file.
import hmac
import secrets
UNLOCKS = {}                      # token -> expiry
PIN_FAILS = []                    # timestamps of wrong PINs
PROTECTED_PHRASES = {"noask": "stop asking for permission", "micopen": "go hands free", "clear": "clear the session"}


def keychain(name):
    return KC.get(name)


def pin_set():
    return KC.has("pin")


FACE_PY = (HERE / ".venv-face" / "bin" / "python", HERE / "face.py")
FACE_PRINT = P.PRINTS / "face" / "owner.npy"
FACE_LAST = {"t": 0.0}


def face_env():
    return FACE_PY[0].exists() and FACE_PY[1].exists()


def face_print():
    return FACE_PRINT.exists()


def face_verify():
    """One fresh photo against the owner's face print. {"ok", "sim", "error"}; at most one check every 4 s."""
    if not face_env():
        return {"ok": False, "error": "face ID is not installed (.venv-face)"}
    if not face_print():
        return {"ok": False, "error": "no face print yet (Learn my face in the console)"}
    if time.time() - FACE_LAST["t"] < 4:
        return {"ok": False, "error": "a face check is already running; try again in a moment"}
    FACE_LAST["t"] = time.time()
    try:
        r = subprocess.run([str(FACE_PY[0]), str(FACE_PY[1]), "verify"], capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"ok": False, "error": r.stderr.strip()[-200:] or "face check failed"}
    except Exception as e:
        d = {"ok": False, "error": f"face check failed: {e}"}
    fslog(f"face check: {'match' if d.get('ok') else 'no match'} {d.get('sim', '')} {d.get('error', '')}".strip())
    return d


def face_enrol_bg():
    """Five shots, in the background; the page watches /config for the print to appear."""
    try:
        subprocess.Popen([str(FACE_PY[0]), str(FACE_PY[1]), "enrol"], stdout=open(P.LOGS / "face.log", "a"), stderr=subprocess.STDOUT)
        fslog("face enrolment started")
    except Exception as e:
        fslog(f"face enrolment failed to start: {e}")


def guard_on():
    return settings().get("guard_settings", True) is not False


def telegram_paired():
    try:
        return bool(json.loads(DB.doc("telegram").read_text()).get("owner"))
    except Exception:
        return False


def has_verifier():
    return pin_set() or telegram_paired() or (P.PRINTS / "voice" / "owner.npy").exists() or face_print()


NEEDS_PIN = "that changes how the agent is set up: unlock the console with your PIN first (or approve on Telegram)"


def untrusted(text):
    """Text from outside (the console, curl, the agent's own shell) never carries the voice line's "(verified)" mark:
    only this server adds it, after an unlock."""
    return re.sub(r"^\s*(\(\s*verified\s*\)\s*)+", "", str(text or ""), flags=re.I)


def from_telegram_bridge(addr):
    """True only when the caller on this socket is the Telegram bridge service itself (our telegram.py, run by launchd),
    so "via telegram" cannot be claimed by anything else on this Mac, the agent's shell included."""
    try:
        port = int(addr[1])
        out = subprocess.run(["lsof", "-nP", f"-iTCP@127.0.0.1:{port}", "-sTCP:ESTABLISHED", "-Fp"], capture_output=True, text=True, timeout=5).stdout
        pids = {int(l[1:]) for l in out.splitlines() if l.startswith("p")} - {os.getpid()}
        for pid in pids:
            info = subprocess.run(["ps", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True, timeout=5).stdout.strip().split(None, 1)
            if len(info) == 2 and info[0] == "1" and info[1] == f"{HOME / 'backtalk' / '.venv' / 'bin' / 'python'} {HERE / 'telegram.py'}":
                return True
    except Exception:
        pass
    return False


def setup_open(body, headers=None):
    """The welcome's writes are open until the owner has been welcomed with something that can verify them; after that
    (and for replacing a kept secret) they need an unlocked console, so nobody else, the agent included, can re-set it."""
    return not settings().get("welcomed") or not has_verifier() or unlocked(body, headers)


def unlocked(body, headers=None):
    tok = str((body or {}).get("unlock") or (headers.get("X-Troi-Unlock", "") if headers else ""))
    exp = UNLOCKS.get(tok)
    if not tok or not exp:
        return False
    if exp < time.time():
        UNLOCKS.pop(tok, None); return False
    return True


def try_unlock(pin):
    now = time.time()
    PIN_FAILS[:] = [t for t in PIN_FAILS if now - t < 600]
    if len(PIN_FAILS) >= 5:
        return None, "too many wrong PINs; try again in ten minutes"
    real = KC.get("pin")
    if not real:
        return None, "no PIN is set yet (onboarding sets it, or: troi-console/keychain.py set pin)"
    if not hmac.compare_digest(str(pin).strip(), real):
        PIN_FAILS.append(now); fslog("wrong PIN at the console"); return None, "wrong PIN"
    tok = secrets.token_hex(16); UNLOCKS[tok] = now + 15 * 60
    fslog("console unlocked with the PIN (15 minutes)")
    return tok, ""


def protected_changes(body, cur):
    """Which of these settings changes lower the guard? Returns a plain-words list."""
    out = []
    if body.get("lan") is True and cur.get("lan") is not True:
        out.append("reachable on the network")
    if body.get("lan") == "tailscale" and not cur.get("lan"):
        out.append("reachable over Tailscale")
    if body.get("voice_id") in ("off", "learn") and cur.get("voice_id") != body["voice_id"]:
        out.append("voice ID " + body["voice_id"])
    if isinstance(body.get("voice_id_threshold"), (int, float)) and float(body["voice_id_threshold"]) < float(cur.get("voice_id_threshold", 0.78)) - 1e-9:
        out.append(f"voice ID looser ({float(body['voice_id_threshold']):.2f})")
    if body.get("wake_word") is False and cur.get("wake_word", True) is not False:
        out.append("wake word off")
    if body.get("face_gate") is False and cur.get("face_gate") is True:
        out.append("face gate off")
    if body.get("eyes") in ("every", "watch", "screen") and cur.get("eyes", "off") == "off":
        out.append(("screen sight on" if body["eyes"] == "screen" else "camera on (" + body["eyes"] + ")"))
    if body.get("face_id") == "learn":
        out.append("face ID enrolment")
    if body.get("guard_settings") is False and cur.get("guard_settings", True) is not False:
        out.append("the settings guard off")
    if body.get("welcomed") is False and cur.get("welcomed"):
        out.append("the welcome again")
    if isinstance(body.get("owner"), str) and cur.get("welcomed") and body["owner"].strip() != cur.get("owner", ""):
        out.append("the owner's name")
    return out


def apply_settings(body, cur):
    if isinstance(body.get("wake_word"), bool):
        cur["wake_word"] = body["wake_word"]
    if isinstance(body.get("lan"), bool) or body.get("lan") == "tailscale":   # answer beyond this Mac (a phone's console); takes effect at the next start
        cur["lan"] = body["lan"]
    if isinstance(body.get("github_orgs"), list):                        # the GitHub orgs and users the CI watch follows (Routines › CI watch)
        cur["github_orgs"] = list(dict.fromkeys(o.strip() for o in body["github_orgs"] if isinstance(o, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", o.strip())))[:24]
    if isinstance(body.get("face_gate"), bool):
        cur["face_gate"] = body["face_gate"]
    if body.get("eyes") in ("off", "every", "watch", "screen"):
        cur["eyes"] = body["eyes"]
    if body.get("face_id") == "learn":
        face_enrol_bg()
    if isinstance(body.get("face_id_threshold"), (int, float)) and 0.5 <= float(body["face_id_threshold"]) <= 0.95:
        cur["face_id_threshold"] = round(float(body["face_id_threshold"]), 2)
    if body.get("voice_id") in ("off", "on", "learn"):
        cur["voice_id"] = body["voice_id"]
        if body["voice_id"] == "learn":
            for f in (P.PRINTS / "voice").glob("clip-*.npy"):   # start a fresh lesson
                f.rename(f.with_suffix(".npy.old"))
    if isinstance(body.get("hands"), dict):
        h = dict(cur.get("hands") or {}); h.update({k: float(v) for k, v in body["hands"].items() if k in ("pinch_close", "pinch_open", "ext", "dwell_ms", "magnet")}); cur["hands"] = h
    if isinstance(body.get("voice_id_threshold"), (int, float)) and 0.6 <= float(body["voice_id_threshold"]) <= 0.95:
        cur["voice_id_threshold"] = round(float(body["voice_id_threshold"]), 2)
    if isinstance(body.get("guard_settings"), bool):
        cur["guard_settings"] = body["guard_settings"]
    if isinstance(body.get("living_greeting"), bool):
        cur["living_greeting"] = body["living_greeting"]
    if re.fullmatch(r"\d\d:\d\d", str(body.get("brief_time", ""))):
        cur["brief_time"] = body["brief_time"]
    if body.get("tts") in ("kokoro", "elevenlabs"):
        cur["tts"] = body["tts"]
    if isinstance(body.get("elevenlabs_voice"), str) and re.fullmatch(r"[A-Za-z0-9_-]{0,64}", body["elevenlabs_voice"]):
        cur["elevenlabs_voice"] = body["elevenlabs_voice"]
    if cur.get("tts") == "elevenlabs" and not cur.get("elevenlabs_voice"):   # no voice chosen yet: your own first, else the first listed
        try:
            vs = elevenlabs_voices().get("voices") or []
            pick = next((v for v in vs if v.get("category") == "cloned"), None) or (vs[0] if vs else None)
            if pick:
                cur["elevenlabs_voice"] = pick["voice_id"]
        except Exception:
            pass
    if "tts" in body or "elevenlabs_voice" in body:            # backtalk reads its own file at start; the voice line follows console.json live
        try:
            bp = HOME / "backtalk" / "backtalk.json"; bt = _read_json(bp)
            bt["elevenlabs"] = {**bt.get("elevenlabs", {}), "enabled": cur.get("tts") == "elevenlabs" and bool(cur.get("elevenlabs_voice")), "voice_id": cur.get("elevenlabs_voice", "")}
            bp.write_text(json.dumps(bt, indent=1), encoding="utf-8")
        except Exception:
            pass
    if isinstance(body.get("welcomed"), bool):
        cur["welcomed"] = body["welcomed"]
    if isinstance(body.get("owner"), str) and 0 < len(body["owner"].strip()) <= 40:
        cur["owner"] = body["owner"].strip()
    return cur


def queue_setting(src, why, apply):
    """File a protected change for the owner: a card on the console (approve needs the PIN) and a Telegram message."""
    rid = f"{int(time.time())}-{len(PENDING) + 1}"
    file_request({"id": rid, "kind": "setting", "src": src, "why": why, "apply": apply, "at": time.time()})
    fslog(f"setting requested {rid}: {src} ({why})")
    try:
        subprocess.Popen([str(HOME / "backtalk" / ".venv" / "bin" / "python"), str(HERE / "telegram.py"), "send",
                          f"{AGENT} was asked to change a protected setting: {src} ({why}).\nReply 'approve' or 'reject'."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return rid


PARTIAL = HOME / "backtalk" / ".voice_partial"


def voice_busy():
    """A turn is in flight (voice.py keeps backtalk/.voice_busy for the whole of it, spoken or silent)."""
    b = HOME / "backtalk" / ".voice_busy"
    try:
        return b.exists() and time.time() - b.stat().st_mtime < 900
    except OSError:
        return False


def partial_text():
    """The reply the brain is producing right now, word by word (voice.py mirrors the stream)."""
    try:
        if PARTIAL.exists() and time.time() - PARTIAL.stat().st_mtime < 40:
            return PARTIAL.read_text()[-4000:]
    except OSError:
        pass
    return ""


def launchd_jobs():
    out = {}
    try:
        for line in subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2].startswith("com.troi-of-silo-one."):
                out[parts[2][len("com.troi-of-silo-one."):]] = {"loaded": True, "running": parts[0] != "-"}
    except Exception:
        pass
    return out


def last_log_line(p):
    try:
        lines = Path(p).read_text(errors="ignore").splitlines()
        return lines[-1][:160] if lines else ""
    except Exception:
        return ""


def reports_list():
    d = P.blob_dir("reports")
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.glob("????-??-??.html"), reverse=True)[:60]:
        day = f.stem; info = {}
        try:
            info = json.loads((d / (day + ".json")).read_text())
        except Exception:
            pass
        n = sum(len(r.get("commits", [])) for r in info.get("local", [])) + sum(len(r.get("commits", [])) for r in info.get("github", {}).get("repos", []))
        out.append({"date": day, "pdf": (d / (day + ".pdf")).exists(), "commits": n, "notes": len(info.get("vault", [])), "narrative": bool(info.get("narrative")), "built": info.get("built", "")})
    return out


def github_orgs(cfg=None):
    """The GitHub orgs and users the CI watch and the report follow: github_orgs (Routines › CI watch), or the old single github_org."""
    cfg = settings() if cfg is None else cfg
    orgs = [str(o).strip() for o in (cfg.get("github_orgs") or []) if str(o).strip()]
    if not orgs and cfg.get("github_org"):
        orgs = [str(cfg["github_org"]).strip()]
    return list(dict.fromkeys(orgs))


def routines():
    """Everything that runs on a clock, with its schedule, switch and last run; the reminders; the reports."""
    cfg = settings(); st = json.loads(DB.doc("pulse-state").read_text()) if DB.doc("pulse-state").exists() else {}; ld = launchd_jobs()
    gh = st.get("gh", {}) if isinstance(st, dict) else {}
    green = sum(1 for v in gh.values() if isinstance(v, dict) and v.get("conclusion") == "success")
    red = sum(1 for v in gh.values() if isinstance(v, dict) and v.get("conclusion") == "failure")
    orgs = github_orgs(cfg)
    jobs = [
        {"id": "brief", "name": "Morning brief", "when": cfg.get("brief_time", "08:00"), "editable": True, "enabled": cfg.get("brief_enabled", True) is not False, "last": st.get("brief_done", ""), "detail": "spoken, from the Morning Brief job in the vault"},
        {"id": "report", "name": "End-of-day report", "when": cfg.get("report_time", "18:30"), "editable": True, "enabled": cfg.get("report_enabled", True) is not False, "last": st.get("report_done", ""), "detail": "what changed today: commits, CI, notes, files; the PDF goes to Telegram"},
        {"id": "ci", "name": "CI watch", "when": "every 3 min", "enabled": bool(orgs), "last": "", "orgs": orgs, "detail": (f"{', '.join(orgs)}: {green} green, {red} failed" if orgs else "no GitHub org or user yet: add one below (it needs gh signed in)")},
        {"id": "servers", "name": "Server watch", "when": "every 15 min", "enabled": bool((_read_json(P.DATA / "servers.json") or {}).get("servers")), "last": "", "detail": (lambda sv, iss: f"{len(sv)} servers, {len(iss)} open issue(s)" + (": " + "; ".join(iss[:3]) if iss else "") if sv else "no servers yet (servers.py add <name> <ssh-host>)")((_read_json(P.DATA / "servers.json") or {}).get("servers", []), st.get("servers") or [])},
        {"id": "calendar", "name": "Calendar", "when": "every minute", "enabled": True, "last": "", "detail": "a heads-up 15 minutes before each event in Calendar.app; the brief lists the day"},
        {"id": "backup", "name": "Vault backup", "when": "23:30", "enabled": ld.get("vault-backup", {}).get("loaded", False), "last": last_log_line(P.LOGS / "backup.log"), "detail": "commits and pushes the vault, then sends the record to its backup repo; never force-pushes"},
        {"id": "housekeeping", "name": "Housekeeping", "when": "03:00", "enabled": ld.get("pulse", {}).get("running", False), "last": st.get("housekept", ""), "detail": "rotates logs; captures older than 14 days go to the Trash (starred ones stay)"},
        {"id": "compact", "name": "Session compaction", "when": "03:30", "enabled": ld.get("pulse", {}).get("running", False), "last": st.get("compacted", ""), "detail": "shrinks the shared conversation's memory, keeps the thread"},
        {"id": "telegram", "name": "Telegram bridge", "when": "always on", "enabled": ld.get("telegram", {}).get("running", False), "last": "", "detail": "text, photos, voice notes, approvals, /call"},
        {"id": "globe", "name": "The globe", "when": "always on", "enabled": ld.get("ring", {}).get("running", False), "last": "", "detail": "on every Space; double-click opens the console"},
    ]
    try:
        rem = json.loads(DB.doc("reminders").read_text())
        rem = sorted([r for r in rem if isinstance(r, dict)], key=lambda r: r.get("at", 0))[:30]
    except Exception:
        rem = []
    return {"jobs": jobs, "reminders": rem, "reports": reports_list(), "pulse": ld.get("pulse", {}).get("running", False)}


# ---- AG-UI (docs.ag-ui.com) on the native line: POST /agent takes RunAgentInput and answers with the standard events
#      over SSE, built from what the voice line leaves behind while the brain works: the growing reply
#      (.voice_partial), the tool in use (.voice_tool), the state (.voice_state), cards (cache/cards.jsonl) and
#      approvals (PENDING). GET /events is the same vocabulary as a running feed of the whole conversation.
import uuid                                                       # noqa: E402


def agui(type_, **kw):
    kw["type"] = type_; kw["timestamp"] = int(time.time() * 1000)
    return "data: " + json.dumps(kw) + "\n\n"


def voice_state():
    try:
        st = (HOME / "backtalk" / ".voice_state").read_text().strip() or "idle"
    except Exception:
        st = "off"
    return "working" if st == "idle" and voice_busy() else st


def voice_tool_info():
    """The tool in the brain's hands right now, {"name", "detail"} (voice.py mirrors it), or None."""
    try:
        raw = (HOME / "backtalk" / ".voice_tool").read_text().strip()
    except Exception:
        return None
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            d = json.loads(raw)
            return {"name": str(d.get("name") or ""), "detail": str(d.get("detail") or "")} if d.get("name") else None
        except ValueError:
            return None
    return {"name": raw, "detail": ""}                       # a bare name, as an older voice line writes it


def voice_tool():
    t = voice_tool_info()
    return t["name"] if t else ""


def agent_run(thread_id, run_id, text, silent=False, timeout=300):
    """Yields SSE frames for one turn. The line goes in through the typing pipe like anything typed on the console.
    AG-UI's order is kept: nothing else while a text message or a tool call is open, so the reply is closed before a
    card, an approval or a tool goes out and reopened for what the brain says next; state changes wait for a gap."""
    yield agui("RUN_STARTED", threadId=thread_id, runId=run_id)
    line = f"(written: {text})" if silent else text
    start = LOG.stat().st_size if LOG.exists() else 0
    cpos = CARDS.stat().st_size if CARDS.exists() else 0
    seen_pending = {p["id"] for p in PENDING}
    ok, err = say(line)
    if not ok:
        yield agui("RUN_ERROR", message=err, code="line"); return
    box = {"mid": None, "sent": "", "tool": None, "state": "", "pending_state": None}

    def close_text():
        if box["mid"] is not None:
            m = box["mid"]; box["mid"] = None
            return agui("TEXT_MESSAGE_END", messageId=m)
        return ""

    def gap():                                   # a moment between messages: the state that changed meanwhile goes out
        if box["pending_state"] is not None and box["tool"] is None and box["mid"] is None:
            v = box["pending_state"]; box["pending_state"] = None
            return agui("CUSTOM", name="silo.state", value=v)
        return ""

    seen_you, quiet_since, t0 = False, None, time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.15)
        st = voice_state()
        if st != box["state"]:
            box["state"] = st; box["pending_state"] = st
        # the tool in use, and what it is on (its input, once the brain has finished writing it): a new call when the
        # tool changes or the same tool is on something else; the detail alone when it arrives for the call in flight
        ti = voice_tool_info(); tn = ti["name"] if ti else ""; td = ti["detail"] if ti else ""
        cur = box["tool"]
        new_call = bool(tn) and (not cur or tn != cur[1] or bool(td and cur[2] and td != cur[2]))
        if cur and (not tn or new_call):
            yield agui("TOOL_CALL_END", toolCallId=cur[0]); box["tool"] = cur = None; yield gap()
        if new_call:
            yield close_text(); yield gap()
            cur = box["tool"] = (uuid.uuid4().hex, tn, td); yield agui("TOOL_CALL_START", toolCallId=cur[0], toolCallName=tn)
            if td:
                yield agui("TOOL_CALL_ARGS", toolCallId=cur[0], delta=json.dumps({"detail": td}))
        elif cur and td and not cur[2]:
            box["tool"] = cur = (cur[0], tn, td); yield agui("TOOL_CALL_ARGS", toolCallId=cur[0], delta=json.dumps({"detail": td}))
        # cards and approvals: between messages, never inside one or inside a tool call
        cards, cpos = read_cards(cpos)
        news = [agui("CUSTOM", name=c["name"], value=c.get("value")) for c in cards]
        for pnd in PENDING:
            if pnd["id"] not in seen_pending:
                seen_pending.add(pnd["id"]); news.append(agui("CUSTOM", name="silo.approval", value={"id": pnd["id"], "kind": pnd.get("kind", "trash"), "subject": pnd.get("src", ""), "why": pnd.get("why", ""), "status": "open"}))
        if news and box["tool"] is None:
            yield close_text()
            for n in news: yield n
            news = []
        # the reply as it grows (text and tool calls interleave; each stretch of text is its own message)
        part = DIRECTIONS.sub("", partial_text() or "")
        if box["tool"] is None and part:
            if part.startswith(box["sent"]) and len(part) > len(box["sent"]):
                if box["mid"] is None:
                    yield gap(); box["mid"] = uuid.uuid4().hex; yield agui("TEXT_MESSAGE_START", messageId=box["mid"], role="assistant")
                yield agui("TEXT_MESSAGE_CONTENT", messageId=box["mid"], delta=part[len(box["sent"]):]); box["sent"] = part
            elif not part.startswith(box["sent"]) and part != box["sent"]:
                yield close_text(); yield gap(); box["mid"] = uuid.uuid4().hex; box["sent"] = part
                yield agui("TEXT_MESSAGE_START", messageId=box["mid"], role="assistant"); yield agui("TEXT_MESSAGE_CONTENT", messageId=box["mid"], delta=part)
        elif box["mid"] is not None and not part:                     # the turn's text is done
            yield close_text(); yield gap()
        # the end: our line was taken, and the line has been quiet since
        if not seen_you and LOG.exists():
            with LOG.open("rb") as f:
                f.seek(start); chunk = f.read().decode("utf-8", "replace")
            seen_you = any(LINE.match(r) and LINE.match(r).group(3) == "you" and text[:40] in r for r in chunk.splitlines())
        idle = seen_you and st == "idle" and box["tool"] is None and not part
        if idle:
            quiet_since = quiet_since or time.time()
            if time.time() - quiet_since > 1.5:
                break
        else:
            quiet_since = None
    if box["tool"]:
        yield agui("TOOL_CALL_END", toolCallId=box["tool"][0]); box["tool"] = None
    if box["sent"] == "" and LOG.exists():                                # the tap missed: take the finished sentences from the log
        with LOG.open("rb") as f:
            f.seek(start); chunk = f.read().decode("utf-8", "replace")
        said = [DIRECTIONS.sub("", TIMING.sub("", m.group(4))).replace("⏎", "\n") for m in (LINE.match(r) for r in chunk.splitlines()) if m and m.group(3) == NAME]
        if said:
            box["mid"] = uuid.uuid4().hex; yield agui("TEXT_MESSAGE_START", messageId=box["mid"], role="assistant"); yield agui("TEXT_MESSAGE_CONTENT", messageId=box["mid"], delta=" ".join(said))
    yield close_text()
    yield agui("CUSTOM", name="silo.state", value="idle")
    yield agui("RUN_FINISHED", threadId=thread_id, runId=run_id)


def events_feed(pos, cpos):
    """Everything, as it happens: finished lines as messages, notes and cards and approvals as custom events."""
    thread = current_session() or "voice"
    yield agui("RUN_STARTED", threadId=thread, runId="feed")
    state, seen_pending, last_partial = "", {p["id"] for p in PENDING}, ""
    while True:
        items, pos = transcript(pos)
        for it in items:
            if it.get("role") in ("you", "agent"):
                mid = uuid.uuid4().hex
                yield agui("TEXT_MESSAGE_START", messageId=mid, role="user" if it["role"] == "you" else "assistant")
                yield agui("TEXT_MESSAGE_CONTENT", messageId=mid, delta=it["text"]); yield agui("TEXT_MESSAGE_END", messageId=mid)
            elif it.get("role") in ("note", "ignored"):
                yield agui("CUSTOM", name="silo.note", value={"text": it["text"], "role": it["role"]})
        cards, cpos = read_cards(cpos)
        for c in cards:
            yield agui("CUSTOM", name=c["name"], value=c.get("value"))
        for pnd in PENDING:
            if pnd["id"] not in seen_pending:
                seen_pending.add(pnd["id"]); yield agui("CUSTOM", name="silo.approval", value={"id": pnd["id"], "kind": pnd.get("kind", "trash"), "subject": pnd.get("src", ""), "why": pnd.get("why", ""), "status": "open"})
        st = voice_state()
        if st != state:
            state = st; yield agui("CUSTOM", name="silo.state", value=st)
        part = DIRECTIONS.sub("", partial_text() or "")
        if part != last_partial:
            last_partial = part; yield agui("CUSTOM", name="silo.partial", value={"text": part})
        yield ": keepalive\n\n" if not items and not cards else ""
        time.sleep(0.4)


TAILSCALE_CLIS = ("/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/opt/homebrew/bin/tailscale", "/usr/local/bin/tailscale")


def _serve_status():
    """What `tailscale serve` publishes on the tailnet, or "" (bounded: the command waits forever when Serve is not enabled)."""
    for cli in TAILSCALE_CLIS:
        if Path(cli).exists():
            try:
                return subprocess.run([cli, "serve", "status"], capture_output=True, text=True, timeout=5).stdout or ""
            except Exception:
                return ""
    return ""


def _serve_holds(port):
    """Does Tailscale's own https listener (a serve rule) hold this port on the tailnet side? Then this server keeps to the
    Mac itself and Tailscale carries the phone: binding every interface would fail with "address already in use"."""
    return f":{port} " in _serve_status() or f":{port}\n" in _serve_status()


def _tailscale():
    """This Mac on its tailnet, when Tailscale runs: its MagicDNS name and addresses (the safe way in from a phone anywhere),
    every form of them a browser may put in an Origin header, and whether Tailscale serves the console over https."""
    for cli in TAILSCALE_CLIS:
        if not Path(cli).exists():
            continue
        try:
            st = json.loads(subprocess.run([cli, "status", "--json"], capture_output=True, text=True, timeout=5).stdout or "{}")
        except Exception:
            return None
        me = st.get("Self") or {}
        ips = [ip for ip in me.get("TailscaleIPs", []) if ip]
        name = (me.get("DNSName") or "").rstrip(".").lower()
        if not ips and not name:
            return None
        hosts = {ip.lower() for ip in ips if ":" not in ip} | {"[" + ip.lower() + "]" for ip in ips if ":" in ip}
        if name:
            hosts.add(name)
        served = _serve_status()
        return {"name": name, "ip": next((ip for ip in ips if ":" not in ip), ips[0] if ips else ""), "hosts": hosts,
                "running": st.get("BackendState") == "Running", "https": bool(name) and (f"https://{name} (" in served or f"https://{name}\n" in served)}
    return None


TAILSCALE = _tailscale()
TAILNET = (ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48"))   # the addresses Tailscale gives


def from_tailnet(addr):
    """Did this connection come over Tailscale (or from this Mac itself)?"""
    try:
        a = ipaddress.ip_address(addr.split("%")[0])
    except ValueError:
        return False
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_loopback or any(a in n for n in TAILNET)


def _local_hosts():
    """Every name this Mac answers to. Its own pages (the console, the galaxies) may come from any of them: localhost on the
    Mac itself, the .local name or the address when the console is open on a phone on the same network."""
    import socket
    hosts = {"127.0.0.1", "localhost", "[::1]"}
    try:
        n = socket.gethostname().lower(); hosts.update({n, n.split(".")[0], n.split(".")[0] + ".local"})
    except Exception:
        pass
    try:
        r = subprocess.run(["scutil", "--get", "LocalHostName"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            hosts.add(r.stdout.strip().lower() + ".local")
    except Exception:
        pass
    try:
        hosts.update(re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=3).stdout))
    except Exception:
        pass
    if TAILSCALE:
        hosts.update(TAILSCALE["hosts"])
    return hosts


LOCAL_HOSTS = _local_hosts()
_ORIGIN = re.compile(r"^https?://([^/:]+|\[[0-9a-f:]+\])(:\d+)?$", re.I)


def local_origin(o):
    """Is this origin one of this Mac's own pages, whichever of the Mac's names the browser used?"""
    m = _ORIGIN.match(o or "")
    return bool(m) and m.group(1).lower() in LOCAL_HOSTS


class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        o = self.headers.get("Origin") if hasattr(self, "headers") else None
        if o and local_origin(o):
            self.send_header("Access-Control-Allow-Origin", o); self.send_header("Vary", "Origin")
        super().end_headers()

    def _sse(self, gen):
        self.send_response(200)
        for k, v in (("Content-Type", "text/event-stream; charset=utf-8"), ("Cache-Control", "no-store"), ("Connection", "keep-alive"), ("X-Accel-Buffering", "no")):   # the origin header comes from end_headers(), once
            self.send_header(k, v)
        self.end_headers()
        try:
            for frame in gen:
                if frame:
                    self.wfile.write(frame.encode("utf-8")); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        # the preflight: end_headers() adds Access-Control-Allow-Origin for this Mac's own pages; it must not be sent twice
        # (a browser refuses a duplicated origin header, and every JSON POST from the console then fails without a word)
        self.send_response(204)
        for k, v in (("Access-Control-Allow-Methods", "GET, POST, OPTIONS"), ("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, X-Filename, X-Kind"), ("Access-Control-Max-Age", "600")):
            self.send_header(k, v)
        self.end_headers()

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":                                             # people belong in the console app
            self.send_response(302); self.send_header("Location", os.environ.get("TROI_CONSOLE_URL", "http://localhost:3100")); self.end_headers()
        elif path == "/index.html":                                 # the old single-page console, kept only as a fallback
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/galaxy.html":
            body = (HERE / "galaxy.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif path == "/browser.jpg":
            # the agent's browser, as the bridge last saw it; asking for it keeps the bridge streaming
            try:
                (P.CACHE / ".browser-watch").touch()
            except OSError:
                pass
            f = P.CACHE / "browser.jpg"
            if not f.exists():
                return self._json({"error": "no frame yet"}, 404)
            data = f.read_bytes()
            self.send_response(200); self.send_header("Content-Type", "image/jpeg"); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        elif path == "/browser":
            try:
                (P.CACHE).mkdir(exist_ok=True); (P.CACHE / ".browser-watch").touch()   # the pane is watching: keep frames coming
            except OSError:
                pass
            info = _read_json(P.CACHE / "browser.json") or {}
            up = False
            try:
                import urllib.request as _u
                with _u.urlopen("http://127.0.0.1:9223/json/version", timeout=1) as r:
                    up = r.status == 200
            except Exception:
                up = False
            self._json({**info, "up": up, "fresh": bool(info.get("t")) and time.time() * 1000 - info.get("t", 0) < 8000})
        elif path.startswith("/sounds/"):        # the interface cues and the thinking loop (assets/*.wav, made with ElevenLabs sound effects)
            m = re.fullmatch(r"/sounds/(cue-[a-z]+|thinking-warm)\.wav", path); f = HERE / "assets" / (m.group(0).rsplit("/", 1)[1] if m else "")
            if not m or not f.exists(): self.send_response(404); self.end_headers(); return
            body = f.read_bytes(); self.send_response(200); self.send_header("Content-Type", "audio/wav"); self.send_header("Cache-Control", "max-age=86400")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif path == "/panes.js":
            body = (HERE / "panes.js").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "application/javascript; charset=utf-8"); self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif path == "/call.html":
            body = (HOME / "console" / "public" / "call.html").read_bytes()     # the console app serves it too, on your network
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif path == "/config":
            bt = _read_json(HOME / "backtalk" / "backtalk.json")          # fresh: the voice line rewrites it (effort, mic, permissions)
            self._json({
                "name": NAME,
                "key": BT.get("ptt_key", "home"),
                "mic_mode": bt.get("mic_mode", "ptt"),
                "permission_mode": bt.get("permission_mode", "ask"),
                "model": bt.get("model", BT.get("model", "claude-sonnet-5")),
                "deep_model": bt.get("deep_model", BT.get("deep_model", "claude-opus-5")),
                "effort": bt.get("effort") or "",
                "wake_word": settings()["wake_word"],
                "eyes": settings()["eyes"],
                "voice_id": settings()["voice_id"],
                "voice_print": (P.PRINTS / "voice" / "owner.npy").exists(),
                "voice_id_threshold": settings().get("voice_id_threshold", 0.78),
                "pin_set": pin_set(), "guard": guard_on(), "guarded": guard_on() and has_verifier(),
                "face_env": face_env(), "face_print": face_print(), "face_id_threshold": settings().get("face_id_threshold", 0.70),
                "vault": HANDS.get("orbs", [{}])[0].get("path", ""),
                "brief_time": settings()["brief_time"],
                "hand_tuning": settings().get("hands", SETTING_DEFAULTS["hands"]),
                "wake_names": settings()["wake_names"],
                "tts": settings().get("tts", "kokoro"), "elevenlabs_voice": settings().get("elevenlabs_voice", ""), "elevenlabs_voice_name": elevenlabs_voice_name(settings().get("elevenlabs_voice", "")), "elevenlabs_key": KC.has("elevenlabs"),
                "kokoro_voice": BT.get("voice", "bm_lewis"), "welcomed": bool(settings().get("welcomed", False)), "owner": settings().get("owner", ""), "lan": settings().get("lan", False), "github_orgs": github_orgs(), "tailscale": ({"name": TAILSCALE["name"], "ip": TAILSCALE["ip"], "https": TAILSCALE.get("https", False)} if TAILSCALE else None),
                "face": f"http://127.0.0.1:{VIS.get('port', 8790)}/faces/{VIS.get('face', 'board')}/",
                "hands": f"http://127.0.0.1:{HANDS.get('port', 8794)}/stage.html",
            })
        elif path == "/state":
            try:
                st = (HOME / "backtalk" / ".voice_state").read_text().strip() or "idle"
            except Exception:
                st = "off"
            if st == "idle" and voice_busy():
                st = "working"
            ui = []                                                   # the directives moved to GET /ui?since=N
            wave = []
            if st == "speaking":
                try:
                    smp = json.loads((HOME / "backtalk" / ".voice_waveform").read_text()).get("samples", [])
                    step = max(1, len(smp) // 32); wave = [round(abs(float(x)), 3) for x in smp[::step]][:32]
                except Exception:
                    wave = []
            live = P.LIVE
            live_p = str(live) if live.exists() and time.time() - live.stat().st_mtime < 6 else ""
            try:
                agents = sum(1 for a in agents_snapshot(light=True) if a["status"] == "active")
            except Exception:
                agents = 0
            self._json({"state": st, "voice": FIFO.exists(), "ui": ui, "settings": settings(), "pending": PENDING, "partial": partial_text(), "wave": wave, "live": live_p, "tool": voice_tool_info(), "agents": agents})
        elif path == "/agents":
            sid, f, _ = brain_paths(); ag = agents_snapshot()
            self._json({"brain": brain_now(), "agents": ag, "session": sid, "record": bool(f and f.exists()), "archived": sum(1 for a in ag if a["archived"])})
        elif path == "/find":
            self._json({"items": find_files(dict(urllib.parse.parse_qsl(query)).get("q", ""))})
        elif path == "/tree":
            q = dict(urllib.parse.parse_qsl(query)); p = q.get("path", "")
            if not p:
                return self._json({"roots": [node(r) for r in file_roots() if r.exists()]})
            if not inside_roots(p) or not Path(p).is_dir():
                return self._json({"error": "not a folder the agent may browse"}, 403)
            self._json(node(Path(p), with_children=True))
        elif path == "/file":
            q = dict(urllib.parse.parse_qsl(query)); p = q.get("p", "")
            if not inside_roots(p) or not Path(p).is_file():
                return self._json({"error": "not allowed"}, 403)
            f = Path(p); ext = f.suffix.lower().lstrip(".")
            MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml", "bmp": "image/bmp",
                    "pdf": "application/pdf", "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg", "m4a": "audio/mp4", "flac": "audio/flac", "aac": "audio/aac",
                    "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "mkv": "video/x-matroska", "glb": "model/gltf-binary", "gltf": "model/gltf+json"}
            if q.get("raw") == "1" or ext in MIME and EXT_KIND.get(ext) in ("image", "video", "audio", "model") or ext == "pdf":
                # bytes, with Range support so audio and video can seek
                size = f.stat().st_size; start, end = 0, size - 1
                rng = self.headers.get("Range", "")
                m = re.match(r"bytes=(\d*)-(\d*)", rng)
                if m and (m.group(1) or m.group(2)):
                    if m.group(1): start = int(m.group(1))
                    if m.group(2): end = int(m.group(2)) if m.group(1) else size - 1
                    if not m.group(1): start = max(0, size - int(m.group(2)))
                    end = min(end, size - 1)
                length = end - start + 1
                self.send_response(206 if m else 200)
                self.send_header("Content-Type", MIME.get(ext, "application/octet-stream")); self.send_header("Accept-Ranges", "bytes")
                if m: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(length)); self.send_header("Cache-Control", "max-age=60"); self.end_headers()
                with f.open("rb") as fh:
                    fh.seek(start); left = length
                    while left > 0:
                        chunk = fh.read(min(1 << 20, left))
                        if not chunk: break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            return
                        left -= len(chunk)
                return
            try:
                text = f.read_bytes()[:400_000].decode("utf-8", "replace")
                if "\x00" in text:
                    text = f"(binary file, {f.stat().st_size:,} bytes)"
            except Exception as e:
                text = f"(could not read: {e})"
            self._json({"path": p, "text": text, "size": f.stat().st_size, "ext": ext, "kind": EXT_KIND.get(ext, "file")})
        elif path == "/mtimes":
            q = dict(urllib.parse.parse_qsl(query)); out = {}
            for pth in q.get("p", "").split("|"):
                if pth and inside_roots(pth) and Path(pth).is_dir():
                    try:
                        st = Path(pth).stat(); out[pth] = int(st.st_mtime * 1000)
                    except OSError:
                        pass
            self._json(out)
        elif path == "/recent":
            roots = [str(r) for r in file_roots() if r.exists()]
            cmd = ["mdfind"] + sum([["-onlyin", r] for r in roots], []) + ["kMDItemContentModificationDate >= $time.today(-7) && kMDItemContentType != public.folder"]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.splitlines()
            except Exception:
                out = []
            items = []
            for pth in out:
                fp = Path(pth)
                if any(part in SKIP_DIRS or part.startswith(".") for part in fp.parts) or not fp.is_file() or fp.suffix.lower().lstrip(".") not in EXT_KIND:
                    continue
                try:
                    e = fp.suffix.lower().lstrip(".")
                    items.append({"path": pth, "name": fp.name, "ext": e, "kind": EXT_KIND.get(e, "file"), "t": int(fp.stat().st_mtime), "size": fp.stat().st_size})
                except OSError:
                    pass
            items.sort(key=lambda i: -i["t"]); self._json({"items": items[:40]})
        elif path == "/apps":
            self._json({"apps": APPS.state()})
        elif path == "/appicon":
            q = dict(urllib.parse.parse_qsl(query)); pth = Path(q.get("p", ""))
            if not str(pth).startswith(str(P.CACHE / "icons")) or not pth.is_file():
                return self._json({"error": "not allowed"}, 403)
            data = pth.read_bytes(); self.send_response(200); self.send_header("Content-Type", "image/png"); self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=3600"); self.end_headers(); self.wfile.write(data)
        elif path == "/vaultgraph":
            vault = Path(HANDS.get("orbs", [{}])[0].get("path", "")); notes, links = [], []
            by_name = {}
            for f in sorted(vault.rglob("*.md")):
                if any(part.startswith(".") for part in f.parts):
                    continue
                rel = f.relative_to(vault); top = rel.parts[0] if len(rel.parts) > 1 else ""
                notes.append({"path": str(f), "name": f.stem, "folder": top, "ext": "md", "kind": "doc", "size": f.stat().st_size})
                by_name.setdefault(f.stem.lower(), str(f))
            for n in notes:
                try:
                    txt = Path(n["path"]).read_text(errors="ignore")
                except Exception:
                    continue
                for m in re.findall(r"\[\[([^\]|#]+)", txt):
                    t = by_name.get(m.strip().lower())
                    if t and t != n["path"]:
                        links.append({"a": n["path"], "b": t})
            self._json({"notes": notes, "links": links})
        elif path == "/vaultcards":
            # one level of the vault as cards: folders (with their index note's opening lines, counts and the newest notes)
            # and notes (opening lines, size, age, tags, link count). Absolute paths, so the file tools work on them.
            vault = Path(HANDS.get("orbs", [{}])[0].get("path", "")).resolve()
            q = dict(urllib.parse.parse_qsl(query)); want = q.get("path", "")
            cur = Path(want).resolve() if want else vault
            if not vault.is_dir() or not (cur == vault or str(cur).startswith(str(vault) + "/")) or not cur.is_dir():
                return self._json({"error": "not a folder inside the vault"}, 403)
            def excerpt(f, n=230):
                try:
                    txt = f.read_text(errors="ignore")[:6000]
                except Exception:
                    return ""
                txt = re.sub(r"\A---.*?---\s*", "", txt, flags=re.S)                       # frontmatter
                lines = [l for l in txt.splitlines() if l.strip() and not l.lstrip().startswith("#") and not re.match(r"^\s*[-*]\s*\[\[", l)]
                t = " ".join(lines)
                t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t); t = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", t); t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
                t = re.sub(r"[`*_>#|]+", "", t); t = re.sub(r"\s+", " ", t).strip()
                return t[:n] + ("…" if len(t) > n else "")
            def tags(f):
                try:
                    head = f.read_text(errors="ignore")[:1500]
                except Exception:
                    return []
                m = re.search(r"^tags:\s*(.+)$", head, flags=re.M)
                out = re.findall(r"[\w/-]+", m.group(1)) if m else []
                out += re.findall(r"(?<![\w/])#([A-Za-z][\w/-]{1,30})", head)
                return sorted(set(x.strip("[]\"' ") for x in out if x and x.lower() not in ("tags",)))[:6]
            folders, notes = [], []
            try:
                entries = sorted(cur.iterdir(), key=lambda e: e.name.lower())
            except PermissionError:
                entries = []
            for e in entries:
                if e.name.startswith("."):
                    continue
                if e.is_dir():
                    mds = [m for m in e.rglob("*.md") if not any(part.startswith(".") for part in m.relative_to(e).parts)]
                    idx = e / f"{e.name}.md"
                    if not idx.exists():
                        cand = [m for m in mds if m.parent == e and m.stem.lower() == e.name.split(" - ", 1)[-1].lower()]
                        idx = cand[0] if cand else None
                    newest = sorted(mds, key=lambda m: -m.stat().st_mtime)[:3]
                    folders.append({"name": e.name, "path": str(e), "kind": "dir", "card": True, "notes": len(mds),
                                    "subs": sum(1 for d in e.iterdir() if d.is_dir() and not d.name.startswith(".")),
                                    "excerpt": excerpt(idx) if idx else "", "recent": [m.stem for m in newest],
                                    "mtime": int(max([m.stat().st_mtime for m in mds] + [e.stat().st_mtime]))})
                elif e.suffix.lower() == ".md":
                    try:
                        txt = e.read_text(errors="ignore")
                    except Exception:
                        txt = ""
                    notes.append({"name": e.stem, "path": str(e), "kind": "doc", "ext": "md", "card": True, "size": e.stat().st_size, "mtime": int(e.stat().st_mtime),
                                  "excerpt": excerpt(e), "tags": tags(e), "links": len(re.findall(r"\[\[", txt)), "words": len(txt.split())})
                elif e.is_file():
                    ext = e.suffix.lower().lstrip(".")
                    notes.append({"name": e.name, "path": str(e), "kind": EXT_KIND.get(ext, "file"), "ext": ext, "card": True, "size": e.stat().st_size, "mtime": int(e.stat().st_mtime), "excerpt": "", "tags": [], "links": 0})
            self._json({"root": str(vault), "path": str(cur), "name": cur.name if cur != vault else "Vault", "folders": folders[:60], "notes": notes[:120]})
        elif path == "/routines":
            self._json(routines())
        elif path == "/reports":
            self._json({"reports": reports_list()})
        elif path in ("/report", "/report.pdf"):
            q = dict(urllib.parse.parse_qsl(query)); d = q.get("d", "")
            if not re.fullmatch(r"\d{4}-\d\d-\d\d", d):
                return self._json({"error": "bad date"}, 400)
            f = P.blob_dir("reports") / (d + (".pdf" if path.endswith(".pdf") else ".html"))
            if not f.exists():
                return self._json({"error": "no such report"}, 404)
            data = f.read_bytes()
            self.send_response(200); self.send_header("Content-Type", "application/pdf" if path.endswith(".pdf") else "text/html; charset=utf-8")
            if path.endswith(".pdf"):
                self.send_header("Content-Disposition", f'attachment; filename="{AGENT}-end-of-day-{d}.pdf"')
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        elif path == "/session":
            try:
                sid = (HOME / "backtalk" / ".backtalk_session").read_text().strip()
            except Exception:
                sid = ""
            self._json({"live": FIFO.exists(), "session": sid})
        elif path == "/pending":
            self._json({"pending": PENDING})
        elif path == "/setup/status":
            import setup as SETUP
            st = SETUP.status(); d = doctor()
            st.update({"screen": d.get("screen", False), "accessibility": d.get("accessibility", False), "doctor": d.get("lines", []), "telegram": telegram_state(), "owner_full": settings().get("owner_full", ""),
                       "address": settings().get("address", ""), "call": settings().get("call", "sir"), "github_org": settings().get("github_org", ""), "github_orgs": github_orgs(), "backup_repo": settings().get("backup_repo", ""),
                       "github_account": settings().get("github_account", "ayesigapaul"), "backup_org": settings().get("backup_org", "Silo-One-Ug"),
                       "gh": bool(shutil.which("gh")) and subprocess.run(["gh", "auth", "token", "-u", settings().get("github_account", "ayesigapaul")], capture_output=True).returncode == 0,
                       "vault_candidates": vault_candidates(), "folder_candidates": folder_candidates(), "file_roots": settings().get("file_roots", [])})
            self._json(st)
        elif path == "/telegram":
            self._json(telegram_state())
        elif path == "/ui":
            q = dict(urllib.parse.parse_qsl(query))
            self._json({"seq": UI_SEQ["n"], "items": ui_since(int(q.get("since", 0) or 0))})
        elif path == "/images":
            self._json({"items": list_images()})
        elif path == "/img":
            q = dict(urllib.parse.parse_qsl(query))
            p = q.get("p", "")
            if not allowed_image(p):
                return self._json({"error": "not allowed"}, 403)
            data = Path(p).read_bytes()
            ext = Path(p).suffix.lower().lstrip(".")
            self.send_response(200); self.send_header("Content-Type", {"jpg": "image/jpeg", "glb": "model/gltf-binary", "gltf": "model/gltf+json"}.get(ext, "image/" + ext))
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "max-age=60"); self.end_headers(); self.wfile.write(data)
        elif path == "/transcript":
            q = dict(urllib.parse.parse_qsl(query))
            items, pos = transcript(int(q.get("pos", 0) or 0))
            cards, cpos = read_cards(int(q.get("cpos", 0) or 0)) if "cpos" in q else ([], None)
            out = {"items": items, "pos": pos}
            if cpos is not None:
                out["cards"], out["cpos"] = cards, cpos
            self._json(out)
        elif path == "/welcome":                                    # onboarding lives in the console app now
            console = os.environ.get("TROI_CONSOLE_URL", "http://localhost:3100")
            self.send_response(302); self.send_header("Location", console + "/welcome"); self.end_headers()
        elif path == "/doctor":
            self._json(doctor())
        elif path == "/voices":
            _VOICES["data"] = None                                     # asking for the list means: fresh
            self._json(elevenlabs_voices_cached())
        elif path == "/history":
            q = dict(urllib.parse.parse_qsl(query))
            try:
                tail_once()
            except Exception:
                pass
            rows = DB.messages(session=q.get("session") or None, limit=min(int(q.get("limit", 120) or 120), 1000), before=int(q["before"]) if q.get("before") else None)
            items = [{"id": r["id"], "role": r["role"], "text": r["text"], "t": (r["clock"] or "")[:5], "meta": r["meta"], "at": r["t"]} for r in rows]
            self._json({"items": items, "pos": LOG.stat().st_size if LOG.exists() else 0, "cpos": CARDS.stat().st_size if CARDS.exists() else 0, "session": current_session()})
        elif path == "/sessions":
            q = dict(urllib.parse.parse_qsl(query)); cur = current_session(); rows = DB.sessions()
            try:
                summarise_sessions(rows, cur)
            except Exception:
                pass
            out = {"sessions": rows, "current": cur}
            if q.get("deleted"):
                out["deleted"] = DB.sessions(deleted=True)
            self._json(out)
        elif path == "/approvals":
            self._json({"approvals": DB.approvals()})
        elif path == "/events":
            q = dict(urllib.parse.parse_qsl(query))
            self._sse(events_feed(int(q.get("pos", 0) or 0) or (LOG.stat().st_size if LOG.exists() else 0), int(q.get("cpos", 0) or 0) or (CARDS.stat().st_size if CARDS.exists() else 0)))
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        import subprocess   # some branches import it locally, which makes the name local to the whole method
        if self.path == "/voice":
            # a voice note from the console page (the phone's microphone): the words come back, and the page sends them as a line
            origin = self.headers.get("Origin", "")
            if origin and not local_origin(origin):
                return self._json({"ok": False, "error": "forbidden"}, 403)
            ext = Path(re.sub(r"[^A-Za-z0-9._-]", "_", self.headers.get("X-Filename", "note.webm"))).suffix.lower() or ".webm"
            n = min(int(self.headers.get("Content-Length", "0")), 30_000_000)
            tmp = P.CACHE / f"voice-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}{ext}"
            tmp.write_bytes(self.rfile.read(n))
            try:
                text = stt_text(tmp)
            except Exception as e:
                return self._json({"ok": False, "error": f"the ears did not answer: {e}"}, 500)
            finally:
                try:
                    tmp.unlink()
                except Exception:
                    pass
            return self._json({"ok": True, "text": text})
        if self.path == "/upload":
            # a file chosen on the console page. X-Kind: uploads keeps it in data/blobs/uploads (any kind, indexed in the
            # record) for the agent to read through an @ mention; otherwise a picture or model for the board's airlock
            origin = self.headers.get("Origin", "")
            if origin and not local_origin(origin):
                return self._json({"ok": False, "error": "forbidden"}, 403)
            name = re.sub(r"[^A-Za-z0-9._-]", "_", self.headers.get("X-Filename", "image.png"))[-80:] or "file"
            n = min(int(self.headers.get("Content-Length", "0")), 60_000_000)
            if self.headers.get("X-Kind") == "uploads":
                if Path(name).suffix.lower() in NOT_UPLOADED:
                    return self._json({"ok": False, "error": "not a kind of file the agent takes"}, 400)
                dst = P.blob_dir("uploads") / f"{time.strftime('%Y-%m-%d-%H%M%S')}-{name}"
                dst.write_bytes(self.rfile.read(n))
                try:
                    DB.blob_index()
                except Exception:
                    pass
                _FIND["at"] = 0.0                                          # the @ picker sees it on its next search
                return self._json({"ok": True, "path": str(dst), "name": name})
            if Path(name).suffix.lower() not in IMG_EXTS:
                return self._json({"ok": False, "error": "not an image or model"}, 400)
            dst = HOME / "barehands" / "media" / ("models" if Path(name).suffix.lower() in (".glb", ".gltf") else "misc") / name
            dst.write_bytes(self.rfile.read(n))
            return self._json({"ok": True, "path": str(dst)})
        if self.path not in ("/say", "/settings", "/board", "/show", "/ui", "/fs", "/approve", "/app", "/open", "/write", "/pending-click", "/ask", "/routines", "/unlock", "/pending-setting", "/face-verify", "/look", "/browser", "/agent", "/keychain", "/setup/profile", "/setup/vault", "/setup/services", "/setup/backup", "/setup/finish", "/star", "/agents", "/sessions"):
            return self._json({"error": "not found"}, 404)
        # localhost page only: refuse cross-site posts
        origin = self.headers.get("Origin", "")
        if origin and not local_origin(origin):                         # this machine's own pages only (by any of its names)
            return self._json({"ok": False, "error": "forbidden"}, 403)
        try:
            n = min(int(self.headers.get("Content-Length", "0")), 20000)
            body = json.loads(self.rfile.read(n) or b"{}")
            text = untrusted(body.get("text", ""))
        except Exception:
            return self._json({"ok": False, "error": "bad request"}, 400)
        if self.path == "/fs":
            try:
                r = fs_op(body)
            except Exception as e:
                r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            if r.get("ok"):
                for k in ("src", "dst", "to"):
                    v = body.get(k) or r.get(k)
                    if v:
                        ui_push({"refresh": str(Path(v).parent if not Path(v).is_dir() or k != "dst" else Path(v))})
            return self._json(r)
        if self.path == "/write":
            # an edit from the galaxy's editor: the previous version is kept in data/backups/
            p = body.get("path", ""); text = body.get("text")
            if not inside_roots(p) or not Path(p).is_file() or not isinstance(text, str):
                return self._json({"ok": False, "error": "not a file the agent may edit"})
            bdir = P.DATA / "backups" / time.strftime("%Y-%m-%d"); bdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, bdir / (time.strftime("%H%M%S") + "-" + Path(p).name))
            Path(p).write_text(text, encoding="utf-8"); fslog(f"edited {p} ({len(text)} chars, backup in {bdir})")
            return self._json({"ok": True, "done": f"saved {Path(p).name} (previous version kept in backups)"})
        if self.path == "/open":
            # open a file in its default application (or a named one); jailed like everything else
            p = body.get("path", "")
            if not inside_roots(p) or not Path(p).exists():
                return self._json({"ok": False, "error": "not in a folder the agent may touch"})
            cmd = ["open", p] if not body.get("app") else ["open", "-a", body["app"], p]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return self._json({"ok": r.returncode == 0, "done": f"opened {Path(p).name}" + (f" in {body['app']}" if body.get("app") else ""), "error": r.stderr.strip()[:200]})
        if self.path == "/routines":
            # the Routines pane: change a time, switch a job on or off, run one now, cancel a reminder
            cur = settings(); rid = str(body.get("id", "")); changed = False; done = ""
            if rid in ("brief", "report"):
                if re.fullmatch(r"\d\d:\d\d", str(body.get("when", ""))):
                    cur[f"{rid}_time"] = body["when"]; changed = True
                if isinstance(body.get("enabled"), bool):
                    cur[f"{rid}_enabled"] = body["enabled"]; changed = True
            if changed:
                SETTINGS.write_text(json.dumps(cur, indent=2), encoding="utf-8"); done = "saved"
            if rid == "reminder" and body.get("cancel"):
                try:
                    items = json.loads(DB.doc("reminders").read_text())
                    keep = [r for r in items if r.get("at") != body["cancel"]]
                    DB.doc("reminders").write_text(json.dumps(keep, indent=2)); done = "reminder cancelled" if len(keep) < len(items) else "no such reminder"
                except Exception as e:
                    done = f"could not cancel: {e}"
            if body.get("run"):
                try:
                    if rid == "report":
                        subprocess.Popen(["/usr/bin/python3", str(HERE / "report.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        done = "building today's report: it appears in the list (and on Telegram) in a minute or two"
                    elif rid == "brief":
                        ok, err = say("(scheduled morning brief: it is time. Run your Morning Brief job now and speak it.)"); done = "asked for the brief" if ok else err
                    elif rid == "compact":
                        ok, err = say("compact the session"); done = "compacting" if ok else err
                    elif rid in ("backup", "housekeeping", "ci"):
                        script = {"backup": "backup-vault.sh", "housekeeping": "housekeeping.sh", "ci": "ci-status.sh"}[rid]
                        r = subprocess.run([str(HERE / script)], capture_output=True, text=True, timeout=180)
                        out = (r.stdout.strip() or r.stderr.strip() or "done"); done = out[-700:]
                    else:
                        done = "that one runs by itself"
                except Exception as e:
                    done = f"failed: {e}"
            return self._json({"ok": True, "done": done, **routines()})
        if self.path == "/ask":
            r = ask_live(text, timeout=int(body.get("timeout", 240)))
            return self._json({"ok": r is not None, "reply": r or "", "live": FIFO.exists()})
        if self.path == "/sessions":                                  # the Sessions page, and the agent's sessions.sh
            cur = current_session()
            if body.get("request_delete"):                            # the agent asks; the owner decides on the console or Telegram
                sid = DB.session_find(str(body["request_delete"]))
                if not sid:
                    return self._json({"ok": False, "error": "no such session (sessions.sh list shows them)"}, 404)
                if sid == cur:
                    return self._json({"ok": False, "error": "that is the session in use: it cannot be deleted while it is on"}, 400)
                row = next((s for s in DB.sessions() + DB.sessions(deleted=True) if s["id"] == sid), None); title = (row or {}).get("title") or sid[:8]
                rid = f"{int(time.time())}-{len(PENDING) + 1}"
                file_request({"id": rid, "kind": "session", "src": title, "session": sid, "why": str(body.get("why", "")), "at": time.time()})
                fslog(f"session deletion requested {rid}: {title} ({body.get('why', '')})")
                try:
                    subprocess.Popen([str(HOME / "backtalk" / ".venv" / "bin" / "python"), str(HERE / "telegram.py"), "send",
                                      f"{AGENT} wants to delete a session: {title}\n{body.get('why', '')}\nReply 'approve' or 'reject' (or use the console)."],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return self._json({"ok": True, "pending": rid, "done": "waiting for the owner's approval"})
            ref = body.get("delete") or body.get("restore") or body.get("title")
            sid = DB.session_find(str(ref)) if ref else None
            if not sid:
                return self._json({"ok": False, "error": "no such session"}, 404)
            if body.get("delete") or body.get("restore"):             # the owner's own hand, proven the way an approval is: an unlocked console
                if has_verifier() and not unlocked(body, self.headers):
                    return self._json({"ok": False, "needs_unlock": True, "error": "deleting a session needs you: unlock with your PIN (or your face)"}, 403)
                if body.get("delete") and sid == cur:
                    return self._json({"ok": False, "error": "that is the session in use: start a new one first"}, 400)
                done = DB.session_delete(sid) if body.get("delete") else DB.session_restore(sid)
                fslog(f"session {'deleted' if body.get('delete') else 'restored'} by the owner: {sid[:8]}")
                return self._json({"ok": bool(done)})
            return self._json({"ok": DB.session_title(sid, str(body.get("text", "")))})
        if self.path == "/agents":                                    # the Agents page: archive a finished delegation off the chart, or all of them
            want = body.get("archive")
            done = {a["id"] for a in agents_snapshot(light=True) if a["status"] != "active"}
            ids = done if want == "finished" else ({want} & done if isinstance(want, str) else set())
            if not ids:
                return self._json({"ok": False, "error": "nothing to archive (only a finished agent can be)"}, 400)
            agents_archive(ids)
            return self._json({"ok": True, "archived": len(ids)})
        if self.path == "/agent":                                     # AG-UI: RunAgentInput in, events out
            last = next((m for m in reversed(body.get("messages") or []) if m.get("role") == "user"), None)
            text = untrusted(" ".join(str((last or {}).get("content", "")).split()))
            if not text:
                return self._json({"ok": False, "error": "no user message"}, 400)
            fp = body.get("forwardedProps") or {}
            silent = bool(fp.get("silent") or (body.get("state") or {}).get("silent"))
            if unlocked(body, self.headers):
                text = "(verified) " + text
            return self._sse(agent_run(str(body.get("threadId") or current_session() or "voice"), str(body.get("runId") or uuid.uuid4().hex), text, silent=silent, timeout=int(fp.get("timeout") or 300)))
        if self.path == "/setup/profile":                             # onboarding: who the agent serves, and how to address them
            if not setup_open(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)
            import setup as SETUP
            cfg = SETUP.load()
            for k in ("owner", "owner_full", "address", "call", "github_org", "board_label"):
                if isinstance(body.get(k), str):
                    cfg[k] = body[k].strip()[:80]
            if isinstance(body.get("file_roots"), list):                # folders the agent may organise: real folders in the home or on a drive
                home, roots = str(Path.home()), []
                for r in body["file_roots"][:24]:
                    q = Path(os.path.expanduser(str(r))).resolve()
                    if q.is_dir() and (str(q).startswith(home + "/") or str(q).startswith("/Volumes/")):
                        roots.append(str(q))
                cfg["file_roots"] = sorted(set(roots + ([cfg["vault"]] if cfg.get("vault") else [])))
            if cfg.get("owner") and not cfg.get("address"):
                cfg["address"] = cfg["owner"]
            SETUP.save(cfg)
            try:
                done = SETUP.render()
            except Exception as e:
                return self._json({"ok": False, "error": f"could not render: {e}"}, 500)
            return self._json({"ok": True, "done": done, **{k: cfg.get(k) for k in ("owner", "owner_full", "address", "call")}})
        if self.path == "/setup/vault":                               # onboarding: a new vault, or the one you have
            if not setup_open(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)
            import setup as SETUP
            try:
                where = SETUP.vault_new(body.get("path") or None) if body.get("mode") == "new" else SETUP.vault_use(str(body.get("path", "")))
                return self._json({"ok": True, "vault": where})
            except SystemExit as e:
                return self._json({"ok": False, "error": str(e)}, 400)
        if self.path == "/setup/services":
            if not setup_open(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)
            import setup as SETUP
            return self._json({"ok": True, "done": SETUP.services(str(body.get("action", "restart")), body.get("name") or None)})
        if self.path == "/setup/backup":                              # where the nightly record backup goes; "now" runs it
            if not setup_open(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)
            import setup as SETUP
            cfg = SETUP.load()
            if isinstance(body.get("backup_repo"), str):
                cfg["backup_repo"] = body["backup_repo"].strip(); SETUP.save(cfg)
            if body.get("now"):
                r = subprocess.run([str(HERE / "backup-data.sh")], capture_output=True, text=True, timeout=600)
                return self._json({"ok": r.returncode == 0, "done": (r.stdout.strip() or r.stderr.strip())[-400:]})
            return self._json({"ok": True})
        if self.path == "/setup/finish":                              # the welcome's last step: welcomed, then the voice line starts over in place
            if not setup_open(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)
            import setup as SETUP
            cfg = SETUP.load(); cfg["welcomed"] = True
            if isinstance(body.get("backup_repo"), str) and body["backup_repo"].strip():
                cfg["backup_repo"] = body["backup_repo"].strip()
            SETUP.save(cfg); SETUP.render()
            try:
                (HOME / "backtalk" / ".backtalk_session").unlink()          # the first meeting is a new conversation, with the new boot file
            except OSError:
                pass
            return self._json({"ok": True, "voice": restart_voice()})
        if self.path == "/star":                                      # keep a capture past its retention (or let it go again)
            n = DB.blob_star(str(body.get("id") or body.get("path") or ""), bool(body.get("on", True)))
            return self._json({"ok": bool(n)})
        if self.path == "/keychain":                                  # a secret into the login Keychain, from the welcome page
            name = str(body.get("service", ""))
            if (KC.has(name) or settings().get("welcomed")) and has_verifier() and not unlocked(body, self.headers):
                return self._json({"ok": False, "error": NEEDS_PIN}, 403)   # a kept secret (the PIN above all) is replaced only by the owner
            ok, err = keychain_set(name, str(body.get("value", "")))
            return self._json({"ok": ok, "error": err}, 200 if ok else 400)
        if self.path == "/pending-click":
            rid = f"{int(time.time())}-{len(PENDING) + 1}"
            file_request({"id": rid, "kind": "click", "src": body.get("src", ""), "why": body.get("why", ""), "action": body.get("action"), "at": time.time()})
            fslog(f"click requested {rid}: {body.get('src')} ({body.get('why')})")
            try:
                subprocess.Popen([str(HOME / "backtalk" / ".venv" / "bin" / "python"), str(HERE / "telegram.py"), "send",
                                  f"{AGENT} wants to click a risky control: {body.get('src')} ({body.get('why')}).\nReply 'approve' or 'reject'."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return self._json({"ok": True, "pending": rid, "done": "waiting for the owner's approval"})
        if self.path == "/app":
            op, name = body.get("op"), body.get("name", "")
            if op == "kill":                      # force-quit can lose unsaved work: the owner's approval, like the Trash
                rid = f"{int(time.time())}-{len(PENDING) + 1}"
                file_request({"id": rid, "kind": "kill", "src": name, "why": body.get("why", "force quit"), "at": time.time()})
                try:
                    subprocess.Popen([str(HOME / "backtalk" / ".venv" / "bin" / "python"), str(HERE / "telegram.py"), "send",
                                      f"{AGENT} wants to FORCE QUIT {name}: {body.get('why', '')}\nReply 'approve' or 'reject'."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return self._json({"ok": True, "pending": rid, "done": "waiting for the owner's approval"})
            if op in ("open", "focus", "quit"):
                return self._json(APPS.do(op, name))
            return self._json({"ok": False, "error": "unknown operation"}, 400)
        if self.path == "/browser":
            # the pane's clicks, keys, scrolling and navigation, queued for the bridge
            op = str(body.get("op", ""))
            if op not in ("click", "move", "scroll", "type", "key", "goto", "back", "forward", "reload", "newtab", "open"):
                return self._json({"ok": False, "error": "unknown browser op"}, 400)
            if op == "open":
                subprocess.Popen([str(HERE / "browser-mcp.sh"), "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._json({"ok": True, "done": "opening the browser"})
            cmd = {k: body[k] for k in ("op", "x", "y", "dy", "text", "key", "url", "count") if k in body}
            try:
                (P.CACHE).mkdir(exist_ok=True)
                with (P.CACHE / "browser-cmds.jsonl").open("a") as f:
                    f.write(json.dumps(cmd) + "\n")
            except OSError as e:
                return self._json({"ok": False, "error": str(e)})
            return self._json({"ok": True})
        if self.path == "/face-verify":
            d = face_verify()
            if d.get("ok"):
                tok = secrets.token_hex(16); UNLOCKS[tok] = time.time() + 15 * 60
                d.update({"token": tok, "until": int(UNLOCKS[tok])})
            return self._json(d)
        if self.path == "/look":
            what = body.get("what", "camera")
            script = HERE / ("look-screen.sh" if what == "screen" else "look.sh")
            try:
                r = subprocess.run([str(script)], capture_output=True, text=True, timeout=30)
                path = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""
                return self._json({"ok": bool(path), "path": path, "error": "" if path else (r.stderr.strip()[-200:] or "capture failed")})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)})
        if self.path == "/unlock":
            tok, err = try_unlock(body.get("pin", ""))
            return self._json({"ok": bool(tok), "token": tok or "", "until": int(UNLOCKS.get(tok, 0)) if tok else 0, "error": err})
        if self.path == "/pending-setting":
            rid = queue_setting(str(body.get("src", "a protected change")), str(body.get("why", "")), {"phrase": PROTECTED_PHRASES.get(str(body.get("phrase", "")), "")})
            return self._json({"ok": True, "pending": rid})
        if self.path == "/approve":
            # a yes is the owner's alone: an unlocked console (PIN or face), or the owner's own Telegram chat through the
            # bridge. A no is always welcome. Until something can verify the owner at all (a fresh install), the console's yes stands.
            by_owner = unlocked(body, self.headers) or (body.get("via") == "telegram" and from_telegram_bridge(self.client_address))
            if body.get("ok") and not by_owner and (has_verifier() or not origin):
                fslog("an approval without the owner's proof was refused")
                return self._json({"ok": False, "needs_unlock": True, "error": "approving needs you: unlock with your PIN (or your face), or approve on Telegram"}, 403)
            return self._json(fs_approve(body.get("id"), bool(body.get("ok"))))
        if self.path == "/ui":
            # the agent (or anything local) steering the page: view, vault, images, panel
            d = {k: body[k] for k in ("view", "vault", "images", "panel", "hint", "files", "focus", "gestures", "refresh", "apps", "modes", "routines", "tidy", "camera", "browser", "dim", "cues", "talk", "approvals", "reports", "go") if k in body}
            if not d:
                return self._json({"ok": False, "error": "nothing to do"}, 400)
            return self._json({"ok": True, "seq": ui_push(d)})
        if self.path == "/show":
            import subprocess
            p = body.get("path", "")
            if not allowed_image(p):
                return self._json({"ok": False, "error": "that file is not in a folder the board may show"}, 403)
            r = subprocess.run([str(HERE / "show-image.sh"), p, body.get("title") or Path(p).stem], capture_output=True, text=True, timeout=20)
            return self._json({"ok": r.returncode == 0, "error": "" if r.returncode == 0 else (r.stderr.strip() or "the hands board is not up")})
        if self.path == "/board":
            # put the vault's top-level folders on the hands board as cards
            import subprocess
            vault = HANDS.get("orbs", [{}])[0].get("path", "")
            board = HOME / "barehands" / "bin" / "board.sh"
            folders = sorted(d.name for d in Path(vault).iterdir() if d.is_dir() and not d.name.startswith("."))[:10] if vault else []
            n = 0
            if body.get("clear"):
                r = subprocess.run([str(board), json.dumps({"a": "reset"})], capture_output=True, text=True, timeout=10)
                return self._json({"ok": r.returncode == 0, "cards": 0, "error": "" if r.returncode == 0 else "the hands board is not up"})
            for i, name in enumerate(folders):
                idx = f"0/{name}/{name.split(' - ', 1)[-1]}.md"
                x = 0.45 + (i % 4) * 0.14; y = 0.25 + (i // 4) * 0.28
                cmd = json.dumps({"a": "add_card", "title": name.split(" - ", 1)[-1].upper(), "body": "tap to open",
                                  "file": idx, "x": round(x, 2), "y": round(y, 2)})
                r = subprocess.run([str(board), cmd], capture_output=True, text=True, timeout=10)
                n += r.returncode == 0
            return self._json({"ok": n > 0, "cards": n, "error": "" if n else "the hands board is not up"})
        if self.path == "/settings":
            cur = settings()
            prot = protected_changes(body, cur)
            if prot and guard_on() and has_verifier() and not unlocked(body, self.headers) and not (body.get("via") == "telegram" and from_telegram_bridge(self.client_address)):
                rid = queue_setting(", ".join(prot), "protected setting; not from an unlocked console", {"settings": {k: v for k, v in body.items() if k != "unlock"}})
                return self._json({"ok": True, "pending": rid, "protected": prot, "done": "waiting for the owner: approve on Telegram, or unlock the console with the PIN and try again", **cur})
            cur = apply_settings(body, cur)
            try:
                SETTINGS.write_text(json.dumps(cur, indent=2), encoding="utf-8")
            except OSError as e:
                return self._json({"ok": False, "error": str(e)}, 500)
            return self._json({"ok": True, **cur})
        if unlocked(body, self.headers):
            text = "(verified) " + str(text)
        if body.get("when") == "idle":
            say_when_idle(str(text)); return self._json({"ok": True, "error": ""})
        ok, err = say(str(text))
        self._json({"ok": ok, "error": err}, 200 if ok else 409)


class Server(ThreadingHTTPServer):
    """The agent's server. "lan" (Modes, protected): false answers on this Mac only; "tailscale" answers this Mac and the
    owner's own devices over Tailscale, and turns every other network away before a byte is read; true answers the network."""
    only_tailnet = False

    def verify_request(self, request, client_address):
        return not self.only_tailnet or from_tailnet(client_address[0])


if __name__ == "__main__":
    restore_requests()
    reach = settings().get("lan"); via_serve = False
    try:
        srv = Server(("0.0.0.0" if reach else "127.0.0.1", PORT), Handler)
    except OSError as e:
        if not (reach and e.errno == 48 and _serve_holds(PORT)):
            raise
        srv = Server(("127.0.0.1", PORT), Handler); via_serve = True         # Tailscale's https listener has the tailnet side of the port: it carries the phone
    srv.only_tailnet = reach == "tailscale" and not via_serve
    print(f"the agent's server (API) on http://127.0.0.1:{PORT}/" + (" and over Tailscale's https" if via_serve else " and over Tailscale" if srv.only_tailnet else " and on this network" if reach else ""), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
