#!/usr/bin/env python3
"""the agent's pulse: the things that happen without being asked. Runs beside the
voice line (started by start.sh) and speaks to the agent through the console's pipe.

  reminders     the reminders document in data/troi.db, written by remind.sh; each fires
                once at its time as "(reminder: ...)" and the agent says it out loud
  github watch  every 3 minutes, the newest CI run on main in each repo of your GitHub org
                branch; a run that finished since the last check is reported
                (failures always, successes only if the previous state failed)
  morning brief at console.json "brief_time" (default 08:00), once a day, only
                if the voice line is up; the agent runs its Morning Brief job

Stdlib only. Never deletes anything but its own fired reminders.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import db as _DB  # noqa: E402  (small documents live in troi.db)

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
FIFO = HERE / ".typed"
SETTINGS = P.CONFIG
REMINDERS = _DB.doc("reminders")
STATE = _DB.doc("pulse-state")
LOG = HOME / "backtalk" / "logs" / "backtalk.log"
VOICE_STATE = HOME / "backtalk" / ".voice_state"
try:
    GH_ORG = json.loads(P.CONFIG.read_text()).get("github_org", "")
except Exception:
    GH_ORG = ""
GH_EVERY = 180
PATH = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")


def log(line):
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass


def jload(p, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def _turn_in_flight():
    b = HOME / "backtalk" / ".voice_busy"
    try:
        return b.exists() and time.time() - b.stat().st_mtime < 900
    except OSError:
        return False


def busy():
    if _turn_in_flight():
        return True
    try:
        return VOICE_STATE.read_text().strip() in ("speaking", "thinking", "listening")
    except Exception:
        return False


def tell(text, phone=None):
    """To the voice line if it is up; otherwise (or additionally) to Telegram."""
    try:
        fd = os.open(str(FIFO), os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (" ".join(text.split()) + "\n").encode()); os.close(fd)
        ok = True
    except OSError:
        ok = False
    if phone and (not ok or phone == "always"):
        try:
            subprocess.run([sys.executable, str(HERE / "telegram.py"), "send", phone if phone != "always" else text],
                           timeout=30, capture_output=True)
        except Exception:
            pass
    return ok


def gh(args):
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=40,
                             env={**os.environ, "PATH": PATH})
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None


def check_reminders():
    items = jload(REMINDERS, [])
    now = time.time()
    due = [r for r in items if r.get("at", 0) <= now]
    if not due:
        return
    if busy():
        return                       # try again next tick, after the agent finishes
    for r in due:
        log(f"[pulse]  reminder due: {r.get('text')}")
        tell(f"(reminder, set by the owner earlier: \"{r.get('text')}\". Say it to him now in one short sentence, as a reminder.)",
             phone=f"Reminder: {r.get('text')}")
    keep = [r for r in items if r not in due]
    REMINDERS.write_text(json.dumps(keep, indent=2))


def check_github(state):
    if not GH_ORG:
        return
    repos = gh(["repo", "list", GH_ORG, "--json", "name", "-q", "[.[].name]"]) or []
    seen = state.setdefault("gh", {})
    for repo in repos:
        runs = gh(["run", "list", "-R", f"{GH_ORG}/{repo}", "-b", "main", "-L", "1",
                   "--json", "databaseId,status,conclusion,name,headSha,displayTitle"]) or []
        if not runs:
            continue
        r = runs[0]
        key = str(r["databaseId"])
        prev = seen.get(repo, {})
        if r["status"] != "completed":
            continue
        if prev.get("id") == key:
            continue                 # already reported / already seen
        first = not prev
        seen[repo] = {"id": key, "conclusion": r["conclusion"]}
        if first:
            continue                 # baseline only, no announcement on startup
        if r["conclusion"] == "failure" or (prev.get("conclusion") == "failure" and r["conclusion"] == "success"):
            what = "FAILED" if r["conclusion"] == "failure" else "is green again"
            log(f"[pulse]  github: {repo} {r['name']} {what}")
            tell(f"(github watch: on {GH_ORG}/{repo}, the workflow \"{r['name']}\" on main {what}: \"{r.get('displayTitle','')}\". "
                 f"Tell the owner in one sentence. If it FAILED, run your CI Failure Response job from the vault: read the failing log, diagnose, "
                 f"and if the fix is small open a PR for it, then report on Telegram; never merge without green CI and the owner's word.)",
                 phone=f"GitHub: {repo} \u2014 {r['name']} on main {what}: {r.get('displayTitle','')}")


SERVER_EVERY = 900          # the server watch: every 15 minutes, read-only over SSH (servers.py)
CAL_EVERY = 60              # the calendar: a heads-up 15 minutes before each event (agenda.py)


def check_servers(state):
    """Compare this round's issues with the last; speak only what changed. The first round is a baseline."""
    try:
        r = subprocess.run([sys.executable, str(HERE / "servers.py"), "check", "--json"], capture_output=True, text=True, timeout=150)
        d = json.loads(r.stdout)
    except Exception as e:
        log(f"[pulse]  servers: check failed ({e!r})"); return
    if not d.get("servers"):
        return
    now_issues = set(d.get("issues", []))
    if state.get("servers") is None:
        state["servers"] = sorted(now_issues); log(f"[pulse]  servers: baseline, {len(now_issues)} open issue(s)"); return
    prev = set(state["servers"]); new, fixed = sorted(now_issues - prev), sorted(prev - now_issues)
    state["servers"] = sorted(now_issues)
    if not new and not fixed:
        return
    log(f"[pulse]  servers: new {new} fixed {fixed}")
    tell(f"(server watch: NEW: {'; '.join(new) or 'none'}. RESOLVED: {'; '.join(fixed) or 'none'}. Tell the owner in one or two sentences. "
         f"For a new issue run your Server Maintenance job: look first, read-only, then propose the fix; nothing changes on a server without the owner's go.)",
         phone="Servers: " + ("NEW: " + "; ".join(new) if new else "") + (" RESOLVED: " + "; ".join(fixed) if fixed else ""))


def check_calendar(state):
    """Events starting within 16 minutes, announced once each."""
    try:
        r = subprocess.run([sys.executable, str(HERE / "agenda.py"), "soon", "16"], capture_output=True, text=True, timeout=75)
        evs = json.loads(r.stdout or "[]")
    except Exception as e:
        log(f"[pulse]  calendar: failed ({e!r})"); return
    told = state.setdefault("cal_told", [])
    for e in evs:
        key = e["start"] + "|" + e["title"]
        if key in told:
            continue
        told.append(key); del told[:-60]
        start = e["start"][11:16]
        log(f"[pulse]  calendar: {e['title']} at {start}")
        tell(f"(calendar: \"{e['title']}\" starts at {start}" + (f" on the {e['calendar']} calendar" if e.get('calendar') else "")
             + (f", call link {e['link']}" if e.get('link') else "") + ". Tell the owner in one sentence, offer to prep them (your Meeting Prep & Notes job), "
             "and to record it when it starts: meeting.py start with no name takes the event's title.)",
             phone=f"Calendar: {e['title']} at {start}" + (f" \u2014 {e['link']}" if e.get('link') else ""))



def check_nightly(state):
    """03:00 housekeeping (logs, old captures); 03:30 compact the shared session if the voice line is up and idle."""
    today = date.today().isoformat(); now = datetime.now().strftime("%H:%M")
    if state.get("housekept") != today and "03:00" <= now <= "05:00":
        state["housekept"] = today
        try:
            out = subprocess.run([str(HERE / "housekeeping.sh")], capture_output=True, text=True, timeout=300).stdout.strip()
            log("[pulse]  housekeeping: " + (out.replace("\n", " | ")[:300] or "nothing to do"))
        except Exception as e:
            log(f"[pulse]  housekeeping failed: {e!r}")
    if state.get("compacted") != today and "03:30" <= now <= "05:30" and FIFO.exists() and not busy():
        state["compacted"] = today
        log("[pulse]  nightly compaction of the shared session")
        tell("compact the session")


def check_report(state):
    """The end-of-day report at console.json "report_time" (default 18:30), once a day: report.py builds
    the HTML and the PDF, asks the brain for the narrative, and sends the PDF to Telegram."""
    cfg = jload(SETTINGS, {})
    if cfg.get("report_enabled") is False:
        return
    t = cfg.get("report_time", "18:30")
    today = date.today().isoformat()
    if state.get("report_done") == today:
        return
    now = datetime.now().strftime("%H:%M")
    if now >= t and now <= "23:00" and not busy():
        state["report_done"] = today
        log("[pulse]  end-of-day report")
        subprocess.Popen([sys.executable, str(HERE / "report.py")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_brief(state):
    cfg = jload(SETTINGS, {})
    if cfg.get("brief_enabled") is False:
        return
    t = cfg.get("brief_time", "08:00")
    today = date.today().isoformat()
    if state.get("brief_done") == today:
        return
    now = datetime.now().strftime("%H:%M")
    if now >= t and now <= "11:00" and not busy():
        state["brief_done"] = today
        log("[pulse]  morning brief")
        tell("(scheduled morning brief: it is time. Run your Morning Brief job now and speak it.)")


def main():
    state = jload(STATE, {})
    last_gh = 0.0
    last_srv = last_cal = 0.0
    while True:
        try:
            if True:
                check_reminders()
                if time.time() - last_gh > GH_EVERY:
                    last_gh = time.time()
                    check_github(state)
                if time.time() - last_srv > SERVER_EVERY:
                    last_srv = time.time(); check_servers(state)
                if time.time() - last_cal > CAL_EVERY:
                    last_cal = time.time(); check_calendar(state)
                check_brief(state)
                check_report(state)
                check_nightly(state)
                STATE.write_text(json.dumps(state))
        except Exception as e:
            log(f"[pulse]  error: {e!r}")
        time.sleep(5)


if __name__ == "__main__":
    main()
