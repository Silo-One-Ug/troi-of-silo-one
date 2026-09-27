#!/usr/bin/env python3
"""Your time at the Mac (Silo One, 2026-09-27): which apps had the front, for how long, and what that adds up to.

  usage.py today | yesterday | week | since YYYY-MM-DD [--json]   the report: hours at the Mac, by kind (coding, browsing, meetings,
                                                                  talking, the rest) and by app, the focus stretches, the switches
  usage.py sample                                                one sample by hand (the pulse takes one every 30 seconds)

What is kept: the name of the app in front, in seconds per day, and the stretches of 25 minutes or more in one app. Never a
window title, never an address, never what was typed. Samples stop while the Mac is idle (no key or mouse for two minutes).
`usage_tracking: false` in the console's settings stops the sampling altogether. The document is "usage" in data/troi.db,
the last 90 days. Stdlib and the Mac's own tools (osascript, ioreg).
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _DB  # noqa: E402
import paths as P  # noqa: E402

DOC = _DB.doc("usage")
EVERY = 30
IDLE_S = 120
FOCUS_MIN = 25 * 60
KEEP_DAYS = 90
KINDS = {
    "coding": {"Code", "Visual Studio Code", "Cursor", "Zed", "Xcode", "WezTerm", "Terminal", "iTerm2", "Warp", "Ghostty", "PyCharm", "IntelliJ IDEA", "Android Studio", "Sublime Text"},
    "browsing": {"Comet", "Google Chrome", "Safari", "Arc", "Firefox", "Brave Browser", "Microsoft Edge"},
    "meetings": {"zoom.us", "Microsoft Teams", "FaceTime", "Webex", "Skype"},
    "talking": {"Mail", "Telegram", "Slack", "Messages", "WhatsApp", "Discord", "Outlook"},
    "writing": {"Obsidian", "Notes", "Pages", "Microsoft Word", "TextEdit", "Notion", "Craft"},
    "music": {"Music", "Spotify", "Podcasts"},
}


def load():
    try:
        d = json.loads(DOC.read_text())
        return d if isinstance(d, dict) else {"days": {}}
    except Exception:
        return {"days": {}}


def save(d):
    days = d.get("days", {})
    for k in sorted(days)[:-KEEP_DAYS]:
        days.pop(k, None)
    DOC.write_text(json.dumps(d))


def tracking_on():
    try:
        return json.loads(P.CONFIG.read_text()).get("usage_tracking", True) is not False
    except Exception:
        return True


def front_app():
    try:
        r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def idle_seconds():
    try:
        out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        return int(m.group(1)) / 1e9 if m else 0.0
    except Exception:
        return 0.0


def sample(state=None):
    """One sample: the front app gets the seconds since the last sample (30 at most, 60 when a beat was missed); a stretch
    of one app is followed and kept when it reaches 25 minutes. `state` is the pulse's memory (last sample, the open stretch)."""
    if not tracking_on():
        return None
    st = state if isinstance(state, dict) else {}
    now = time.time(); mem = st.setdefault("usage", {})
    if idle_seconds() > IDLE_S:
        _close_stretch(mem, now); mem["last"] = now; return "idle"
    app = front_app()
    if not app:
        mem["last"] = now; return None
    last = float(mem.get("last") or now); dt = min(60.0, max(0.0, now - last)) if mem.get("last") else float(EVERY)
    mem["last"] = now
    d = load(); day = d.setdefault("days", {}).setdefault(date.today().isoformat(), {"apps": {}, "switches": 0, "first": now, "last": now, "sessions": [], "firstseen": {}})
    day["apps"][app] = round(day["apps"].get(app, 0) + dt, 1); day["last"] = now; day.setdefault("firstseen", {}).setdefault(app, now)
    cur = mem.get("stretch")
    if cur and cur.get("app") == app:
        cur["end"] = now
    else:
        if cur:
            day["switches"] = int(day.get("switches", 0)) + 1
        _close_stretch(mem, now, d)
        mem["stretch"] = {"app": app, "start": now, "end": now}
    save(d)
    return app


def _close_stretch(mem, now, d=None):
    cur = mem.pop("stretch", None)
    if not cur:
        return
    length = float(cur.get("end", now)) - float(cur["start"])
    if length >= FOCUS_MIN:
        d = d or load()
        day = d.setdefault("days", {}).setdefault(datetime.fromtimestamp(cur["start"]).date().isoformat(), {"apps": {}, "switches": 0, "first": cur["start"], "last": now, "sessions": [], "firstseen": {}})
        day.setdefault("sessions", []).append([round(cur["start"]), round(cur["end"]), cur["app"]])
        save(d)


def kind_of(app):
    for k, apps in KINDS.items():
        if app in apps:
            return k
    return "other"


def hours(s):
    return f"{s / 3600:.1f} h" if s >= 3600 else f"{round(s / 60)} min"


def report(days, label):
    d = load().get("days", {})
    picked = {k: v for k, v in d.items() if k in days}
    if not picked:
        return {"label": label, "empty": True}
    apps = {}; sessions = []; switches = 0; first = None; last = None
    for k in sorted(picked):
        v = picked[k]
        for a, s in v.get("apps", {}).items():
            apps[a] = apps.get(a, 0) + s
        sessions += [(*s, k) for s in v.get("sessions", [])]
        switches += int(v.get("switches", 0))
        first = v.get("first") if first is None else min(first, v.get("first", first)); last = v.get("last") if last is None else max(last, v.get("last", last))
    total = sum(apps.values())
    by_kind = {}
    for a, s in apps.items():
        by_kind[kind_of(a)] = by_kind.get(kind_of(a), 0) + s
    return {"label": label, "days": len(picked), "total": total, "apps": sorted(apps.items(), key=lambda x: -x[1]), "kinds": sorted(by_kind.items(), key=lambda x: -x[1]),
            "sessions": sorted(sessions, key=lambda s: -(s[1] - s[0])), "switches": switches, "first": first, "last": last}


def say(r):
    if r.get("empty"):
        return f"{r['label']}: nothing recorded yet" + ("" if tracking_on() else " (usage_tracking is off in the settings)")
    lines = [f"{r['label']}: {hours(r['total'])} at the Mac" + (f" over {r['days']} days" if r["days"] > 1 else (f" (first {datetime.fromtimestamp(r['first']):%H:%M}, last {datetime.fromtimestamp(r['last']):%H:%M})" if r.get("first") else "")) + f", {r['switches']} switches"]
    for k, s in r["kinds"]:
        top = [f"{a} {hours(t)}" for a, t in r["apps"] if kind_of(a) == k][:3]
        lines.append(f"  {k:<9} {hours(s):>8}   " + ", ".join(top))
    ses = r["sessions"]
    if ses:
        longest = ses[0]
        lines.append(f"  focus     {len(ses)} stretch{'es' if len(ses) != 1 else ''} of 25 min or more; the longest {round((longest[1] - longest[0]) / 60)} min in {longest[2]}" + (f" ({longest[3]})" if r["days"] > 1 else ""))
    else:
        lines.append("  focus     no stretch of 25 minutes in one app")
    return "\n".join(lines)


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    js = "--json" in a; a = [x for x in a if x != "--json"]
    today = date.today()
    if a[0] == "sample":
        print(sample({}) or "nothing sampled"); return 0
    if a[0] == "today":
        r = report({today.isoformat()}, "Today")
    elif a[0] == "yesterday":
        r = report({(today - timedelta(days=1)).isoformat()}, "Yesterday")
    elif a[0] == "week":
        r = report({(today - timedelta(days=i)).isoformat() for i in range(7)}, "The last seven days")
    elif a[0] == "since" and len(a) > 1:
        try:
            start = date.fromisoformat(a[1])
        except ValueError:
            print("since YYYY-MM-DD"); return 2
        r = report({(start + timedelta(days=i)).isoformat() for i in range((today - start).days + 1)}, f"Since {a[1]}")
    else:
        print("usage.py today | yesterday | week | since YYYY-MM-DD [--json] | sample"); return 2
    print(json.dumps(r) if js else say(r)); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
