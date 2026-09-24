#!/usr/bin/env python3
"""the agent's calendar: what is on today, what is next, what starts soon. Reads the Mac's Calendar app
(every account added under System Settings > Internet Accounts: Google, iCloud, Exchange). Stdlib only.

  agenda.py today                 today's events (JSON list: title, start, end, calendar, location, link)
  agenda.py next                  the next event from now (or {} if none in 7 days)
  agenda.py week                  the next 7 days
  agenda.py soon [minutes]        events starting within N minutes (default 20), for the pulse
  agenda.py current               the event happening right now, if any (meeting.py names recordings after it)

"link" is the first video-call URL found in the location or notes (Meet, Zoom, Teams, Webex).
Ignore calendars by listing their names in console.json "calendar_ignore" (default: Birthdays, Siri Suggestions).
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
LINK = re.compile(r"https?://[^\s<>\"']*(?:meet\.google\.com|zoom\.us|teams\.microsoft\.com|teams\.live\.com|webex\.com)[^\s<>\"']*")


def ignored():
    try: return set(json.loads((P.CONFIG).read_text()).get("calendar_ignore", ["Birthdays", "Siri Suggestions"]))
    except Exception: return {"Birthdays", "Siri Suggestions"}


def events(start, end):
    """Events overlapping [start, end) from every calendar, via one AppleScript pass; tab-separated fields."""
    def apple(var, d):                       # built from parts: locale-proof, unlike a date "..." literal
        return (f'set {var} to current date\nset year of {var} to {d.year}\nset month of {var} to {d.month}\nset day of {var} to {d.day}\n'
                f'set time of {var} to {d.hour * 3600 + d.minute * 60 + d.second}')
    script = f'''
{apple("d1", start)}
{apple("d2", end)}
set out to ""
tell application "Calendar"
  repeat with c in calendars
    set cname to name of c
    try
      set evs to (every event of c whose start date < d2 and end date > d1)
      repeat with e in evs
        set out to out & cname & tab & (summary of e) & tab & ((start date of e) as «class isot» as string) & tab & ((end date of e) as «class isot» as string) & tab & (allday event of e) & tab & (location of e) & tab & (description of e) & linefeed
      end repeat
    end try
  end repeat
end tell
return out'''
    if subprocess.run(["pgrep", "-x", "Calendar"], capture_output=True).returncode != 0:
        subprocess.run(["open", "-g", "-j", "-a", "Calendar"], capture_output=True)      # in the background, no window
        import time; time.sleep(3)
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
    if r.returncode != 0 and "-600" in r.stderr:                                        # "isn't running": it is still launching
        import time; time.sleep(4); r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise SystemExit("Calendar: " + (r.stderr.strip().splitlines() or ["failed"])[-1])
    skip = ignored(); out = []
    for line in r.stdout.splitlines():
        f = line.split("\t")
        if len(f) < 7 or f[0] in skip: continue
        cal, title, s, e, allday, loc, notes = f[0], f[1], f[2], f[3], f[4] == "true", f[5], f[6]
        try: sd, ed = dt.datetime.fromisoformat(s), dt.datetime.fromisoformat(e)
        except ValueError: continue
        m = LINK.search(loc + " " + notes)
        out.append({"title": title, "start": sd.isoformat(timespec="minutes"), "end": ed.isoformat(timespec="minutes"),
                    "allday": allday, "calendar": cal, "location": loc.replace("missing value", ""), "link": m.group(0) if m else ""})
    out.sort(key=lambda x: x["start"]); return out


def main(a):
    c = a[0] if a else "help"; now = dt.datetime.now()
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if c == "today": print(json.dumps(events(day0, day0 + dt.timedelta(days=1)), indent=2))
    elif c == "week": print(json.dumps(events(day0, day0 + dt.timedelta(days=7)), indent=2))
    elif c == "next":
        ev = [e for e in events(now, now + dt.timedelta(days=7)) if not e["allday"] and dt.datetime.fromisoformat(e["start"]) >= now]
        print(json.dumps(ev[0] if ev else {}, indent=2))
    elif c == "soon":
        mins = int(a[1]) if len(a) > 1 else 20
        ev = [e for e in events(now, now + dt.timedelta(minutes=mins)) if not e["allday"] and dt.datetime.fromisoformat(e["start"]) >= now]
        print(json.dumps(ev, indent=2))
    elif c == "current":
        ev = [e for e in events(now - dt.timedelta(minutes=1), now + dt.timedelta(minutes=1)) if not e["allday"]]
        print(json.dumps(ev[0] if ev else {}, indent=2))
    else: print(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
