#!/usr/bin/env python3
"""The agent's pulse: the things that happen without being asked. A background service (launchd,
com.troi-of-silo-one.pulse) that speaks to the agent through the voice line's typing pipe.

  reminders     the reminders document in data/troi.db, written by remind.sh; each fires once at its
                time as "(reminder: ...)" and the agent says it out loud (to Telegram when the voice line is down)
  watches       the owner's watches (watches.py; the "watches" document): a schedule in plain words, a folder, a file,
                a process, a page, the disk, the power, the battery, an app, the Wi-Fi; when one fires, the owner's own
                instruction reaches the agent as a line of context and the agent acts under its rules (or only tells)
  CI watch      every 3 minutes, the newest run on main of each repo of the GitHub orgs and users (github_orgs in the
                settings); a run that finished since the last check is reported (failures always,
                successes only when the previous run failed)
  server watch  every 15 minutes, servers.py checks the servers in data/servers.json; only changes are told
  Grafana watch every minute, grafana.py reads the alert rules' state at the Grafana in data/grafana.json (the token
                is the Keychain item `grafana`); what began firing and what resolved is told, a storm as one line
                (all of these go to Telegram instead when the voice line is down)
  calendar      a heads-up 15 minutes before each event in the Mac's Calendar (agenda.py)
  the Mac       every 15 minutes, machine.py reads the Mac's own health (the startup disk, memory pressure, a process hot
                for two rounds, the battery, the heat); only what is new is said, through the triage
  morning brief at "brief_time" (default 08:00), once a day, only if the voice line is up; the agent runs
                its Morning Brief job
  day's report  at "report_time" (default 18:30), report.py builds the end-of-day report
  nightly       03:00 housekeeping.sh (logs, retention), 03:30 compaction of the shared session

Stdlib only. Never deletes anything but its own fired reminders.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import db as _DB  # noqa: E402  (small documents live in troi.db)
import watches as _W  # noqa: E402  (the owner's watches: "watch this, and when it happens, do that")
import triage as _T  # noqa: E402  (what the pulse says is sorted first: urgent, action, fyi, ignore; quiet hours hold the middle)

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
def github_orgs():
    """The GitHub orgs and users whose repos the CI watch follows: github_orgs in the settings (Routines › CI watch);
    github_org, the old single one, still counts. Read every round, so a change applies at once."""
    try:
        c = json.loads(P.CONFIG.read_text())
    except Exception:
        return []
    orgs = [str(o).strip() for o in (c.get("github_orgs") or []) if str(o).strip()]
    if not orgs and c.get("github_org"):
        orgs = [str(c["github_org"]).strip()]
    return list(dict.fromkeys(orgs))


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


def say(kind, line, phone=None, level=None):
    """Every line to the owner goes through the triage: urgent is spoken and phoned, action spoken when free (held in quiet
    hours), fyi kept for the digest, ignore dropped. `tell` remains the raw channel for the nightly compaction's command."""
    return _T.deliver(None, kind, line, phone=phone, level=level)


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
        say("reminder", f"(reminder, set by the owner earlier: \"{r.get('text')}\". Say it to them now in one short sentence, as a reminder.)",
            phone=f"Reminder: {r.get('text')}")
    keep = [r for r in items if r not in due]
    REMINDERS.write_text(json.dumps(keep, indent=2))


def check_github(state):
    orgs = github_orgs()
    if not orgs:
        return
    seen = state.setdefault("gh", {})
    for org in orgs:
        repos = gh(["repo", "list", org, "--json", "name", "-q", "[.[].name]"]) or []
        for repo in repos:
            full = f"{org}/{repo}"
            runs = gh(["run", "list", "-R", full, "-b", "main", "-L", "1",
                       "--json", "databaseId,status,conclusion,name,headSha,displayTitle"]) or []
            if not runs:
                continue
            r = runs[0]
            key = str(r["databaseId"])
            prev = seen.get(full) or seen.get(repo, {})    # the state was keyed by the repo alone before there were several orgs
            if r["status"] != "completed":
                continue
            if prev.get("id") == key:
                continue                 # already reported / already seen
            first = not prev
            seen[full] = {"id": key, "conclusion": r["conclusion"]}
            if first:
                continue                 # baseline only, no announcement on startup
            if r["conclusion"] == "failure" or (prev.get("conclusion") == "failure" and r["conclusion"] == "success"):
                what = "FAILED" if r["conclusion"] == "failure" else "is green again"
                log(f"[pulse]  github: {full} {r['name']} {what}")
                say("github", f"(github watch: on {full}, the workflow \"{r['name']}\" on main {what}: \"{r.get('displayTitle','')}\". "
                     f"Tell the owner in one sentence. If it FAILED, run your CI Failure Response job from the vault: read the failing log, diagnose, "
                    f"and if the fix is small open a PR for it, then report on Telegram; never merge without green CI and the owner's word.)",
                    phone=f"GitHub: {full} \u2014 {r['name']} on main {what}: {r.get('displayTitle','')}")


SERVER_EVERY = 900          # the server watch: every 15 minutes, read-only over SSH (servers.py)
CAL_EVERY = 60              # the calendar: a heads-up 15 minutes before each event (agenda.py)
GRAFANA_EVERY = 60          # the Grafana watch: every minute, the alert rules' state over https (grafana.py); only changes are told


def check_grafana(state):
    """What began firing and what resolved in Grafana since the last pass (grafana.py watch). Quiet without a token,
    quiet on the first pass (a baseline), and one line per change; a storm is one line."""
    try:
        import grafana as GF
        if not GF.token():
            return
        lines = GF.watch()
    except Exception as e:
        err = str(e)[:160]
        if state.get("grafana_err") != err:
            state["grafana_err"] = err; log(f"[pulse]  grafana: {err}")
        return
    state.pop("grafana_err", None)
    for line in lines:
        log(f"[pulse]  grafana: {line}")
        say("grafana", f"(grafana watch: {line}. Tell the owner in one sentence. For something FIRING run your Server Maintenance job: look first, read-only "
            f"(servers.py check on the node named, grafana.py query for the metric behind it), then propose the fix; nothing changes on a server without the owner's go. "
            f"Keep the board's production panel current if one is up.)",
            phone=f"Grafana: {line}")


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
    say("servers", f"(server watch: NEW: {'; '.join(new) or 'none'}. RESOLVED: {'; '.join(fixed) or 'none'}. Tell the owner in one or two sentences. "
        f"For a new issue run your Server Maintenance job: look first, read-only, then propose the fix; nothing changes on a server without the owner's go.)",
        phone="Servers: " + ("NEW: " + "; ".join(new) if new else "") + (" RESOLVED: " + "; ".join(fixed) if fixed else ""))


MACHINE_EVERY = 900         # the Mac itself: every 15 minutes, read-only (machine.py); only what is new is said, a disk warning at most every six hours


def check_machine(state):
    """The Mac's own health, through the triage: the startup disk, memory pressure, a process hot for two rounds, the battery, the heat."""
    try:
        import machine as MC
        d = MC.check()
        found = MC.issues(d, state.get("machine_prev"))
    except Exception as e:
        log(f"[pulse]  machine: check failed ({e!r})"); return
    state["machine_prev"] = {"hot": {"by_cpu": d.get("hot", {}).get("by_cpu", [])[:6]}}
    told = state.setdefault("machine_told", {})
    now = time.time()
    for lvl, text in found:
        key = re.sub(r"[\d.]+", "#", text)                          # the same warning with other numbers is the same warning
        if now - float(told.get(key) or 0) < 6 * 3600:
            continue
        told[key] = now
        for k in [k for k in told if now - float(told[k]) > 86400]:
            del told[k]
        log(f"[pulse]  machine: {lvl}: {text}")
        say("machine", f"(the Mac itself: {text}. Tell the owner in one sentence; if it is the disk or a hot process, look first (machine.py why-slow, files.py size), "
            f"then propose what to do; nothing is removed or quit without their word.)", phone=f"This Mac: {text}", level=lvl)


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
        say("calendar", f"(calendar: \"{e['title']}\" starts at {start}" + (f" on the {e['calendar']} calendar" if e.get('calendar') else "")
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
        say("brief", "(scheduled morning brief: it is time. Run your Morning Brief job now and speak it.)", level="action")


def main():
    state = jload(STATE, {})
    _T.bind(tell, log)
    last_gh = 0.0; last_mc = time.time() - MACHINE_EVERY + 120     # the first look at the Mac two minutes in, once the rest has settled
    last_srv = last_cal = last_gf = 0.0
    while True:
        try:
            if True:
                check_reminders()
                _W.check(state, lambda line, phone=None, level=None: say("watch", line, phone=phone, level=level), log, busy)   # the owner's watches, through the triage
                if time.time() - last_gh > GH_EVERY:
                    last_gh = time.time()
                    check_github(state)
                if time.time() - last_srv > SERVER_EVERY:
                    last_srv = time.time(); check_servers(state)
                if time.time() - last_cal > CAL_EVERY:
                    last_cal = time.time(); check_calendar(state)
                if time.time() - last_gf > GRAFANA_EVERY:
                    last_gf = time.time(); check_grafana(state)
                if time.time() - last_mc > MACHINE_EVERY:
                    last_mc = time.time(); check_machine(state)
                check_brief(state)
                check_report(state)
                check_nightly(state)
                STATE.write_text(json.dumps(state))
        except Exception as e:
            log(f"[pulse]  error: {e!r}")
        time.sleep(5)


if __name__ == "__main__":
    main()
