#!/usr/bin/env python3
"""the agent's server watch: read-only health checks over SSH, for the pulse and on request. Stdlib only.

  servers.py list                          the servers in data/servers.json
  servers.py add <name> <ssh-host> [role]  add one (ssh-host is an alias or address from ~/.ssh/config)
  servers.py check [name] [--json]         check all (or one): load, disk, memory, failed services,
                                           containers, pending updates, reboot needed. Prints a table,
                                           or JSON with an "issues" list for the pulse.

Everything is read-only (ssh -o BatchMode=yes, key auth only; a server that asks for a password just
shows as unreachable). Fixes are the agent's Server Maintenance job, one at a time, with the owner's go.
Thresholds live in data/servers.json "thresholds": disk_pct (80), load_per_core (1.5), mem_pct (90).
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
CONF = P.DATA / "servers.json"
DEFAULT_THRESHOLDS = {"disk_pct": 80, "load_per_core": 1.5, "mem_pct": 90}

# one shell script, run on the server, prints tagged lines; every command is optional and read-only
PROBE = r'''
echo "host=$(hostname)"
echo "cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)"
echo "load=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || uptime | sed 's/.*load average[s]*: //')"
echo "up=$(uptime -p 2>/dev/null || uptime | sed 's/.*up //; s/,.*//')"
df -P -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | awk 'NR>1 && $6!~"^/(boot|snap|run)" {print "disk="$6" "$5" "$4}'
free -m 2>/dev/null | awk '/^Mem:/ {printf "mem=%d %d\n", $3, $2}'
command -v systemctl >/dev/null && echo "failed=$(systemctl --failed --no-legend --plain 2>/dev/null | awk '{print $1}' | tr '\n' ',' | sed 's/,$//')"
command -v docker >/dev/null && docker ps -a --format '{{.Names}}|{{.Status}}' 2>/dev/null | sed 's/^/docker=/'
[ -f /var/run/reboot-required ] && echo "reboot=yes"
command -v apt-get >/dev/null && [ -r /var/lib/apt/periodic/update-success-stamp ] && echo "updates=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst ')"
'''


def load():
    try: return json.loads(CONF.read_text())
    except Exception: return {"servers": [], "thresholds": dict(DEFAULT_THRESHOLDS)}


def save(d):
    CONF.write_text(json.dumps(d, indent=2))


def probe(server, timeout=40):
    host = server["host"]
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new",
                        host, "sh", "-s"], input=PROBE, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 and "host=" not in r.stdout:
        return {"name": server["name"], "host": host, "reachable": False, "error": (r.stderr.strip().splitlines() or ["ssh failed"])[-1][:160]}
    d = {"name": server["name"], "host": host, "role": server.get("role", ""), "reachable": True, "disks": [], "docker": [], "failed": []}
    for line in r.stdout.splitlines():
        if "=" not in line: continue
        k, v = line.split("=", 1)
        if k == "disk":
            mnt, pct, avail = v.split()
            if mnt.startswith(("/sys", "/proc", "/dev")): continue
            d["disks"].append({"mount": mnt, "pct": int(pct.rstrip("%")), "avail_mb": int(avail) // 1024})
        elif k == "up": d["up"] = v[3:] if v.startswith("up ") else v
        elif k == "mem":
            used, total = map(int, v.split()); d["mem_pct"] = round(100 * used / max(total, 1)); d["mem_total_mb"] = total
        elif k == "failed": d["failed"] = [x for x in v.split(",") if x]
        elif k == "docker": name, status = v.split("|", 1); d["docker"].append({"name": name, "status": status})
        elif k == "load": d["load"] = [float(x) for x in v.replace(",", " ").split()[:3]]
        elif k == "cores": d["cores"] = int(v or 1)
        elif k in ("host", "reboot", "updates"): d[k] = v
    return d


def issues(d, th):
    out = []
    if not d.get("reachable"): return [f"unreachable ({d.get('error', '')})"]
    for disk in d["disks"]:
        if disk["pct"] >= th["disk_pct"]: out.append(f"disk {disk['mount']} {disk['pct']}% full ({disk['avail_mb']} MB left)")
    if d.get("load") and d["load"][1] > th["load_per_core"] * max(d.get("cores", 1), 1):
        out.append(f"load {d['load'][1]:.1f} on {d.get('cores', 1)} cores")
    if d.get("mem_pct", 0) >= th["mem_pct"]: out.append(f"memory {d['mem_pct']}% used")
    for u in d["failed"]: out.append(f"service {u} failed")
    for c in d["docker"]:
        s = c["status"].lower()
        if "restarting" in s or ("exited" in s and "(0)" not in s) or "unhealthy" in s: out.append(f"container {c['name']}: {c['status']}")
    if d.get("reboot") == "yes": out.append("reboot required")
    return out


def check(names=None, as_json=False):
    cfg = load(); th = {**DEFAULT_THRESHOLDS, **cfg.get("thresholds", {})}
    servers = [s for s in cfg["servers"] if not names or s["name"] in names]
    if not servers:
        print("no servers configured (servers.py add <name> <ssh-host> [role])" if not as_json else json.dumps({"servers": [], "issues": []})); return
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda s: probe(s), servers))
    for d in results: d["issues"] = issues(d, th)
    if as_json:
        print(json.dumps({"servers": results, "issues": [f"{d['name']}: {i}" for d in results for i in d["issues"]]})); return
    for d in sorted(results, key=lambda x: (x["reachable"], -len(x["issues"]))):
        if not d["reachable"]:
            print(f"{d['name']:<18} UNREACHABLE  {d.get('error', '')}"); continue
        worst = max((x["pct"] for x in d["disks"]), default=0)
        ld = f"{d['load'][1]:.1f}/{d.get('cores', '?')}c" if d.get("load") else "?"
        print(f"{d['name']:<18} {'OK ' if not d['issues'] else 'ATTENTION'}  up {d.get('up', '?')}, load {ld}, disk {worst}%, mem {d.get('mem_pct', '?')}%, "
              f"{len(d['docker'])} containers" + (f", {d['updates']} updates" if d.get("updates") else ""))
        for i in d["issues"]: print(f"{'':<18}   - {i}")


def main(a):
    c = a[0] if a else "help"
    if c == "list":
        cfg = load()
        for s in cfg["servers"]: print(f"{s['name']:<18} {s['host']:<28} {s.get('role', '')}")
        print("no servers yet" if not cfg["servers"] else "")
    elif c == "add" and len(a) >= 3:
        cfg = load(); cfg["servers"] = [s for s in cfg["servers"] if s["name"] != a[1]]
        cfg["servers"].append({"name": a[1], "host": a[2], "role": " ".join(a[3:])}); save(cfg); print(f"added {a[1]} ({a[2]})")
    elif c == "check":
        rest = [x for x in a[1:] if x != "--json"]; check(rest or None, "--json" in a)
    else: print(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
