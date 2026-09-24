#!/usr/bin/env python3
"""Applications for the console and for the agent: list (with icons), running state, open, quit."""
import json, os, plistlib, subprocess, sys, time
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
CACHE = P.CACHE / "icons"
DIRS = [Path("/Applications"), Path.home() / "Applications", Path("/System/Applications"), Path("/System/Applications/Utilities")]


def running_names():
    r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'],
                       capture_output=True, text=True, timeout=15)
    return set(x.strip() for x in r.stdout.split(",") if x.strip())


def icon_for(app: Path):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (app.stem.replace("/", "_") + ".png")
    if out.exists():
        return out
    try:
        info = plistlib.load(open(app / "Contents" / "Info.plist", "rb"))
        icns = info.get("CFBundleIconFile") or info.get("CFBundleIconName") or "AppIcon"
        if not icns.endswith(".icns"):
            icns += ".icns"
        src = app / "Contents" / "Resources" / icns
        if not src.exists():
            cands = list((app / "Contents" / "Resources").glob("*.icns"))
            if not cands:
                return None
            src = cands[0]
        subprocess.run(["sips", "-s", "format", "png", "-Z", "128", str(src), "--out", str(out)], capture_output=True, timeout=20)
        return out if out.exists() else None
    except Exception:
        return None


def list_apps():
    apps, seen = [], set()
    for d in DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix != ".app" or p.name in seen:
                continue
            seen.add(p.name)
            cat = "Other"
            try:
                info = plistlib.load(open(p / "Contents" / "Info.plist", "rb"))
                raw = str(info.get("LSApplicationCategoryType", "")).replace("public.app-category.", "")
                cat = {"developer-tools": "Developer", "productivity": "Productivity", "utilities": "Utilities", "social-networking": "Social", "music": "Music",
                       "video": "Video", "photography": "Photo", "graphics-design": "Design", "entertainment": "Entertainment", "business": "Business",
                       "education": "Education", "games": "Games", "reference": "Reference", "news": "News", "finance": "Finance", "lifestyle": "Lifestyle",
                       "medical": "Medical", "travel": "Travel", "weather": "Weather", "healthcare-fitness": "Health"}.get(raw, raw.replace("-", " ").title() if raw else ("System" if "System" in str(d) else "Other"))
            except Exception:
                cat = "System" if "System" in str(d) else "Other"
            apps.append({"name": p.stem, "path": str(p), "where": str(d), "category": cat})
    return apps


def state():
    run = running_names()
    apps = list_apps()
    for a in apps:
        a["running"] = a["name"] in run
        ic = icon_for(Path(a["path"]))
        a["icon"] = str(ic) if ic else None
    apps.sort(key=lambda a: (not a["running"], a["name"].lower()))
    return apps


def find(name):
    n = name.lower().strip()
    apps = list_apps()
    for a in apps:
        if a["name"].lower() == n:
            return a
    for a in apps:
        if n in a["name"].lower():
            return a
    return None


def do(op, name):
    a = find(name)
    if not a:
        return {"ok": False, "error": f"no application called {name!r}"}
    if op == "open":
        r = subprocess.run(["open", "-a", a["path"]], capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "done": f"opened {a['name']}", "error": r.stderr.strip()}
    if op == "focus":
        subprocess.run(["osascript", "-e", f'tell application "{a["name"]}" to activate'], capture_output=True, timeout=15)
        return {"ok": True, "done": f"{a['name']} is in front"}
    if op == "quit":
        r = subprocess.run(["osascript", "-e", f'tell application "{a["name"]}" to quit'], capture_output=True, text=True, timeout=20)
        return {"ok": r.returncode == 0, "done": f"asked {a['name']} to quit (it may ask you to save)", "error": r.stderr.strip()[:200]}
    if op == "kill":
        r = subprocess.run(["pkill", "-x", a["name"]], capture_output=True, text=True, timeout=10)
        return {"ok": r.returncode == 0, "done": f"force-quit {a['name']}", "error": "was not running" if r.returncode else ""}
    return {"ok": False, "error": "unknown operation"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for a in state():
            print(("● " if a["running"] else "  ") + a["name"])
    elif cmd == "running":
        print("\n".join(sorted(running_names())))
    elif cmd in ("open", "quit", "focus", "kill") and len(sys.argv) > 2:
        print(json.dumps(do(cmd, " ".join(sys.argv[2:]))))
    else:
        print("apps.py list | running | open <name> | focus <name> | quit <name> | kill <name>")
