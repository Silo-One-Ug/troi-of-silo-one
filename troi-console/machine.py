#!/usr/bin/env python3
"""The Mac itself, watched (Silo One, 2026-09-27): read-only health of this machine, and the pulse's eye on it.

  machine.py check [--json]      disk free per volume, memory pressure, the load and the hot processes, the battery and the
                                 power, the thermal state, uptime, login items, when Time Machine last ran
  machine.py why-slow            the same, told as a diagnosis: what is eating the CPU and the memory right now

The pulse runs the check every fifteen minutes and speaks only through the triage: under 10 GB free on the startup disk
is action, under 3 GB urgent; a process over 90% of a core for two rounds is action; critical memory pressure is action;
the battery under 15% and unplugged is action; a thermal state of "heavy" or worse is action. Everything here reads;
nothing is changed. Stdlib and the Mac's own tools (df, vm_stat, memory_pressure, ps, pmset, uptime, tmutil, osascript).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DISK_ACTION_GB = 10
DISK_URGENT_GB = 3
CPU_HOT = 90.0
BATTERY_LOW = 15


def run(args, timeout=20):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/sbin:/sbin:" + os.environ.get("PATH", "")})
        return r.stdout if r.returncode == 0 else (r.stdout + r.stderr)
    except Exception:
        return ""


def disks():
    out = []
    seen = set()
    for m in ("/", "/Volumes"):
        paths = [m] if m == "/" else [os.path.join(m, d) for d in (os.listdir(m) if os.path.isdir(m) else []) if not d.startswith(".")]
        for p in paths:
            try:
                st = os.statvfs(p)
            except OSError:
                continue
            total = st.f_frsize * st.f_blocks; free = st.f_frsize * st.f_bavail
            key = (total, free)                                        # APFS volumes of one container share their space: one line for them
            if key in seen or total < 1e9:
                continue
            seen.add(key)
            out.append({"path": p, "total_gb": round(total / 1e9, 1), "free_gb": round(free / 1e9, 1), "used_pct": round(100 * (1 - free / total)) if total else 0})
    return out


def memory():
    d = {}
    mp = run(["memory_pressure"])
    m = re.search(r"System-wide memory free percentage:\s*(\d+)%", mp)
    if m:
        d["free_pct"] = int(m.group(1))
    d["pressure"] = "critical" if "CRITICAL" in mp.upper() and "free percentage" not in mp.upper().split("CRITICAL")[0][-40:] else ("warn" if re.search(r"warn", mp, re.I) else "normal")
    vm = run(["vm_stat"])
    m = re.search(r"page size of (\d+) bytes", vm); page = int(m.group(1)) if m else 16384
    def pages(name):
        mm = re.search(name + r":\s+(\d+)", vm); return int(mm.group(1)) * page if mm else 0
    d["swapins"] = pages("Swapins"); d["compressed_gb"] = round(pages("Pages occupied by compressor") / 1e9, 1)
    d["free_gb"] = round((pages("Pages free") + pages("Pages inactive")) / 1e9, 1)
    try:
        d["total_gb"] = round(int(run(["sysctl", "-n", "hw.memsize"]).strip()) / 1e9, 1)
    except Exception:
        pass
    return d


def load():
    up = run(["uptime"]).strip()
    m = re.search(r"load averages?:\s*([\d.]+)[, ]+([\d.]+)[, ]+([\d.]+)", up)
    d = {"load": [float(x) for x in m.groups()] if m else [], "cores": os.cpu_count() or 1}
    m = re.search(r"up\s+(.*?),\s+\d+ users?", up)
    d["uptime"] = m.group(1).strip() if m else ""
    return d


def hot(n=6):
    out = run(["ps", "-Axo", "pid=,%cpu=,%mem=,comm="])
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) != 4:
            continue
        try:
            rows.append({"pid": int(parts[0]), "cpu": float(parts[1]), "mem": float(parts[2]), "name": parts[3].rsplit("/", 1)[-1][:40]})
        except ValueError:
            pass
    return {"by_cpu": sorted(rows, key=lambda r: -r["cpu"])[:n], "by_mem": sorted(rows, key=lambda r: -r["mem"])[:n]}


def power():
    out = run(["pmset", "-g", "batt"])
    d = {"source": "battery" if "Battery Power" in out else "ac" if "AC Power" in out else "unknown"}
    m = re.search(r"(\d{1,3})%;\s*([a-z ]+?);", out)
    if m:
        d["battery_pct"] = int(m.group(1)); d["state"] = m.group(2).strip()
    m = re.search(r"(\d+:\d+) remaining", out)
    if m:
        d["remaining"] = m.group(1)
    th = run(["pmset", "-g", "therm"])
    m = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", th)
    d["cpu_speed_limit"] = int(m.group(1)) if m else 100
    m = re.search(r"CPU_Scheduler_Limit\s*=\s*(\d+)", th)
    d["scheduler_limit"] = int(m.group(1)) if m else 100
    d["thermal"] = "heavy" if d["cpu_speed_limit"] < 60 or d["scheduler_limit"] < 60 else "warm" if d["cpu_speed_limit"] < 100 or d["scheduler_limit"] < 100 else "nominal"
    return d


def login_items():
    out = run(["osascript", "-e", 'tell application "System Events" to get the name of every login item'], timeout=15).strip()
    return [x.strip() for x in out.split(",") if x.strip()] if out and "error" not in out.lower() else []


def time_machine():
    out = run(["tmutil", "latestbackup"], timeout=20).strip()
    if not out or "No machine" in out or "not configured" in out.lower():
        return {"configured": False}
    m = re.search(r"(\d{4}-\d{2}-\d{2})-(\d{6})", out)
    return {"configured": True, "last": f"{m.group(1)} {m.group(2)[:2]}:{m.group(2)[2:4]}" if m else out[-40:]}


def check():
    return {"t": time.time(), "disks": disks(), "memory": memory(), "load": load(), "hot": hot(), "power": power(), "login_items": login_items(), "time_machine": time_machine()}


def issues(d, prev=None):
    """(level, text) for what deserves a word; `prev` is the last check, for what must hold two rounds."""
    out = []
    for disk in d.get("disks", []):
        if disk["path"] == "/" or disk["free_gb"] < DISK_ACTION_GB:
            if disk["free_gb"] < DISK_URGENT_GB:
                out.append(("urgent", f"only {disk['free_gb']} GB free on {disk['path']}"))
            elif disk["free_gb"] < DISK_ACTION_GB:
                out.append(("action", f"{disk['free_gb']} GB free on {disk['path']} ({disk['used_pct']}% used)"))
    mem = d.get("memory", {})
    if mem.get("pressure") == "critical":
        out.append(("action", f"memory pressure is critical ({mem.get('free_pct', '?')}% free)"))
    pw = d.get("power", {})
    if pw.get("source") == "battery" and pw.get("battery_pct") is not None and pw["battery_pct"] < BATTERY_LOW:
        out.append(("action", f"battery at {pw['battery_pct']}%, unplugged"))
    if pw.get("thermal") == "heavy":
        out.append(("action", f"the Mac is throttling from heat (CPU speed limit {pw.get('cpu_speed_limit')}%)"))
    if prev:
        now_hot = {r["name"]: r["cpu"] for r in d.get("hot", {}).get("by_cpu", []) if r["cpu"] >= CPU_HOT}
        then_hot = {r["name"]: r["cpu"] for r in prev.get("hot", {}).get("by_cpu", []) if r["cpu"] >= CPU_HOT}
        for name in now_hot:
            if name in then_hot:
                out.append(("action", f"{name} has been at {now_hot[name]:.0f}% of a core for two rounds"))
    return out


def fmt(d):
    lines = []
    for disk in d["disks"]:
        lines.append(f"disk {disk['path']}: {disk['free_gb']} GB free of {disk['total_gb']} ({disk['used_pct']}% used)")
    m = d["memory"]
    lines.append(f"memory: {m.get('free_pct', '?')}% free, pressure {m.get('pressure')}, {m.get('compressed_gb', 0)} GB compressed" + (f", {m.get('total_gb')} GB in all" if m.get("total_gb") else ""))
    l = d["load"]
    if l.get("load"):
        lines.append(f"load: {l['load'][0]} / {l['load'][1]} / {l['load'][2]} on {l['cores']} cores" + (f", up {l['uptime']}" if l.get("uptime") else ""))
    lines.append("hot: " + ", ".join(f"{r['name']} {r['cpu']:.0f}%" for r in d["hot"]["by_cpu"][:4]))
    lines.append("memory hogs: " + ", ".join(f"{r['name']} {r['mem']:.1f}%" for r in d["hot"]["by_mem"][:4]))
    p = d["power"]
    lines.append(f"power: {p.get('source')}" + (f", battery {p.get('battery_pct')}% ({p.get('state')})" if p.get("battery_pct") is not None else "") + (f", {p.get('remaining')} remaining" if p.get("remaining") else "") + f", thermal {p.get('thermal')}")
    lines.append(f"login items: {len(d['login_items'])}" + (": " + ", ".join(d["login_items"][:8]) if d["login_items"] else ""))
    tm = d["time_machine"]
    lines.append("Time Machine: " + (f"last backup {tm['last']}" if tm.get("configured") else "not configured"))
    return "\n".join(lines)


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "check":
        d = check()
        if "--json" in a:
            print(json.dumps(d)); return 0
        print(fmt(d))
        iss = issues(d)
        if iss:
            print("worth a word: " + "; ".join(f"{lvl}: {t}" for lvl, t in iss))
        return 0
    if a[0] == "why-slow":
        d = check(); h = d["hot"]; m = d["memory"]; l = d["load"]
        top = h["by_cpu"][0] if h["by_cpu"] else None
        parts = []
        if top and top["cpu"] >= 50:
            parts.append(f"{top['name']} is taking {top['cpu']:.0f}% of a core")
        if l.get("load") and l["load"][0] > l["cores"]:
            parts.append(f"the load is {l['load'][0]} on {l['cores']} cores")
        if m.get("pressure") in ("warn", "critical"):
            parts.append(f"memory pressure is {m['pressure']} ({m.get('free_pct', '?')}% free, {m.get('compressed_gb', 0)} GB compressed)")
        if d["power"].get("thermal") != "nominal":
            parts.append(f"the Mac is {d['power']['thermal']} and slowing itself")
        for disk in d["disks"]:
            if disk["path"] == "/" and disk["free_gb"] < DISK_ACTION_GB:
                parts.append(f"the startup disk has {disk['free_gb']} GB free")
        print("; ".join(parts) if parts else "nothing stands out: the CPU, the memory, the heat and the disk all look ordinary")
        print("the top of the CPU: " + ", ".join(f"{r['name']} {r['cpu']:.0f}%" for r in h["by_cpu"][:5]))
        print("the top of the memory: " + ", ".join(f"{r['name']} {r['mem']:.1f}%" for r in h["by_mem"][:5]))
        return 0
    print("machine.py check [--json] | why-slow"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
