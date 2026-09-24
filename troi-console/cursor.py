#!/usr/bin/env python3
"""the agent's real hands on the Mac: the actual pointer and keyboard, with guards.

  cursor.py where                    pointer position
  cursor.py move X Y                 move the pointer
  cursor.py click [X Y]              left-click        cursor.py double [X Y]      cursor.py right [X Y]
  cursor.py drag X1 Y1 X2 Y2         press, drag, release
  cursor.py type "text"              type into the focused field
  cursor.py key <name>               return, tab, esc, space, delete, arrows, or combos like cmd+c, cmd+shift+t
  cursor.py under [X Y]              what is under the pointer (role, title, app)

Guards, all of them always on:
  look first     a click needs a screenshot (look-screen.sh) taken in the last 45 s,
                 so the agent acts on what is really on screen, not on memory
  read the button  the accessibility API names the element under the pointer; a
                 risky one (delete, remove, erase, empty trash, pay, buy, send, submit,
                 allow, install, reset, format, quit…) is NOT clicked: an approval
                 request is filed for the owner instead (console card / Telegram)
  keys           destructive shortcuts are refused outright (cmd+delete, cmd+shift+delete,
                 cmd+q, cmd+w, cmd+shift+q, cmd+opt+esc)
  no secrets     text that looks like a password prompt is refused
  everything is logged to troi-console/logs/cursor.log
"""
import glob, json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

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
LOGF = P.LOGS / "cursor.log"
CLI = "/opt/homebrew/bin/cliclick"
RISKY = re.compile(r"\b(delete|remove|erase|empty trash|move to trash|trash|pay|purchase|buy|checkout|send|submit|confirm|allow|always allow|grant|install|uninstall|reset|restore|format|wipe|quit|force quit|shut down|restart|log out|sign out|unsubscribe|cancel subscription|transfer|withdraw)\b", re.I)
BLOCKED_KEYS = {"cmd+delete", "cmd+shift+delete", "cmd+backspace", "cmd+shift+backspace", "cmd+q", "cmd+shift+q", "cmd+w", "cmd+alt+esc", "cmd+opt+esc", "cmd+ctrl+q"}


def log(line):
    LOGF.parent.mkdir(exist_ok=True)
    with LOGF.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


def out(obj):
    print(json.dumps(obj)); sys.exit(0 if obj.get("ok") else 1)


def cli(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True, timeout=20)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def pointer():
    ok, s = cli("p"); m = re.search(r"(\d+),(\d+)", s)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def looked_recently(seconds=45):
    shots = glob.glob(str(P.blob_dir("screens") / "*"))
    return bool(shots) and time.time() - max(os.path.getmtime(s) for s in shots) < seconds


def under(x, y):
    """Role / title / app of the element under a point, via the accessibility API."""
    try:
        from ApplicationServices import (AXUIElementCreateSystemWide, AXUIElementCopyElementAtPosition, AXUIElementCopyAttributeValue, AXIsProcessTrusted)
        if not AXIsProcessTrusted():
            return {"trusted": False}
        err, el = AXUIElementCopyElementAtPosition(AXUIElementCreateSystemWide(), float(x), float(y), None)
        if err or el is None:
            return {"trusted": True, "role": None}
        def attr(a):
            e, v = AXUIElementCopyAttributeValue(el, a, None); return None if e else (str(v) if v is not None else None)
        role, title, desc, val = attr("AXRole"), attr("AXTitle"), attr("AXDescription"), attr("AXValue")
        # walk up for a window / app title
        app = None
        try:
            e, win = AXUIElementCopyAttributeValue(el, "AXWindow", None)
            if not e and win is not None:
                e2, wt = AXUIElementCopyAttributeValue(win, "AXTitle", None); app = None if e2 else str(wt)
        except Exception:
            pass
        return {"trusted": True, "role": role, "title": title or desc or "", "value": (val or "")[:60], "window": app or ""}
    except Exception as e:
        return {"trusted": False, "error": repr(e)[:120]}


def ask_owner(kind, what, why, action):
    try:
        body = json.dumps({"kind": "click", "src": what, "why": why, "action": action}).encode()
        req = urllib.request.Request("http://127.0.0.1:8796/pending-click", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return {"ok": False, "error": f"could not file the request: {e}"}


def guarded_click(kind, x, y):
    if not looked_recently():
        out({"ok": False, "error": "look first: take a screenshot with look-screen.sh (it must be under 45 s old) so you click what is really there"})
    info = under(x, y)
    if not info.get("trusted"):
        out({"ok": False, "error": "the accessibility API is not available to this process (System Settings > Privacy & Security > Accessibility for the app that launched the agent); clicks are refused without it"})
    label = f"{info.get('role') or '?'} '{info.get('title') or ''}' in '{info.get('window') or ''}'"
    if RISKY.search(info.get("title") or "") or RISKY.search(info.get("value") or ""):
        r = ask_owner("click", label, f"{kind} at {x},{y}", {"kind": kind, "x": x, "y": y})
        log(f"{kind} at {x},{y} on {label}: RISKY -> approval {r.get('pending', r.get('error'))}")
        out({"ok": bool(r.get("ok")), "pending": r.get("pending"), "done": f"that is a risky control ({label}); a request is waiting for the owner's approval", "error": r.get("error", "")})
    ok, s = cli({"click": "c", "double": "dc", "right": "rc"}[kind] + f":{x},{y}")
    log(f"{kind} at {x},{y} on {label}: {'ok' if ok else s}")
    out({"ok": ok, "done": f"{kind}ed {label}", "error": "" if ok else s})


def main(a):
    cmd = a[0] if a else "help"
    if cmd == "where":
        x, y = pointer(); out({"ok": True, "x": x, "y": y})
    if cmd == "under":
        x, y = (int(a[1]), int(a[2])) if len(a) > 2 else pointer(); out({"ok": True, **under(x, y)})
    if cmd == "move":
        ok, s = cli(f"m:{a[1]},{a[2]}"); log(f"move {a[1]},{a[2]}"); out({"ok": ok, "error": "" if ok else s})
    if cmd in ("click", "double", "right"):
        x, y = (int(a[1]), int(a[2])) if len(a) > 2 else pointer(); guarded_click(cmd, x, y)
    if cmd == "drag":
        if not looked_recently():
            out({"ok": False, "error": "look first (look-screen.sh within 45 s)"})
        info = under(int(a[1]), int(a[2]))
        if RISKY.search(info.get("title") or ""):
            out({"ok": False, "error": f"refusing to drag a risky control: {info.get('title')}"})
        ok, s = cli(f"dd:{a[1]},{a[2]}", f"du:{a[3]},{a[4]}"); log(f"drag {a[1]},{a[2]} -> {a[3]},{a[4]}: {ok}"); out({"ok": ok, "error": "" if ok else s})
    if cmd == "type":
        text = " ".join(a[1:])
        info = under(*pointer())
        if (info.get("role") or "") == "AXSecureTextField" or re.search(r"password|passcode|pin", (info.get("title") or "") + (info.get("window") or ""), re.I):
            out({"ok": False, "error": "that looks like a password field; the agent never types secrets"})
        ok, s = cli(f"t:{text}"); log(f"type {len(text)} chars into {info.get('role')} '{info.get('title')}'"); out({"ok": ok, "error": "" if ok else s})
    if cmd == "key":
        k = a[1].lower().replace("option", "alt").replace("command", "cmd").replace("control", "ctrl")
        if k in BLOCKED_KEYS:
            log(f"key {k}: BLOCKED"); out({"ok": False, "error": f"{k} is a destructive shortcut; refused"})
        if "+" in k:
            mods, key = k.rsplit("+", 1); ok, s = cli(f"kd:{mods}", f"t:{key}" if len(key) == 1 else f"kp:{key}", f"ku:{mods}")
        else:
            ok, s = cli(f"kp:{k}")
        log(f"key {k}: {ok}"); out({"ok": ok, "error": "" if ok else s})
    print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
