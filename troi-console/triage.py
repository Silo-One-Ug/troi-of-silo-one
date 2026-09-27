#!/usr/bin/env python3
"""Notification triage (Silo One, 2026-09-27): what the pulse has to say is sorted before it is said.

Four levels, and a channel for each:
  urgent    spoken as soon as the agent is free, and always to the phone; crosses quiet hours
  action    spoken when the agent is free (to the phone when the voice line is down); held for the digest in quiet hours
  fyi       never spoken: kept for the digest ("what did I miss")
  ignore    logged, nothing more

Quiet: the owner's word ("don't disturb me for two hours unless it's urgent" -> triage.py quiet on 2h), a meeting being
recorded (meeting.py), an event in progress on the calendar (checked every five minutes), or the night (23:00 to 07:00,
console.json "quiet_night": false to switch it off). In quiet only the urgent is spoken; the rest waits.

  triage.py digest [--since 8h]      what was said and what was held, by level, newest first
  triage.py quiet on [2h] | off | status
  triage.py level <kind> "<text>"    what level a line would get (the rules, for a look)

The log of it is the "triage" document in data/troi.db (the last 500 items). Stdlib only.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _DB  # noqa: E402
import paths as P  # noqa: E402

DOC = _DB.doc("triage")
QUIET = _DB.doc("triage-quiet")
LEVELS = ("urgent", "action", "fyi", "ignore")
KEEP = 500
HERE = Path(__file__).resolve().parent
_tell = None
_log = None

URGENT_WORDS = re.compile(r"\b(down|unreachable|not answering|no route|disk (is )?full|out of (disk|memory|space)|critical|crashed|data loss|production is|prod is|ransom|breach|refused every)\b", re.I)


def bind(tell, log):
    """The pulse hands over its channel to the agent and its log."""
    global _tell, _log
    _tell, _log = tell, log


# ---- the rules: a kind and a line -> a level
def classify(kind, text, level=None):
    if level in LEVELS:
        return level
    t = text or ""
    if kind == "reminder":
        return "action"
    if kind == "github":
        return "action" if "FAILED" in t else "fyi"                  # green again is good news, not a task
    if kind == "servers":
        if URGENT_WORDS.search(t):
            return "urgent"
        return "action" if "NEW:" in t and "NEW: none" not in t else "fyi"
    if kind == "grafana":
        if re.search(r"\b(critical|page|sev ?1|P1)\b", t, re.I) or URGENT_WORDS.search(t):
            return "urgent"
        return "action" if re.search(r"\bfiring\b|\bbegan\b", t, re.I) else "fyi"
    if kind == "calendar":
        return "action"
    if kind == "watch":
        return "action"
    if kind in ("brief", "report", "nightly"):
        return "action"
    return "action"


# ---- quiet
def quiet_status():
    """(quiet: bool, why: str)."""
    try:
        q = json.loads(QUIET.read_text())
    except Exception:
        q = {}
    until = float(q.get("until") or 0)
    if until and time.time() < until:
        return True, f"your word, until {datetime.fromtimestamp(until):%H:%M}"
    if until and time.time() >= until and q.get("until"):
        try:
            QUIET.write_text(json.dumps({}))
        except Exception:
            pass
    try:
        rec = P.DATA / "blobs" / "meetings" / ".recording.json"
        if rec.exists() and time.time() - rec.stat().st_mtime < 6 * 3600:
            return True, "a meeting is being recorded"
    except Exception:
        pass
    try:
        if _DB.doc("movie").exists():                                # media.py movie on leaves this while the film runs
            return True, "movie mode"
    except Exception:
        pass
    try:
        cfg = json.loads(P.CONFIG.read_text())
    except Exception:
        cfg = {}
    if cfg.get("quiet_night", True):
        h = datetime.now().hour
        if h >= 23 or h < 7:
            return True, "the night"
    return False, ""


_cal = {"at": 0.0, "busy": False}


def in_event():
    """An event in progress on the calendar, asked every five minutes at most."""
    if time.time() - _cal["at"] < 300:
        return _cal["busy"]
    _cal["at"] = time.time()
    try:
        r = subprocess.run([sys.executable, str(HERE / "agenda.py"), "current"], capture_output=True, text=True, timeout=40)
        d = json.loads(r.stdout or "{}")
        _cal["busy"] = bool(d and d.get("title"))
    except Exception:
        _cal["busy"] = False
    return _cal["busy"]


def is_quiet():
    q, why = quiet_status()
    if q:
        return True, why
    if in_event():
        return True, "an event is on"
    return False, ""


# ---- the record of it
def load():
    try:
        d = json.loads(DOC.read_text())
        return d if isinstance(d, list) else []
    except Exception:
        return []


def note(kind, level, text, how):
    items = load()
    items.append({"t": time.time(), "kind": kind, "level": level, "text": (text or "")[:300], "how": how})
    del items[:-KEEP]
    try:
        DOC.write_text(json.dumps(items))
    except Exception:
        pass


# ---- the channel
def deliver(state, kind, line, phone=None, level=None):
    """Sort, then say, phone, hold or drop. `line` is the agent's context; `phone` the Telegram wording (the digest keeps the phone
    wording when there is one, since it is the plain one)."""
    lvl = classify(kind, phone or line, level)
    plain = phone if isinstance(phone, str) and phone not in ("always",) else re.sub(r"^\(|\)$", "", line or "")[:300]
    quiet, why = is_quiet()
    if lvl == "ignore":
        note(kind, lvl, plain, "dropped")
        if _log: _log(f"[pulse]  triage: ignored {kind}: {plain[:100]}")
        return "ignore"
    if lvl == "fyi":
        note(kind, lvl, plain, "digest")
        if _log: _log(f"[pulse]  triage: fyi {kind}: {plain[:100]}")
        return "fyi"
    if lvl == "action" and quiet:
        note(kind, lvl, plain, f"held ({why})")
        if _log: _log(f"[pulse]  triage: held {kind} ({why}): {plain[:100]}")
        return "held"
    if lvl == "urgent":
        ok = _tell(line, phone="always") if _tell else False
        if ok and phone and phone != "always":                        # the voice line took it; the phone hears it too
            try:
                subprocess.run([sys.executable, str(HERE / "telegram.py"), "send", "URGENT: " + phone], timeout=30, capture_output=True)
            except Exception:
                pass
        note(kind, lvl, plain, "spoken and phoned" if ok else "phoned")
        return "urgent"
    ok = _tell(line, phone=phone) if _tell else False
    note(kind, lvl, plain, "spoken" if ok else ("phoned" if phone else "lost, the voice line is down"))
    return "action"


# ---- the command line
def cmd_digest(a):
    since = 8 * 3600
    if "--since" in a:
        i = a.index("--since"); v = a[i + 1]
        m = re.fullmatch(r"(\d+)\s*(h|m|d)?", v.strip())
        if m:
            n = int(m.group(1)); u = m.group(2) or "h"; since = n * {"m": 60, "h": 3600, "d": 86400}[u]
    items = [x for x in load() if time.time() - x.get("t", 0) <= since]
    if not items:
        print(f"nothing in the last {since // 3600 if since >= 3600 else since // 60}{'h' if since >= 3600 else 'm'}"); return 0
    q, why = is_quiet()
    print(f"the last {since // 3600 if since >= 3600 else since // 60}{'h' if since >= 3600 else 'm'}: {len(items)} item{'s' if len(items) != 1 else ''}" + (f" · quiet now ({why})" if q else ""))
    for lvl in LEVELS:
        rows = [x for x in items if x.get("level") == lvl]
        if not rows:
            continue
        print(f"{lvl.upper()} ({len(rows)})")
        for x in sorted(rows, key=lambda r: -r.get("t", 0))[:15]:
            print(f"  {datetime.fromtimestamp(x['t']):%a %H:%M}  {x.get('kind', ''):<9} {x.get('text', '')[:110]}  [{x.get('how', '')}]")
        if len(rows) > 15:
            print(f"  … and {len(rows) - 15} more")
    return 0


def cmd_quiet(a):
    if not a or a[0] == "status":
        q, why = quiet_status()
        print(f"quiet ({why})" if q else "not quiet" + ("; an event is on" if in_event() else "")); return 0
    if a[0] == "off":
        QUIET.write_text(json.dumps({})); print("quiet off"); return 0
    if a[0] == "on":
        hours = 2.0
        if len(a) > 1:
            m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(h|m)?", a[1].strip())
            if m:
                hours = float(m.group(1)) / (60 if m.group(2) == "m" else 1)
        until = time.time() + hours * 3600
        QUIET.write_text(json.dumps({"until": until, "set": time.time()}))
        print(f"quiet until {datetime.fromtimestamp(until):%H:%M}: only the urgent is spoken; the rest waits for the digest"); return 0
    print("triage.py quiet on [2h] | off | status"); return 2


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "digest":
        return cmd_digest(a[1:])
    if a[0] == "quiet":
        return cmd_quiet(a[1:])
    if a[0] == "level" and len(a) > 2:
        print(classify(a[1], " ".join(a[2:]))); return 0
    print("triage.py digest [--since 8h] | quiet on [2h]|off|status | level <kind> \"<text>\""); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
