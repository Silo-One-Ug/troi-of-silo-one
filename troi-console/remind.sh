#!/bin/bash
# the agent sets a reminder:  remind.sh "20m" "check the deploy"   (units: m, h, or HH:MM today/tomorrow)
# List: remind.sh list      Cancel: remind.sh cancel <number>
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; export C
python3 - "$@" <<'PY'
import json, os, sys, time, re, datetime as dt
sys.path.insert(0, os.environ["C"]); import db                   # reminders are a document in data/troi.db
F = db.doc("reminders")
try: items = json.loads(F.read_text())
except FileNotFoundError: items = []
a = sys.argv[1:]
if not a or a[0] == "list":
    for i, r in enumerate(items, 1): print(f"{i}. {dt.datetime.fromtimestamp(r['at']):%a %H:%M} — {r['text']}")
    print("no reminders" if not items else ""); sys.exit()
if a[0] == "cancel":
    n = int(a[1]) - 1; r = items.pop(n); F.write_text(json.dumps(items, indent=2)); print("cancelled:", r["text"]); sys.exit()
when, text = a[0], " ".join(a[1:])
m = re.fullmatch(r"(\d+)\s*(m|min|mins|minutes?|h|hr|hours?)", when.strip())
if m:
    n = int(m.group(1)); at = time.time() + n * (60 if m.group(2).startswith("m") else 3600)
else:
    hh, mm = map(int, when.split(":")); t = dt.datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    if t < dt.datetime.now(): t += dt.timedelta(days=1)
    at = t.timestamp()
items.append({"at": at, "text": text}); F.write_text(json.dumps(items, indent=2))
print(f"reminder set for {dt.datetime.fromtimestamp(at):%a %H:%M}: {text}")
PY
