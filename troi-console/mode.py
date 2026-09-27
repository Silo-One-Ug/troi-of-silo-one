#!/usr/bin/env python3
"""Modes: a stance the agent takes, and the switches that go with it, in one word (Silo One, 2026-09-27).

  mode.py list                 the modes and what each sets
  mode.py <name> [--dry]       take the stance: the brain and its effort, speech, the room's sound, quiet hours, the console's
                               view; the stance itself reaches the agent as a line of context, and it works that way until the
                               mode ends. --dry says what would change.
  mode.py off [--dry]          the resting state: whatever the mode changed goes back as it was
  mode.py status               which mode is on, since when

The modes are in data/modes.json (the owner's; changed at their word). A mode pulls only the switches that need no
verification: the brain (brain.sh), speech (console.sh speak), the sound (sounds.py), quiet (triage.py quiet), the view
(console.sh view). The microphone and the permissions are protected and stay where they are: a mode never touches them.
Stdlib only.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db as _DB  # noqa: E402
import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
FILE = P.DATA / "modes.json"
STATE = _DB.doc("mode")
FIFO = HERE / ".typed"


def load():
    try:
        d = json.loads(FILE.read_text())
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def sh(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")})
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)[:120]


def tell(text):
    """A line of context to the agent through the voice line's pipe, like the pulse's; quietly nothing when the line is down."""
    try:
        fd = os.open(str(FIFO), os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (" ".join(text.split()) + "\n").encode()); os.close(fd)
        return True
    except OSError:
        return False


def settings():
    try:
        return json.loads(P.CONFIG.read_text())
    except Exception:
        return {}


def current():
    """What the switches are now, for the way back: speech, quiet, the brain's word."""
    cfg = settings()
    code, live = sh([str(HERE / "brain.sh"), "status"], timeout=20)
    return {"speak": "off" if cfg.get("speak") is False else "on", "brain_status": live[:200] if code == 0 else "", "quiet": sh([sys.executable, str(HERE / "triage.py"), "quiet", "status"])[1][:60]}


def apply(name, m, dry):
    done = []; before = current()
    def step(label, args, timeout=60):
        if dry:
            done.append("would " + label); return
        code, out = sh(args, timeout)
        done.append(label if code == 0 else f"{label}: {out[:80] or 'refused'}")
    if m.get("brain") == "deep":
        step(f"the deep brain at {m.get('effort', 'high')} effort", [str(HERE / "brain.sh"), "for", f"the {m.get('name', name)} mode", "--deep", "--effort", m.get("effort", "high")])
    elif m.get("brain") == "fast":
        step("the fast brain", [str(HERE / "brain.sh"), "back"])
    if m.get("speak") in ("on", "off"):
        step(f"speech {m['speak']}", [str(HERE / "console.sh"), "speak", m["speak"]])
    if m.get("sound") == "stop":
        step("the sounds off", [sys.executable, str(HERE / "sounds.py"), "stop"])
    elif m.get("sound"):
        step(f"the {m['sound']} sound", [sys.executable, str(HERE / "sounds.py"), "play", m["sound"]], timeout=90)
    if m.get("quiet") in ("on", "off"):
        step(f"quiet {m['quiet']}", [sys.executable, str(HERE / "triage.py"), "quiet", m["quiet"], *(["12h"] if m["quiet"] == "on" else [])])
    if m.get("view"):
        step(f"the {m['view']} view", [str(HERE / "console.sh"), "view", m["view"]])
    if not dry:
        STATE.write_text(json.dumps({"mode": name, "since": time.time(), "before": before, "set": {k: m.get(k) for k in ("brain", "speak", "sound", "quiet", "view")}}))
        tell(f"(mode: {m.get('name', name)} from now on. {m.get('stance', '')} Say in one line that you are in {m.get('name', name)} mode; \"mode off\" ends it.)")
    return done


def undo(dry):
    st = state()
    if not st.get("mode"):
        print("no mode is on"); return 0
    s = st.get("set") or {}; b = st.get("before") or {}
    done = []
    def step(label, args, timeout=60):
        if dry:
            done.append("would " + label); return
        code, out = sh(args, timeout)
        done.append(label if code == 0 else f"{label}: {out[:80] or 'refused'}")
    if s.get("brain") == "deep":
        step("the fast brain again", [str(HERE / "brain.sh"), "back"])
    if s.get("speak") and b.get("speak") and s["speak"] != b["speak"]:
        step(f"speech {b['speak']} again", [str(HERE / "console.sh"), "speak", b["speak"]])
    if s.get("sound") and s["sound"] != "stop":
        step("the sound off", [sys.executable, str(HERE / "sounds.py"), "stop"])
    if s.get("quiet") == "on" and "not quiet" in (b.get("quiet") or "not quiet"):
        step("quiet off", [sys.executable, str(HERE / "triage.py"), "quiet", "off"])
    if s.get("view") and s["view"] != "conversation":
        step("the conversation view", [str(HERE / "console.sh"), "view", "face"])
    if not dry:
        STATE.write_text(json.dumps({}))
        tell(f"(mode off: the {st.get('mode')} stance ends; back to your usual self. Say so in one line.)")
    print(f"{'would end' if dry else 'ended'} the {st.get('mode')} mode: " + ("; ".join(done) or "nothing to put back"))
    return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    dry = "--dry" in a; a = [x for x in a if x != "--dry"]
    modes = load()
    if a[0] == "list":
        if not modes:
            print("no modes in data/modes.json"); return 0
        for k, m in modes.items():
            bits = [f"brain {m.get('brain')}" + (f" ({m.get('effort')})" if m.get("brain") == "deep" else ""), f"speech {m.get('speak')}", f"sound {m.get('sound') or 'as is'}", f"quiet {m.get('quiet')}", f"view {m.get('view')}"]
            print(f"{k:<12} {m.get('name', k)}: {', '.join(bits)}\n{'':<13}{m.get('stance', '')[:150]}")
        return 0
    if a[0] == "status":
        st = state()
        print(f"{st['mode']} mode, since {datetime.fromtimestamp(st['since']):%H:%M}" if st.get("mode") else "no mode: the resting state"); return 0
    if a[0] == "off":
        return undo(dry)
    name = a[0].lower(); m = modes.get(name)
    if not m:
        print(f"no mode called {name}; mode.py list"); return 2
    if state().get("mode") and state()["mode"] != name and not dry:
        undo(False)                                                   # one stance at a time: the last one is put back first
    done = apply(name, m, dry)
    print(f"{'would take' if dry else 'took'} the {m.get('name', name)} stance: " + "; ".join(done))
    if not dry:
        print(f"the stance reached the agent: {m.get('stance', '')[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
