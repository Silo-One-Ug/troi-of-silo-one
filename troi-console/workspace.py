#!/usr/bin/env python3
"""Workspaces: one word sets the desk (Silo One, 2026-09-27). "Start my work setup" opens the apps, starts what must run, puts
the pages up in the owner's browser and a sticky note with the open priorities on the screen.

  workspace.py start work [--dry]      run the steps of the "work" workspace (--dry says what would happen)
  workspace.py end work [--dry]        run its end steps (quit what it opened), when it has any
  workspace.py list | show work        the workspaces, and one workspace's steps
  workspace.py add work app "Visual Studio Code"      a step appended: app | quit | url | run | sticky | tool | focus | say | wait
  workspace.py priorities              the open items of the vault's Active Priorities, as the sticky would show them

The steps, in data/workspaces.json (the owner's; changed at their word):
  {"app": "Visual Studio Code"}                 open an application (apps.sh open)
  {"quit": "Visual Studio Code"}                quit one politely (apps.sh quit; it may ask to save)
  {"url": "https://github.com"}                 a page in the owner's default browser (https only)
  {"run": "colima start", "unless": "colima status"}   a command; skipped when the "unless" check succeeds; never anything
                                                that removes, kills, resets or forces (refused by word)
  {"sticky": "priorities"} | {"sticky": "any words"}   a Stickies note: the open priorities, or the words given
  {"tool": "sounds.py play focus"}              one of the agent's own tools in troi-console/
  {"focus": "Visual Studio Code"}               bring an app forward across Spaces (spaces.sh to)
  {"say": "Your work setup is up."}             a line for the agent to say when the steps are done
  {"wait": 2}                                   a pause, in seconds

Each step reports; a step that fails does not stop the rest. Nothing here removes anything.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
FILE = P.DATA / "workspaces.json"
# a step never removes, kills, resets or forces: the words that would, refused wherever they stand in the command
FORBIDDEN = re.compile(r"(?:^|[\s;&|(`])(?:rm|rmdir|unlink|shred|kill|pkill|killall|shutdown|reboot|halt|mkfs|diskutil|dd|format|truncate|srm)(?=\s|$)"
                       r"|(?:^|\s)(?:--force|--hard|--delete|--purge|--prune|-rf|-fr|-f)(?=\s|$)"
                       r"|\b(?:delete|prune|drop\s+(?:table|database)|reset\s+--hard|force-push)\b"
                       r"|>\s*/dev/", re.I)
STICKY_LIMIT = 12


def load():
    try:
        d = json.loads(FILE.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save(d):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False))


def log(line):
    try:
        P.LOGS.mkdir(parents=True, exist_ok=True)
        with open(P.LOGS / "workspace.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass


def sh(args, timeout=120, shell=False):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=shell, env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")})
    return r.returncode, (r.stdout + r.stderr).strip()


# ---- the sticky
def priorities():
    """The open items of the vault's Active Priorities, cleaned for a sticky: the link brackets off, each cut to a line."""
    try:
        vault = Path(str(json.loads(P.CONFIG.read_text()).get("vault") or (P.DATA / "vault"))).expanduser()
        text = (vault / "Active Priorities.md").read_text()
    except Exception:
        return []
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*-\s*\[ \]\s*(.+)$", line)
        if not m:
            continue
        s = m.group(1)
        s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda mm: mm.group(2) or mm.group(1), s)
        s = re.sub(r"\s*See [^.]*\.$", "", s).strip()
        s = re.sub(r"`", "", s)
        if len(s) > 150:
            s = s[:147].rstrip() + "…"
        items.append(s)
    return items


def sticky_text(what):
    if what == "priorities":
        items = priorities()
        head = f"Open priorities · {datetime.now():%a %d %b}"
        body = "\n".join(f"• {it}" for it in items[:STICKY_LIMIT]) if items else "• nothing open"
        if len(items) > STICKY_LIMIT:
            body += f"\n… and {len(items) - STICKY_LIMIT} more in the vault"
        return head + "\n" + body
    return str(what)


def make_sticky(text):
    """A new Stickies note with the text: Stickies has no scripting of its own, so the note is made the way a hand would,
    a new note and a paste; the clipboard's text is put back after. Needs Accessibility for the process running this."""
    had = None
    try:
        r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5); had = r.stdout if r.returncode == 0 else None
    except Exception:
        had = None
    subprocess.run(["pbcopy"], input=text, text=True, timeout=5)
    script = '''
tell application "Stickies" to activate
delay 0.8
tell application "System Events"
  tell process "Stickies"
    set frontmost to true
    keystroke "n" using command down
    delay 0.5
    keystroke "v" using command down
  end tell
end tell'''
    ok, out = sh(["osascript", "-e", script], timeout=30)
    time.sleep(0.6)
    if had is not None:
        try:
            subprocess.run(["pbcopy"], input=had, text=True, timeout=5)
        except Exception:
            pass
    if ok != 0:
        return False, out[:200]
    return True, ""


# ---- the steps
def run_step(step, dry):
    if not isinstance(step, dict) or not step:
        return ("skip", "not a step")
    kind, val = next(iter(step.items()))
    if kind == "app":
        if dry:
            return ("would", f"open {val}")
        code, out = sh([str(HERE / "apps.sh"), "open", str(val)], timeout=60)
        return ("ok", f"{val} opened") if code == 0 else ("fail", f"{val}: {out[:120] or 'could not open'}")
    if kind == "quit":
        if dry:
            return ("would", f"quit {val}")
        code, out = sh([str(HERE / "apps.sh"), "quit", str(val)], timeout=60)
        return ("ok", f"{val} asked to quit") if code == 0 else ("fail", f"{val}: {out[:120]}")
    if kind == "url":
        u = str(val).strip()
        if not u.lower().startswith("https://"):
            return ("fail", f"{u}: https only")
        if dry:
            return ("would", f"open {u} in the default browser")
        code, out = sh(["open", u], timeout=30)
        shown = re.sub(r"^https://(www\.)?", "", u).rstrip("/")
        return ("ok", f"{shown} in the browser") if code == 0 else ("fail", f"{u}: {out[:120]}")
    if kind == "run":
        cmd = str(val).strip()
        if FORBIDDEN.search(cmd):
            return ("fail", f"refused, it removes, kills, resets or forces: {cmd}")
        unless = step.get("unless")
        if unless:
            if FORBIDDEN.search(str(unless)):
                return ("fail", f"refused check: {unless}")
            code, _ = sh(shlex.split(str(unless)), timeout=60)
            if code == 0:
                return ("skip", f"{cmd}: already the case ({unless} succeeded)")
        if dry:
            return ("would", f"run {cmd}")
        code, out = sh(shlex.split(cmd), timeout=int(step.get("timeout") or 300))
        tail = out.splitlines()[-1][:120] if out else ""
        return ("ok", f"{cmd}" + (f": {tail}" if tail else "")) if code == 0 else ("fail", f"{cmd} exited {code}: {tail}")
    if kind == "sticky":
        text = sticky_text(val)
        n = text.count("\n")
        if dry:
            return ("would", f"a sticky note with {n} line{'s' if n != 1 else ''}: {text.splitlines()[0]}")
        ok, err = make_sticky(text)
        if ok:
            return ("ok", f"a sticky note: {text.splitlines()[0]} ({n} line{'s' if n != 1 else ''})")
        fallback = P.DATA / "blobs" / "notes"; fallback.mkdir(parents=True, exist_ok=True)
        f = fallback / f"sticky-{datetime.now():%Y-%m-%d_%H-%M}.txt"; f.write_text(text)
        sh(["open", "-e", str(f)], timeout=15)
        return ("fail", f"Stickies could not take the note ({err or 'Accessibility is needed for the process running this'}); it is open in TextEdit instead: {f}")
    if kind == "tool":
        parts = shlex.split(str(val))
        if not parts or not (HERE / parts[0]).exists() or "/" in parts[0]:
            return ("fail", f"not one of my tools: {val}")
        if FORBIDDEN.search(str(val)):
            return ("fail", f"refused: {val}")
        if dry:
            return ("would", f"run {val}")
        code, out = sh([str(HERE / parts[0]), *parts[1:]], timeout=120)
        return ("ok", f"{val}" + (f": {out.splitlines()[-1][:100]}" if out else "")) if code == 0 else ("fail", f"{val}: {out[:120]}")
    if kind == "focus":
        if dry:
            return ("would", f"bring {val} forward")
        code, out = sh([str(HERE / "spaces.sh"), "to", str(val)], timeout=30)
        return ("ok", f"{val} in front") if code == 0 else ("fail", f"{val}: {out[:120]}")
    if kind == "say":
        return ("say", str(val))
    if kind == "wait":
        s = min(30, max(0, float(val or 0)))
        if not dry:
            time.sleep(s)
        return ("ok", f"waited {s:g} s")
    return ("skip", f"unknown step: {kind}")


def run(name, which, dry):
    ws = load().get(name)
    if not ws:
        print(f"no workspace called {name}; workspace.py list"); return 2
    steps = ws.get(which) or []
    if not steps:
        print(f"the {name} workspace has no {'end ' if which == 'end' else ''}steps"); return 0
    print(f"{'would ' if dry else ''}{'end' if which == 'end' else 'start'} {ws.get('name') or name}: {len(steps)} step{'s' if len(steps) != 1 else ''}")
    marks = {"ok": "✓", "would": "·", "skip": "·", "fail": "✗", "say": "»"}
    fails = 0; says = []
    for st in steps:
        status, what = run_step(st, dry)
        if status == "say":
            says.append(what); continue
        if status == "fail":
            fails += 1
        print(f"  {marks.get(status, '·')} {what}")
        log(f"{name} {which}: {status} {what}")
    for s in says:
        print(f"  » say: {s}")
    print(("done" if not fails else f"done with {fails} failure{'s' if fails != 1 else ''}") + (" (nothing was done: a dry run)" if dry else ""))
    return 1 if fails else 0


def cmd_list():
    d = load()
    if not d:
        print("no workspaces yet: workspace.py add work app \"Visual Studio Code\" … (see --help)"); return 0
    for k, ws in d.items():
        print(f"{k:<10} {ws.get('name') or k}: {len(ws.get('steps') or [])} step{'s' if len(ws.get('steps') or []) != 1 else ''}" + (f", {len(ws['end'])} to end" if ws.get("end") else ""))
    return 0


def cmd_show(name):
    ws = load().get(name)
    if not ws:
        print(f"no workspace called {name}"); return 2
    print(f"{ws.get('name') or name}")
    for st in ws.get("steps") or []:
        k, v = next(iter(st.items())); extra = {kk: vv for kk, vv in st.items() if kk != k}
        print(f"  {k}: {v}" + (f"   {extra}" if extra else ""))
    if ws.get("end"):
        print("  to end:")
        for st in ws["end"]:
            k, v = next(iter(st.items())); print(f"  {k}: {v}")
    return 0


def cmd_add(a):
    if len(a) < 3:
        print('usage: workspace.py add <workspace> <app|quit|url|run|sticky|tool|focus|say|wait> "<value>" [--end] [--unless "<check>"]'); return 2
    a = list(a); end = "--end" in a
    if end:
        a.remove("--end")
    unless = None
    if "--unless" in a:
        i = a.index("--unless"); unless = a[i + 1]; del a[i:i + 2]
    name, kind, val = a[0], a[1], " ".join(a[2:])
    if kind not in ("app", "quit", "url", "run", "sticky", "tool", "focus", "say", "wait"):
        print(f"not a step kind: {kind}"); return 2
    if kind == "run" and FORBIDDEN.search(val):
        print(f"refused: a step never removes, kills, resets or forces ({val})"); return 2
    if kind == "url" and not val.lower().startswith("https://"):
        print("a url step is https only"); return 2
    d = load(); ws = d.setdefault(name, {"name": name.capitalize(), "steps": [], "end": []})
    step = {kind: float(val) if kind == "wait" else val}
    if unless and kind == "run":
        step["unless"] = unless
    ws.setdefault("end" if end else "steps", []).append(step); save(d)
    print(f"{name}: {kind} step added" + (" (to end)" if end else "") + f"; {len(ws['end' if end else 'steps'])} now"); return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    dry = "--dry" in a
    a = [x for x in a if x != "--dry"]
    if a[0] in ("start", "end") and len(a) > 1:
        return run(a[1], "steps" if a[0] == "start" else "end", dry)
    if a[0] == "list":
        return cmd_list()
    if a[0] == "show" and len(a) > 1:
        return cmd_show(a[1])
    if a[0] == "add":
        return cmd_add(a[1:])
    if a[0] == "priorities":
        for it in priorities():
            print("• " + it)
        return 0
    print("workspace.py start|end <name> [--dry] · list · show <name> · add <name> <kind> <value> · priorities"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
