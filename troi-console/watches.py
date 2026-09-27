#!/usr/bin/env python3
"""Watches: "watch this, and when it happens, do that" (Silo One, 2026-09-27). The pulse notices; the agent acts.

A watch is a trigger and an instruction in the owner's words. The pulse evaluates every watch on its tick; when one fires,
the instruction reaches the agent through the voice line as a line of context ("(watch … fired: … The owner asked: …)"),
and the agent does the thing under all its usual rules: nothing is deleted, anything risky is filed for the owner's
approval, the guard stands. This file never runs a command of its own. A watch can also just tell (--tell): one sentence
to the owner, no action.

  watches.py add time "every monday at 8am" "prepare my weekly briefing"
  watches.py add time "in 40 minutes" "check the deploy"                        a one-shot: fires once, then turns itself off
  watches.py add folder ~/Downloads --glob "*.pdf" "file the invoice under Finance/2026"
  watches.py add file ~/Projects/x/build.log "read the tail and tell me if it failed"
  watches.py add process Docker --when stops "tell me"                          starts | stops | both; --cpu 90 for a hog
  watches.py add url https://example.com/pricing --every 15m "tell me what changed"
  watches.py add disk --below 10 "warn me and say what is taking the space"     GB free, on / unless --path
  watches.py add power --on battery "turn the planet to saver"                  battery | ac | both
  watches.py add battery --below 20 "remind me to plug in"
  watches.py add app Spotify --when opens "turn the sounds off"                 opens | quits | both
  watches.py add wifi "say which network we are on"
  watches.py add device AirPods --when connects "route the sound to them"     a Bluetooth device coming or going (once a minute)
  watches.py list | on <id> | off <id> | test <id> | when "<phrase>"

The schedule words: every N minutes|hours · every hour · every day|morning|evening|night|afternoon|noon [at HH:MM|8am|8:30pm]
· every monday|weekday|weekend [morning|at …] · every 1st|15th [at …] · in 20 minutes · at 8am tomorrow · on friday at 5pm.

Caution, built in: a watch never runs anything itself; each has a cooldown (60 s, url watches their --every) and a daily cap
(30 fires; past it the watch goes quiet until midnight and says so once); a watch is turned off, never deleted; a one-shot
turns itself off after it fires. Stdlib only. The document is "watches" in data/troi.db; the pulse's own state keeps
what each watch has seen.
"""
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _DB  # noqa: E402

DOC = _DB.doc("watches")
KINDS = ("time", "folder", "file", "process", "url", "disk", "power", "battery", "app", "wifi", "device")
DEFAULT_GAP = 60            # seconds between two fires of one watch
DAILY_CAP = 30              # fires a day, then quiet until midnight
PENDING_GRACE = 1800        # a fire that waited for the agent to be free is dropped after this long

# ---- the document
def load():
    try:
        items = json.loads(DOC.read_text())
    except Exception:
        items = []
    return items if isinstance(items, list) else []


def save(items):
    DOC.write_text(json.dumps(items, indent=2))


def new_id(items):
    n = 1 + max([int(str(w.get("id", "w0"))[1:] or 0) for w in items if str(w.get("id", "")).startswith("w") and str(w.get("id", ""))[1:].isdigit()] + [0])
    return f"w{n}"


# ---- the schedule words -> {"every": s} | {"at": "HH:MM", "days": [...], "dom": n} | {"once": epoch}
WORDS_TIME = {"morning": "08:00", "evening": "18:00", "night": "21:00", "afternoon": "14:00", "noon": "12:00", "midday": "12:00",
              "lunch": "13:00", "midnight": "00:00", "dawn": "06:00"}
DAYS = {"monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
        "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6}


def _clock(s):
    """'8am' '8 am' '8:30pm' '08:00' '20h' 'noon' -> 'HH:MM' or None."""
    s = s.strip().lower()
    if s in WORDS_TIME:
        return WORDS_TIME[s]
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|h)?", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return f"{h:02d}:{mi:02d}"


def parse_when(text):
    """The schedule words to a spec, or None when the words make no schedule."""
    t = " ".join(str(text).lower().replace(",", " ").split())
    t = re.sub(r"\b(o'clock|oclock)\b", "", t).strip()
    # every N minutes / hours
    m = re.fullmatch(r"every\s+(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?)", t)
    if m:
        n = int(m.group(1)); unit = m.group(2)
        return {"every": max(60, n * (60 if unit.startswith("m") else 3600))}
    if t in ("every hour", "hourly", "each hour"):
        return {"every": 3600}
    if t in ("every minute",):
        return {"every": 60}
    # in N minutes / hours -> once
    m = re.fullmatch(r"in\s+(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?)", t)
    if m:
        n = int(m.group(1)); unit = m.group(2)
        return {"once": time.time() + n * (60 if unit.startswith("m") else 3600)}
    # the time words anywhere in the phrase
    at = None
    m = re.search(r"\bat\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm|h)?|noon|midday|midnight)\b", t)
    if m:
        at = _clock(m.group(1)); t = (t[:m.start()] + t[m.end():]).strip()
    for w, hhmm in WORDS_TIME.items():
        if re.search(rf"\b{w}\b", t):
            at = at or hhmm; t = re.sub(rf"\b{w}\b", "", t).strip()
    t = " ".join(t.split())
    # a one-shot: tomorrow / on <day> / today
    if t.startswith(("tomorrow", "at tomorrow")) or t.endswith("tomorrow") or t == "tomorrow":
        d = datetime.now().date() + timedelta(days=1); hh, mm = map(int, (at or "08:00").split(":"))
        return {"once": datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm).timestamp()}
    m = re.fullmatch(r"(?:on\s+|this\s+|next\s+)?([a-z]+)", t)
    if m and m.group(1) in DAYS and not t.startswith("every"):
        want = DAYS[m.group(1)]; d = datetime.now().date()
        for _ in range(8):
            d += timedelta(days=1)
            if d.weekday() == want:
                break
        hh, mm = map(int, (at or "08:00").split(":"))
        return {"once": datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm).timestamp()}
    if t in ("today", "later today") and at:
        d = datetime.now(); hh, mm = map(int, at.split(":")); when = d.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if when < d:
            when += timedelta(days=1)
        return {"once": when.timestamp()}
    # recurring: every day / weekday / weekend / <days> / 1st of the month
    if not t.startswith("every") and not t.startswith("each") and not t.startswith("daily") and not t.startswith("weekly"):
        if at and not t:
            return {"at": at, "days": None, "dom": None}     # a bare time: every day at that time
        return None
    body = re.sub(r"^(every|each|daily|weekly)\s*", "", t).strip()
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?(?:\s+(?:day\s+)?of\s+(?:the\s+|every\s+|each\s+)?month)?", body)
    if m and 1 <= int(m.group(1)) <= 31:
        return {"at": at or "08:00", "days": None, "dom": int(m.group(1))}
    days = None
    if body in ("", "day", "days"):
        days = None
    elif body in ("weekday", "weekdays", "working day", "work day", "workday"):
        days = [0, 1, 2, 3, 4]
    elif body in ("weekend", "weekends"):
        days = [5, 6]
    else:
        found = [DAYS[w.rstrip("s")] for w in re.split(r"\s+|and|&|/", body) if w and w.rstrip("s") in DAYS]
        if not found or any(w and w.rstrip("s") not in DAYS and w not in ("and", "&", "on") for w in re.split(r"\s+|/", body)):
            return None
        days = sorted(set(found))
    return {"at": at or "08:00", "days": days, "dom": None}


def describe_when(spec):
    if spec.get("once"):
        return "once, " + datetime.fromtimestamp(spec["once"]).strftime("%a %d %b %H:%M")
    if spec.get("every"):
        s = spec["every"]; return "every " + (f"{s // 3600} h" if s % 3600 == 0 else f"{s // 60} min")
    days = spec.get("days"); dom = spec.get("dom")
    when = f"at {spec.get('at', '08:00')}"
    if dom:
        return f"the {dom}{'st' if dom in (1, 21, 31) else 'nd' if dom in (2, 22) else 'rd' if dom in (3, 23) else 'th'} of every month {when}"
    if days is None:
        return "every day " + when
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if days == [0, 1, 2, 3, 4]:
        return "weekdays " + when
    if days == [5, 6]:
        return "weekends " + when
    return "every " + ", ".join(names[d] for d in days) + " " + when


# ---- the triggers: each returns (fired: bool, details: str); `seen` is this watch's memory in the pulse's state
def _time_due(spec, seen, now):
    if spec.get("once"):
        return (now >= spec["once"], "the time came")
    if spec.get("every"):
        last = seen.get("last", 0)
        if not last:
            seen["last"] = now; return (False, "")               # the first pass sets the clock
        if now - last < spec["every"]:
            return (False, "")
        seen["last"] = now
        return (True, "the interval passed")
    d = datetime.fromtimestamp(now); key = d.strftime("%Y-%m-%d %H:%M")
    if d.strftime("%H:%M") != spec.get("at", "08:00") or seen.get("minute") == key:
        return (False, "")
    if spec.get("dom") and d.day != spec["dom"]:
        return (False, "")
    if spec.get("days") is not None and d.weekday() not in spec["days"]:
        return (False, "")
    seen["minute"] = key
    return (True, "the time came")


def _listing(path, glob):
    out = {}
    try:
        for e in os.scandir(path):
            if e.name.startswith(".") or not e.is_file():
                continue
            if glob and not fnmatch.fnmatch(e.name, glob):
                continue
            out[e.name] = int(e.stat().st_mtime)
    except OSError:
        return None
    return out


FOLDER_SETTLE = 8           # seconds a folder watch waits after the first new file, so a burst of downloads is one line, not twenty


def _folder(spec, seen, now):
    cur = _listing(os.path.expanduser(spec.get("path", "")), spec.get("glob"))
    if cur is None:
        return (False, "")
    prev = seen.get("files")
    seen["files"] = cur
    if prev is None:
        return (False, "")                                        # the first pass is the baseline
    new = sorted(n for n in cur if n not in prev)
    if new:
        held = seen.setdefault("held", [])
        held.extend(n for n in new if n not in held); seen.setdefault("held_at", now)
    held = seen.get("held") or []
    if not held or now - seen.get("held_at", now) < FOLDER_SETTLE:
        return (False, "")
    seen.pop("held", None); seen.pop("held_at", None)
    shown = ", ".join(held[:5]) + (f" and {len(held) - 5} more" if len(held) > 5 else "")
    return (True, f"new in {spec.get('path')}: {shown}")


def _file(spec, seen):
    p = os.path.expanduser(spec.get("path", ""))
    try:
        mt = int(os.stat(p).st_mtime)
    except OSError:
        if seen.get("mtime") is not None and not seen.get("gone"):
            seen["gone"] = True; return (True, f"{spec.get('path')} is gone")
        return (False, "")
    seen.pop("gone", None)
    prev = seen.get("mtime"); seen["mtime"] = mt
    if prev is None or prev == mt:
        return (False, "")
    return (True, f"{spec.get('path')} changed at {datetime.fromtimestamp(mt):%H:%M:%S}")


def _ps():
    try:
        out = subprocess.run(["ps", "-axo", "pid=,%cpu=,comm="], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            try:
                rows.append((int(parts[0]), float(parts[1]), parts[2]))
            except ValueError:
                pass
    return rows


def _process(spec, seen):
    name = str(spec.get("name", "")).lower(); when = spec.get("when", "both"); cpu = spec.get("cpu")
    rows = [r for r in _ps() if name and name in r[2].lower()]
    running = bool(rows)
    prev = seen.get("running")
    seen["running"] = running
    if cpu and rows:
        top = max(r[1] for r in rows)
        if top >= float(cpu):
            return (True, f"{spec.get('name')} is at {top:.0f}% CPU")
    if prev is None:
        return (False, "")
    if running and not prev and when in ("starts", "both"):
        return (True, f"{spec.get('name')} started")
    if prev and not running and when in ("stops", "both"):
        return (True, f"{spec.get('name')} stopped")
    return (False, "")


def _apps_open():
    rows = _ps()
    names = set()
    for _, _, comm in rows:
        m = re.search(r"/([^/]+)\.app/Contents/MacOS/", comm)
        if m:
            names.add(m.group(1).lower())
    return names


def _app(spec, seen):
    name = str(spec.get("name", "")).lower(); when = spec.get("when", "both")
    open_ = name in _apps_open()
    prev = seen.get("open"); seen["open"] = open_
    if prev is None:
        return (False, "")
    if open_ and not prev and when in ("opens", "both"):
        return (True, f"{spec.get('name')} opened")
    if prev and not open_ and when in ("quits", "both"):
        return (True, f"{spec.get('name')} quit")
    return (False, "")


def _url(spec, seen, now):
    every = int(spec.get("every") or 900)
    if now - seen.get("checked", 0) < every:
        return (False, "")
    seen["checked"] = now
    url = str(spec.get("url", ""))
    if not url.lower().startswith("https://"):
        return (False, "")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) Troi watch"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(2_000_000).decode("utf-8", "replace")
    except Exception as e:
        err = str(e)[:80]
        if seen.get("err") != err:
            seen["err"] = err
        return (False, "")
    seen.pop("err", None)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text); text = " ".join(text.split())
    digest = hashlib.sha1(text.encode()).hexdigest()
    prev = seen.get("hash"); seen["hash"] = digest; seen["size"] = len(text)
    if prev is None or prev == digest:
        return (False, "")
    return (True, f"{url} changed ({len(text)} characters of text now)")


def _disk(spec, seen, now):
    path = os.path.expanduser(spec.get("path") or "/")
    try:
        free_gb = shutil.disk_usage(path).free / 1e9
    except OSError:
        return (False, "")
    below = float(spec.get("below_gb") or 10)
    low = free_gb < below
    if low and now - seen.get("told", 0) > 6 * 3600:
        seen["told"] = now; return (True, f"{free_gb:.1f} GB free on {path}, under {below:g} GB")
    if not low:
        seen.pop("told", None)
    return (False, "")


def _pmset():
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None, None
    src = "battery" if "Battery Power" in out else "ac" if "AC Power" in out else None
    m = re.search(r"(\d{1,3})%", out)
    return src, (int(m.group(1)) if m else None)


def _power(spec, seen):
    src, _ = _pmset()
    if src is None:
        return (False, "")
    prev = seen.get("src"); seen["src"] = src
    if prev is None or prev == src:
        return (False, "")
    want = spec.get("on", "both")
    if want == "both" or want == src:
        return (True, "on battery now" if src == "battery" else "plugged in now")
    return (False, "")


def _battery(spec, seen):
    src, pct = _pmset()
    if pct is None:
        return (False, "")
    below = int(spec.get("below") or 20); low = pct < below and src == "battery"
    prev = seen.get("low"); seen["low"] = low
    if low and not prev:
        return (True, f"battery at {pct}%, under {below}%")
    return (False, "")


def _wifi(spec, seen):
    try:
        out = subprocess.run(["networksetup", "-getairportnetwork", spec.get("iface") or "en0"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return (False, "")
    m = re.search(r"Network:\s*(.+)$", out.strip())
    ssid = m.group(1).strip() if m else ("off" if "not associated" in out.lower() or "off" in out.lower() else "")
    if not ssid:
        return (False, "")
    prev = seen.get("ssid"); seen["ssid"] = ssid
    if prev is None or prev == ssid:
        return (False, "")
    return (True, f"the Wi-Fi is {ssid} now (was {prev})")


def _device(spec, seen, now):
    """A Bluetooth device coming or going (system_profiler, asked once a minute at most)."""
    if now - seen.get("checked", 0) < 60:
        return (False, "")
    seen["checked"] = now
    try:
        out = subprocess.run(["system_profiler", "SPBluetoothDataType", "-json"], capture_output=True, text=True, timeout=30).stdout
        d = (json.loads(out).get("SPBluetoothDataType") or [{}])[0]
        names = {n.lower() for e in (d.get("device_connected") or []) for n in (e.keys() if isinstance(e, dict) else [])}
    except Exception:
        return (False, "")
    want = str(spec.get("name", "")).lower(); when = spec.get("when", "both")
    here = any(want in n for n in names)
    prev = seen.get("here"); seen["here"] = here
    if prev is None:
        return (False, "")
    if here and not prev and when in ("connects", "both"):
        return (True, f"{spec.get('name')} connected")
    if prev and not here and when in ("disconnects", "both"):
        return (True, f"{spec.get('name')} disconnected")
    return (False, "")


def evaluate(w, seen, now):
    k = w.get("kind"); spec = w.get("spec") or {}
    if k == "device":
        return _device(spec, seen, now)
    if k == "time":
        return _time_due(spec, seen, now)
    if k == "folder":
        return _folder(spec, seen, now)
    if k == "file":
        return _file(spec, seen)
    if k == "process":
        return _process(spec, seen)
    if k == "app":
        return _app(spec, seen)
    if k == "url":
        return _url(spec, seen, now)
    if k == "disk":
        return _disk(spec, seen, now)
    if k == "power":
        return _power(spec, seen)
    if k == "battery":
        return _battery(spec, seen)
    if k == "wifi":
        return _wifi(spec, seen)
    return (False, "")


# ---- the pulse's call: every tick
def line_for(w, details):
    note, do = w.get("note") or w.get("kind"), (w.get("do") or "").strip()
    if w.get("mode") == "tell" or not do:
        return (f"(watch \"{note}\": {details}. Tell the owner in one sentence.)", f"Watch, {note}: {details}")
    return (f"(watch \"{note}\" fired: {details}. The owner asked that when this happens you: \"{do}\". Do exactly that now, under your usual rules: "
            f"nothing is deleted, anything risky is filed for their approval, and say in one line what you did.)",
            f"Watch, {note}: {details}. You asked: \"{do}\". The voice line is down, so nothing was done; say the word when you are back.")


def check(state, tell, log, busy):
    """Evaluate every watch that is on; fire what is due (or hold it while the agent is busy, up to half an hour)."""
    items = load()
    if not items:
        return
    now = time.time(); today = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
    mem = state.setdefault("watch_seen", {}); pending = state.setdefault("watch_pending", [])
    changed = False
    for w in items:
        wid = str(w.get("id"))
        if not w.get("on", True):
            continue
        seen = mem.setdefault(wid, {})
        try:
            fired, details = evaluate(w, seen, now)
        except Exception as e:
            log(f"[pulse]  watch {wid} failed: {e!r}"); continue
        if not fired:
            continue
        # the cooldown holds what repeats (a time, a page, the disk, a file being written, the battery); a transition (a new file, a
        # process or an app coming or going, the power, the Wi-Fi) is never swallowed, the daily cap is its brake
        gapped = w.get("gap") is not None or w.get("kind") in ("time", "url", "disk", "file", "battery")
        if gapped and now - float(w.get("last") or 0) < int(w.get("gap") or DEFAULT_GAP):
            continue
        if w.get("day") != today:
            w["day"] = today; w["today"] = 0
        if int(w.get("today") or 0) >= int(w.get("cap") or DAILY_CAP):
            if not w.get("capped"):
                w["capped"] = True; changed = True
                log(f"[pulse]  watch {wid} capped for today")
                tell(f"(watch \"{w.get('note') or w.get('kind')}\" fired {w.get('today')} times today and is quiet until midnight. Tell the owner in one sentence.)",
                     phone=f"Watch, {w.get('note')}: quiet until midnight after {w.get('today')} fires today.")
            continue
        w["last"] = now; w["today"] = int(w.get("today") or 0) + 1; w["fires"] = int(w.get("fires") or 0) + 1; w.pop("capped", None); changed = True
        if w.get("kind") == "time" and (w.get("spec") or {}).get("once"):
            w["on"] = False                                          # a one-shot has done its work
        log(f"[pulse]  watch {wid} ({w.get('note')}): {details}")
        pending.append({"id": wid, "details": details, "at": now})
    if changed:
        save(items)
    # fire what is pending, when the agent is free; drop what waited too long
    if pending:
        keep = []
        for p in pending:
            if now - p["at"] > PENDING_GRACE:
                log(f"[pulse]  watch {p['id']}: dropped, the agent stayed busy for half an hour"); continue
            if busy():
                keep.append(p); continue
            w = next((x for x in items if str(x.get("id")) == p["id"]), None)
            if not w:
                continue
            line, phone = line_for(w, p["details"])
            try:
                tell(line, phone=phone, level=w.get("level") or ("action"))      # the pulse's channel sorts it (triage.py); --fyi keeps it for the digest
            except TypeError:
                tell(line, phone=phone)
        state["watch_pending"] = keep


# ---- the command line
def _opt(a, name, default=None):
    if name in a:
        i = a.index(name); v = a[i + 1] if i + 1 < len(a) else default
        del a[i:i + 2]; return v
    return default


def _flag(a, name):
    if name in a:
        a.remove(name); return True
    return False


def _every(s):
    m = re.fullmatch(r"(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?|s|sec|secs|seconds?)?", str(s).strip())
    if not m:
        return 900
    n = int(m.group(1)); u = m.group(2) or "m"
    return max(60, n * (3600 if u.startswith("h") else 1 if u.startswith("s") else 60))


def cmd_add(a):
    a = list(a)
    tell_only = _flag(a, "--tell"); fyi = _flag(a, "--fyi"); urgent = _flag(a, "--urgent")
    gap = _opt(a, "--gap"); cap = _opt(a, "--cap")
    if not a or a[0] not in KINDS:
        print("usage: watches.py add <" + "|".join(KINDS) + "> … \"<what to do>\"   (watches.py --help for the shapes)"); return 2
    kind = a.pop(0); spec = {}; note = ""
    if kind == "time":
        if len(a) < 2:
            print('usage: watches.py add time "<when>" "<what to do>"'); return 2
        spec = parse_when(a[0])
        if not spec:
            print(f"I cannot read \"{a[0]}\" as a schedule. Try: every monday at 8am · every day at 18:00 · every 30 minutes · in 20 minutes · at 9am tomorrow"); return 2
        note = describe_when(spec); do = " ".join(a[1:])
    elif kind == "folder":
        glob = _opt(a, "--glob")
        if len(a) < 2:
            print('usage: watches.py add folder <path> [--glob "*.pdf"] "<what to do>"'); return 2
        p = os.path.expanduser(a[0])
        if not os.path.isdir(p):
            print(f"no such folder: {a[0]}"); return 2
        spec = {"path": a[0], "glob": glob}; note = f"new files in {a[0]}" + (f" ({glob})" if glob else ""); do = " ".join(a[1:])
    elif kind == "file":
        if len(a) < 2:
            print('usage: watches.py add file <path> "<what to do>"'); return 2
        spec = {"path": a[0]}; note = f"changes to {a[0]}"; do = " ".join(a[1:])
    elif kind == "process":
        when = _opt(a, "--when", "both"); cpu = _opt(a, "--cpu")
        if len(a) < 2:
            print('usage: watches.py add process <name> [--when starts|stops|both] [--cpu 90] "<what to do>"'); return 2
        spec = {"name": a[0], "when": when if when in ("starts", "stops", "both") else "both", "cpu": float(cpu) if cpu else None}
        note = f"{a[0]} {when}" + (f", or over {cpu}% CPU" if cpu else ""); do = " ".join(a[1:])
    elif kind == "app":
        when = _opt(a, "--when", "both")
        if len(a) < 2:
            print('usage: watches.py add app <name> [--when opens|quits|both] "<what to do>"'); return 2
        spec = {"name": a[0], "when": when if when in ("opens", "quits", "both") else "both"}; note = f"{a[0]} {when}"; do = " ".join(a[1:])
    elif kind == "url":
        every = _every(_opt(a, "--every", "15m"))
        if len(a) < 2 or not a[0].lower().startswith("https://"):
            print('usage: watches.py add url https://… [--every 15m] "<what to do>"   (https only)'); return 2
        spec = {"url": a[0], "every": every}; note = f"changes at {a[0]}"; do = " ".join(a[1:]); gap = gap or every
    elif kind == "disk":
        path = _opt(a, "--path", "/"); below = _opt(a, "--below", "10")
        if not a:
            print('usage: watches.py add disk [--path /] --below 10 "<what to do>"'); return 2
        spec = {"path": path, "below_gb": float(below)}; note = f"disk under {below} GB free on {path}"; do = " ".join(a)
    elif kind == "power":
        on = _opt(a, "--on", "both")
        if not a:
            print('usage: watches.py add power [--on battery|ac|both] "<what to do>"'); return 2
        spec = {"on": on if on in ("battery", "ac", "both") else "both"}; note = "power: " + ("battery or the cord" if spec["on"] == "both" else spec["on"]); do = " ".join(a)
    elif kind == "battery":
        below = _opt(a, "--below", "20")
        if not a:
            print('usage: watches.py add battery --below 20 "<what to do>"'); return 2
        spec = {"below": int(below)}; note = f"battery under {below}%"; do = " ".join(a)
    elif kind == "device":
        when = _opt(a, "--when", "both")
        if len(a) < 2:
            print('usage: watches.py add device <name> [--when connects|disconnects|both] "<what to do>"'); return 2
        spec = {"name": a[0], "when": when if when in ("connects", "disconnects", "both") else "both"}; note = f"{a[0]} {when} (Bluetooth)"; do = " ".join(a[1:])
    else:  # wifi
        if not a:
            print('usage: watches.py add wifi "<what to do>"'); return 2
        spec = {"iface": _opt(a, "--iface", "en0")}; note = "the Wi-Fi network changes"; do = " ".join(a)
    items = load(); wid = new_id(items)
    w = {"id": wid, "kind": kind, "spec": spec, "do": do.strip(), "mode": "tell" if tell_only else "ask", "note": note, "on": True, "created": time.time(), "fires": 0}
    if gap:
        w["gap"] = int(_every(gap)) if not str(gap).isdigit() else int(gap)
    if cap:
        w["cap"] = int(cap)
    if fyi:
        w["level"] = "fyi"                                          # kept for the digest, never spoken
    elif urgent:
        w["level"] = "urgent"                                       # spoken at once and phoned, quiet hours or not
    items.append(w); save(items)
    print(f"watch {wid}: {note} -> {'tell the owner' if tell_only else do.strip()}   (watches.py off {wid} turns it off)")
    return 0


def cmd_list():
    items = load()
    if not items:
        print("no watches. watches.py --help shows the shapes."); return 0
    for w in items:
        on = "on " if w.get("on", True) else "off"
        last = datetime.fromtimestamp(w["last"]).strftime("%a %H:%M") if w.get("last") else "never"
        print(f"{w['id']:<5} {on} {w.get('kind'):<8} {w.get('note', '')}  ->  {w.get('do') or 'tell the owner'}   [fired {w.get('fires', 0)}, last {last}]")
    return 0


def cmd_switch(wid, on):
    items = load()
    for w in items:
        if str(w.get("id")) == wid:
            w["on"] = on; save(items); print(f"watch {wid} {'on' if on else 'off (kept)'}: {w.get('note')}"); return 0
    print(f"no watch {wid}"); return 1


def cmd_test(wid):
    items = load(); w = next((x for x in items if str(x.get("id")) == wid), None)
    if not w:
        print(f"no watch {wid}"); return 1
    seen = {}
    fired, details = evaluate(w, seen, time.time())
    print(f"{wid} {w.get('kind')}: {'would fire' if fired else 'quiet'}" + (f": {details}" if details else "") + f"   (a first look is a baseline for folder, file, process, app, url, power and wifi)")
    line, _ = line_for(w, details or "(details)")
    print("the line to the agent: " + line)
    return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "add":
        return cmd_add(a[1:])
    if a[0] == "list":
        return cmd_list()
    if a[0] in ("on", "off") and len(a) > 1:
        return cmd_switch(a[1], a[0] == "on")
    if a[0] == "test" and len(a) > 1:
        return cmd_test(a[1])
    if a[0] == "when" and len(a) > 1:
        spec = parse_when(" ".join(a[1:]))
        print(json.dumps(spec) + ("  ->  " + describe_when(spec) if spec else "  (not a schedule I can read)")); return 0 if spec else 2
    print(__doc__.strip().splitlines()[0]); print("watches.py add|list|on|off|test|when   (--help for the shapes)"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
