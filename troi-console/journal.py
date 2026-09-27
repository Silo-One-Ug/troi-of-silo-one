#!/usr/bin/env python3
"""The action journal (Silo One, 2026-09-27): what the agent did, when, and how each thing is undone.

  journal.py list [--since 4h] [--kind files|workspace|watch|bookmark|request|said]   newest first, numbered
  journal.py undo [n]          undo the last reversible action, or #n from the list: a file moved, renamed, copied or a folder
                               made -> the file hands' own undo; a tag -> untag; an archive or an unpacked folder -> a Trash
                               request for it (the owner approves); a watch -> off; a bookmark -> archived. Nothing is deleted.
  journal.py why [n]           the entry, and what was said in the conversation in the ninety seconds around it

One read model over the logs the tools already keep: data/logs/fs.log (fs.sh and files.py), data/logs/workspace.log, the
watches and bookmarks, the approval requests and what the pulse said (the record). Stdlib only.
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

HERE = Path(__file__).resolve().parent
UNDO_FS = {"move", "rename", "copy", "mkdir"}


def ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        return None


def read_log(path, kind):
    out = []
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except Exception:
        return out
    for line in lines[-2000:]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\S+)\s*(.*)$", line)
        if not m:
            continue
        t = ts(m.group(1))
        if t is None:
            continue
        op, rest = m.group(2).rstrip(":").lower(), m.group(3).strip()
        if kind == "files" and op not in ("move", "rename", "copy", "mkdir", "undo", "trash", "zip", "unzip", "tag", "untag"):
            continue                                                # the file log also keeps the console's own lines (unlocks, refusals): not actions of mine
        out.append({"t": t, "kind": kind, "op": op, "what": rest})
    return out


def entries(since):
    now = time.time(); rows = []
    for e in read_log(P.LOGS / "fs.log", "files"):
        if e["op"] in UNDO_FS:
            e["undo"] = "fs.sh undo (the file hands put it back)"
        elif e["op"] == "tag":
            e["undo"] = "files.py untag"
        elif e["op"] in ("zip", "unzip"):
            e["undo"] = "a Trash request for what was made (fs.sh trash), yours to approve"
        elif e["op"] == "untag":
            e["undo"] = "files.py tag puts it back"
        else:
            e["undo"] = ""
        rows.append(e)
    for e in read_log(P.LOGS / "workspace.log", "workspace"):
        e["undo"] = "workspace.py end <name>, when it has end steps"
        rows.append(e)
    try:
        for w in json.loads(_DB.doc("watches").read_text()):
            rows.append({"t": float(w.get("created") or 0), "kind": "watch", "op": "set", "what": f"{w.get('id')}: {w.get('note')} -> {w.get('do') or 'tell'}" + ("" if w.get("on", True) else " (off)"), "undo": f"watches.py off {w.get('id')}", "wid": w.get("id")})
    except Exception:
        pass
    try:
        for i, b in enumerate(json.loads((P.DATA / "bookmarks.json").read_text()), 1):
            rows.append({"t": float(b.get("added") or 0), "kind": "bookmark", "op": "kept", "what": f"#{i} {b.get('title', '')[:60]} {b.get('url', '')}" + (" (archived)" if b.get("archived") else ""), "undo": f"browse.py bookmark archive {i}", "bid": i})
    except Exception:
        pass
    try:
        with _DB.connect() as c:
            for r in c.execute("select id, kind, src, why, status, at from approvals order by at desc limit 200"):
                rows.append({"t": float(r["at"] or 0), "kind": "request", "op": r["kind"] or "request", "what": f"{r['src']}" + (f" ({r['why']})" if r["why"] else "") + f" [{r['status']}]", "undo": "yours to decide on the console or Telegram"})
    except Exception:
        pass
    try:
        for x in json.loads(_DB.doc("triage").read_text()):
            rows.append({"t": float(x.get("t") or 0), "kind": "said", "op": x.get("level", ""), "what": f"{x.get('kind', '')}: {x.get('text', '')[:120]} [{x.get('how', '')}]", "undo": ""})
    except Exception:
        pass
    rows = [r for r in rows if r["t"] and now - r["t"] <= since]
    rows.sort(key=lambda r: -r["t"])
    return rows


def parse_since(a, default=4 * 3600):
    if "--since" in a:
        i = a.index("--since"); v = a[i + 1]; del a[i:i + 2]
        m = re.fullmatch(r"(\d+)\s*(m|h|d)?", v.strip())
        if m:
            return int(m.group(1)) * {"m": 60, "h": 3600, "d": 86400}[m.group(2) or "h"]
    return default


def cmd_list(a):
    since = parse_since(a); kind = None
    if "--kind" in a:
        i = a.index("--kind"); kind = a[i + 1]; del a[i:i + 2]
    rows = [r for r in entries(since) if not kind or r["kind"] == kind]
    if not rows:
        print("nothing in the journal for that stretch"); return 0
    for i, r in enumerate(rows, 1):
        print(f"{i:>3}. {datetime.fromtimestamp(r['t']):%a %H:%M}  {r['kind']:<9} {r['op']:<7} {r['what'][:120]}" + (f"   ↶ {r['undo']}" if r.get("undo") else ""))
    return 0


def pick(a):
    since = parse_since(a, 7 * 86400)
    rows = entries(since)
    n = int(a[0]) if a and a[0].isdigit() else None
    if n is not None:
        return rows[n - 1] if 0 < n <= len(rows) else None, rows
    return next((r for r in rows if r.get("undo") and r["kind"] in ("files", "watch", "bookmark")), None), rows


def cmd_undo(a):
    r, _ = pick(a)
    if not r:
        print("nothing to undo"); return 1
    print(f"undoing: {datetime.fromtimestamp(r['t']):%a %H:%M} {r['kind']} {r['op']} {r['what'][:100]}")
    if r["kind"] == "files" and r["op"] in UNDO_FS:
        out = subprocess.run([str(HERE / "fs.sh"), "undo"], capture_output=True, text=True, timeout=40)
        print((out.stdout + out.stderr).strip()[:300] or "asked the file hands to put it back"); return 0
    if r["kind"] == "files" and r["op"] == "tag":
        m = re.match(r"^(.*?)\s+\+\s+(.*)$", r["what"])
        if not m:
            print("the tag line could not be read"); return 1
        tags = [t.strip() for t in m.group(2).split(",") if t.strip() and not t.startswith("(")]
        out = subprocess.run([sys.executable, str(HERE / "files.py"), "untag", m.group(1), *tags], capture_output=True, text=True, timeout=40)
        print((out.stdout + out.stderr).strip()[:300]); return 0
    if r["kind"] == "files" and r["op"] in ("zip", "unzip"):
        m = re.match(r"^(.*?)\s+->\s+(.*)$", r["what"])
        if not m:
            print("the line could not be read"); return 1
        out = subprocess.run([str(HERE / "fs.sh"), "trash", m.group(2), f"undo of {r['op']} at the owner's word"], capture_output=True, text=True, timeout=40)
        print(f"a Trash request for {m.group(2)} is waiting for your approval" + (f" ({out.stdout.strip()[:60]})" if out.stdout.strip() else "")); return 0
    if r["kind"] == "watch" and r.get("wid"):
        out = subprocess.run([sys.executable, str(HERE / "watches.py"), "off", str(r["wid"])], capture_output=True, text=True, timeout=30)
        print(out.stdout.strip()[:200]); return 0
    if r["kind"] == "bookmark" and r.get("bid"):
        out = subprocess.run([sys.executable, str(HERE / "browse.py"), "bookmark", "archive", str(r["bid"])], capture_output=True, text=True, timeout=30)
        print(out.stdout.strip()[:200]); return 0
    print("that one is not mine to undo: " + (r.get("undo") or "it changed nothing")); return 1


def cmd_why(a):
    rows = entries(7 * 86400)
    if a and a[0].isdigit():
        n = int(a[0]); r = rows[n - 1] if 0 < n <= len(rows) else None
    else:
        r = rows[0] if rows else None
    if not r:
        print("nothing in the journal"); return 1
    print(f"{datetime.fromtimestamp(r['t']):%a %d %b %H:%M:%S}  {r['kind']} {r['op']}  {r['what'][:160]}")
    try:
        with _DB.connect() as c:
            rows = c.execute("select role, text, t from messages where t between ? and ? and role in ('you','agent','note') order by t", (r["t"] - 90, r["t"] + 90)).fetchall()
    except Exception as e:
        print(f"the record could not be read: {str(e)[:100]}"); return 1
    if not rows:
        print("nothing was said in the conversation in the ninety seconds around it (a routine, or the other session)"); return 0
    print("what was said around it:")
    for m in rows:
        print(f"  {datetime.fromtimestamp(m['t']):%H:%M:%S}  {m['role']:<5} {str(m['text'])[:160]}")
    return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "list":
        return cmd_list(a[1:])
    if a[0] == "undo":
        return cmd_undo(a[1:])
    if a[0] == "why":
        return cmd_why(a[1:])
    print("journal.py list [--since 4h] [--kind …] | undo [n] | why [n]"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
