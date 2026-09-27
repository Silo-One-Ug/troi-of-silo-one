#!/usr/bin/env python3
"""Habits: what repeats, and what could be automated (Silo One, 2026-09-27). Nothing here creates anything; it proposes.

  habits.py suggest [--days 14]     the suggestions, numbered, each with the command that would set it up
  habits.py raised <n>              mark one as put to the owner, so it is not raised again for a fortnight
  habits.py answers                 what was raised, and when

Three kinds of repetition are looked for:
  the morning apps      the same apps in front in the first half hour of the day on most days -> a workspace
  the same request      the same words asked three times or more (the record's own lines) -> a workspace step, or a time watch
                        when the asks fall in one hour of the day
  the same file work    the same file-hands operation on the same folder three times or more -> a folder watch
Stdlib only. What is read: the "usage" document, the record's messages and data/logs/fs.log. The raised ones are kept in the
"habits" document.
"""
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _DB  # noqa: E402
import paths as P  # noqa: E402

RAISED = _DB.doc("habits")
QUIET_DAYS = 14
STOP = {"please", "troi", "can", "you", "could", "would", "the", "a", "an", "me", "my", "for", "to", "and", "now", "again", "ok", "okay", "hey", "hi", "hello"}
CONTROL = ("push talk", "hands free", "movie mode", "clear session", "compact session", "text only", "speak", "welcome", "stop", "mode off", "quiet", "aloud", "switch deep", "back fast", "set effort")


def raised():
    try:
        d = json.loads(RAISED.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def norm_request(t):
    t = re.sub(r"[^a-z0-9 ]", " ", str(t).lower())
    words = [w for w in t.split() if w not in STOP]
    return " ".join(words)


def morning_apps(days):
    try:
        d = json.loads(_DB.doc("usage").read_text()).get("days", {})
    except Exception:
        return []
    counts = Counter(); seen_days = 0
    since = (date.today() - timedelta(days=days)).isoformat()
    for k, v in d.items():
        if k < since or not v.get("firstseen") or not v.get("first"):
            continue
        seen_days += 1
        for app, t in v["firstseen"].items():
            if t - v["first"] <= 1800:
                counts[app] += 1
    if seen_days < 3:
        return []
    regular = [a for a, n in counts.items() if n >= max(3, round(seen_days * 0.6))]
    return [(regular, seen_days)] if len(regular) >= 2 else []


def requests(days):
    since = time.time() - days * 86400
    try:
        with _DB.connect() as c:
            rows = c.execute("select text, t from messages where role='you' and t >= ? order by t", (since,)).fetchall()
    except Exception:
        return []
    groups = defaultdict(list)
    for r in rows:
        key = norm_request(r["text"])
        if len(key) < 6 or len(key.split()) > 12:
            continue
        groups[key].append((r["text"], r["t"]))
    out = []
    for key, items in groups.items():
        if len(items) < 3 or any(c in key for c in CONTROL):
            continue                                                # a switch of the voice line's own is a habit of the console, not of the owner's work
        hours = [datetime.fromtimestamp(t).hour for _, t in items]
        common = Counter(hours).most_common(1)[0]
        window = common[0] if common[1] >= len(items) * 0.7 else None
        out.append((items[-1][0], len(items), window))
    return sorted(out, key=lambda x: -x[1])


def file_work():
    try:
        lines = (P.LOGS / "fs.log").read_text(errors="replace").splitlines()[-3000:]
    except Exception:
        return []
    counts = Counter()
    for line in lines:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}) \S+ (move|copy|rename|zip|tag)\s+(\S.*?)(?:\s+->\s+(\S.*))?$", line)
        if not m:
            continue
        src = m.group(3).strip(); folder = str(Path(src).parent)
        counts[(m.group(2), folder)] += 1
    return [(op, folder, n) for (op, folder), n in counts.items() if n >= 3]


def suggestions(days):
    out = []
    for apps, seen in morning_apps(days):
        names = ", ".join(sorted(apps))
        out.append({"kind": "workspace", "why": f"{names} were the first apps up on {seen} of the last {days} days", "do": "a workspace that opens them: " + " ".join(f'workspace.py add morning app "{a}";' for a in sorted(apps))})
    for text, n, hour in requests(days):
        if hour is not None:
            out.append({"kind": "watch", "why": f'"{text}" asked {n} times, usually around {hour:02d}:00', "do": f'watches.py add time "every day at {hour:02d}:00" "{text}"'})
        else:
            out.append({"kind": "step", "why": f'"{text}" asked {n} times', "do": f'a workspace step, or a shorter word for it: workspace.py add work say "{text}"'})
    for op, folder, n in file_work():
        out.append({"kind": "folder", "why": f"{op} in {folder}, {n} times", "do": f'watches.py add folder "{folder}" "do the usual with what lands here"'})
    for s in out:
        s["id"] = hashlib.sha1((s["kind"] + s["do"]).encode()).hexdigest()[:10]
    r = raised()
    fresh = [s for s in out if time.time() - float(r.get(s["id"], 0)) > QUIET_DAYS * 86400]
    return fresh, out


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "suggest":
        days = 14
        if "--days" in a:
            i = a.index("--days"); days = int(a[i + 1])
        fresh, allof = suggestions(days)
        if not fresh:
            print("nothing repeats enough to suggest" + (f" ({len(allof)} already raised this fortnight)" if allof else "") + f"; the last {days} days looked at"); return 0
        print(f"{len(fresh)} suggestion{'s' if len(fresh) != 1 else ''} from the last {days} days (nothing is set up until the owner says so):")
        for i, s in enumerate(fresh, 1):
            print(f"{i:>2}. {s['why']}\n    -> {s['do']}   [habits.py raised {i}]")
        return 0
    if a[0] == "raised" and len(a) > 1:
        fresh, _ = suggestions(14); n = int(a[1]) - 1
        if not (0 <= n < len(fresh)):
            print("no such suggestion"); return 2
        r = raised(); r[fresh[n]["id"]] = time.time(); RAISED.write_text(json.dumps(r)); print(f"raised: {fresh[n]['why'][:80]} (quiet for {QUIET_DAYS} days)"); return 0
    if a[0] == "answers":
        r = raised()
        if not r:
            print("nothing raised yet"); return 0
        for k, t in sorted(r.items(), key=lambda x: -x[1]):
            print(f"  {datetime.fromtimestamp(t):%a %d %b %H:%M}  {k}")
        return 0
    print("habits.py suggest [--days 14] | raised <n> | answers"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
