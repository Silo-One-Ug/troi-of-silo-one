#!/usr/bin/env python3
"""the agent's continuous eyes. Runs beside the voice line (started by start.sh).

Reads console.json every second. When "eyes" is "every" or "watch" it keeps the
camera open (imagesnap time-lapse, one frame every 2 s) and keeps
data/cache/live.jpg pointing at the newest frame. voice.py attaches that
frame to each request in "every" mode.

In "watch" mode it also compares frames: a large, settled change in the view
(someone arrives or leaves, something is held up) is reported to the agent as
a typed line through the console's pipe, so the agent can say a word about it.
At most one report per WATCH_COOLDOWN seconds, and none while the agent is talking.

Frames are throwaway: only the last ~2 minutes are kept. Camera light is on
whenever a mode is active, which is the honest signal that the agent is looking.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
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
SETTINGS = P.CONFIG
LOOKS = P.CACHE                              # live frames are throwaway: never kept
LIVE_DIR = P.CACHE / "live"
FIFO = HERE / ".typed"
STATE = HOME / "backtalk" / ".voice_state"
LOG = HOME / "backtalk" / "logs" / "backtalk.log"
INTERVAL = 2.0
KEEP_S = 120
WATCH_THRESHOLD = 0.12     # mean abs pixel change (0..1) that counts as "the view changed"
WATCH_SETTLE = 3           # consecutive changed frames before we speak (not a passing hand)
WATCH_COOLDOWN = 60
PATH = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")


def log(line):
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass


def lid_closed():
    try:
        out = subprocess.run(["ioreg", "-r", "-k", "AppleClamshellState", "-d", "4"], capture_output=True, text=True, timeout=5).stdout
        return '"AppleClamshellState" = Yes' in out
    except Exception:
        return False


def mode():
    try:
        m = json.loads(SETTINGS.read_text()).get("eyes", "off")
        if m in ("every", "watch") and lid_closed():
            return "off"                              # lid closed: the camera sees nothing, save the battery
        return m if m in ("every", "watch") else "off"
    except Exception:
        return "off"


def newest():
    frames = sorted(LIVE_DIR.glob("frame-*.jpg"))
    return frames[-1] if frames else None


def prune():
    now = time.time()
    for f in LIVE_DIR.glob("frame-*.jpg"):
        if now - f.stat().st_mtime > KEEP_S:
            try:
                f.unlink()
            except OSError:
                pass


def gray(path):
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        im = im.convert("L").resize((64, 36))
        return np.asarray(im, dtype="float32") / 255.0


def speaking():
    try:
        return STATE.read_text().strip() in ("speaking", "thinking", "listening")
    except Exception:
        return False


def tell_agent(text):
    try:
        fd = os.open(str(FIFO), os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (text + "\n").encode()); os.close(fd)
        return True
    except OSError:
        return False


def main():
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    cam = None
    last = None
    changed_run = 0
    last_report = 0.0
    baseline = None
    try:
        while True:
            m = mode()
            if m != "off" and cam is None:
                for f in LIVE_DIR.glob("frame-*.jpg"):
                    f.unlink()
                cam = subprocess.Popen(["imagesnap", "-q", "-w", "1", "-t", str(INTERVAL), "frame.jpg"],
                                       cwd=LIVE_DIR, env={**os.environ, "PATH": PATH},
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log(f"[eyes]   camera on ({m})")
                baseline = None
            if m == "off" and cam is not None:
                cam.terminate(); cam = None
                log("[eyes]   camera off")
                try:
                    (LOOKS / "live.jpg").unlink()
                except OSError:
                    pass
            if cam is not None and cam.poll() is not None:
                log("[eyes]   camera process died, restarting")
                cam = None
                time.sleep(2)
                continue
            f = newest() if cam is not None else None
            if f is not None and f != last and time.time() - f.stat().st_mtime > 0.3:
                last = f
                tmp = LOOKS / "live.jpg.tmp"
                try:
                    os.link(f, tmp)
                    os.replace(tmp, LOOKS / "live.jpg")
                except OSError:
                    pass
                if m == "watch":
                    try:
                        g = gray(f)
                        if baseline is None:
                            baseline = g
                        else:
                            diff = float(abs(g - baseline).mean())
                            if diff > WATCH_THRESHOLD:
                                changed_run += 1
                            else:
                                changed_run = 0
                            if changed_run >= WATCH_SETTLE:
                                baseline = g
                                changed_run = 0
                                if time.time() - last_report > WATCH_COOLDOWN and not speaking():
                                    last_report = time.time()
                                    log(f"[eyes]   view changed (diff {diff:.2f}), telling the agent")
                                    tell_agent(f"(camera watch: the view changed noticeably. Read {f} and, only if there is "
                                               f"something worth a word to the owner, say ONE short sentence about it. "
                                               f"If it is nothing, reply with exactly: Noted.)")
                    except Exception as e:
                        log(f"[eyes]   watch error: {e!r}")
                prune()
            time.sleep(1.0)
    finally:
        if cam is not None:
            cam.terminate()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    main()
