#!/usr/bin/env python3
"""The end-of-day report: what changed today, across the machine, GitHub and the vault.

  report.py                 today's report: facts, the agent's narrative, HTML, PDF, then the PDF to Telegram
  report.py --date 2026-09-22
  report.py --no-send       build it, do not send it
  report.py --no-narrative  facts only (no call to the brain)

Facts: commits today in every git repo under the browsable folders (who, what, when), commits and
CI runs today in the GitHub orgs and users the CI watch follows, notes changed in the vault, reminders that fired,
files touched, and how much talking went on. The brain writes the narrative (the same shared
session, so it knows the day). Output: data/blobs/reports/<date>.html, .pdf and .json; the console's Reports
page lists them; the PDF goes to Telegram. Runs on the system python, standard library only.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
REPORTS = P.blob_dir("reports")
SETTINGS = P.CONFIG
PATH = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SKIP = {"node_modules", ".venv", "venv", "vendor", "Library", "__pycache__", ".Trash", "dist", "build", "Pods"}


def settings():
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


def names():
    try:
        agent = json.loads((HOME / "backtalk" / "backtalk.json").read_text()).get("name", "Assistant")
    except Exception:
        agent = "Assistant"
    return agent, settings().get("owner", "the owner")


def run(cmd, timeout=60, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env={**os.environ, "PATH": PATH})
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


# ---------------------------------------------------------------- facts
def git_repos(roots, depth=3):
    """Every git working tree under the browsable folders, a few levels deep."""
    out = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        stack = [(root, 0)]
        while stack:
            d, lvl = stack.pop()
            try:
                kids = [k for k in d.iterdir() if k.is_dir() and not k.name.startswith(".") and k.name not in SKIP]
            except (PermissionError, OSError):
                continue
            if (d / ".git").exists():
                out.append(d); continue
            if lvl < depth:
                stack.extend((k, lvl + 1) for k in kids)
    return sorted(set(out))


def local_commits(day, roots):
    since, until = f"{day} 00:00", f"{day} 23:59:59"
    repos = []
    for repo in git_repos(roots):
        log = run(["git", "log", f"--since={since}", f"--until={until}", "--all", "--date=format:%H:%M", "--format=%h%x1f%an%x1f%ad%x1f%s"], cwd=str(repo), timeout=30)
        commits = [dict(zip(("sha", "author", "time", "subject"), l.split("\x1f"))) for l in log.splitlines() if l.count("\x1f") == 3]
        dirty = len([l for l in run(["git", "status", "--porcelain"], cwd=str(repo), timeout=30).splitlines() if l.strip()])
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo), timeout=10).strip()
        if commits or dirty:
            repos.append({"name": repo.name, "path": str(repo), "branch": branch, "commits": commits[:40], "dirty": dirty})
    repos.sort(key=lambda r: (-len(r["commits"]), r["name"].lower()))
    return repos


def github_activity(day, orgs):
    """Commits and CI runs of the day in every org and user the CI watch follows. "org" stays the label the report shows."""
    orgs = [o for o in (orgs if isinstance(orgs, list) else [orgs]) if o]
    if not orgs:
        return {"org": "", "orgs": [], "repos": [], "runs": []}
    start = f"{day}T00:00:00Z"; end = f"{day}T23:59:59Z"
    repos, runs = [], []
    for org in orgs:
      names_ = []
      try:
        names_ = json.loads(run(["gh", "repo", "list", org, "--json", "name", "-q", "[.[].name]", "-L", "60"], timeout=40) or "[]")
      except Exception:
        pass
      for name_ in names_:
        name = f"{org}/{name_}" if len(orgs) > 1 else name_
        try:
            cs = json.loads(run(["gh", "api", f"/repos/{org}/{name_}/commits?since={start}&until={end}&per_page=50"], timeout=40) or "[]")
        except Exception:
            cs = []
        if isinstance(cs, list) and cs:
            repos.append({"name": name, "commits": [{"sha": c.get("sha", "")[:7], "author": (c.get("commit", {}).get("author", {}) or {}).get("name", "") or (c.get("author") or {}).get("login", ""),
                                                       "time": (c.get("commit", {}).get("author", {}) or {}).get("date", "")[11:16], "subject": (c.get("commit", {}).get("message", "") or "").split("\n")[0][:120]} for c in cs]})
        try:
            rs = json.loads(run(["gh", "run", "list", "-R", f"{org}/{name_}", "-L", "10", "--created", day, "--json", "name,conclusion,status,headBranch,displayTitle"], timeout=40) or "[]")
        except Exception:
            rs = []
        for r in rs if isinstance(rs, list) else []:
            runs.append({"repo": name, "workflow": r.get("name", ""), "branch": r.get("headBranch", ""), "conclusion": r.get("conclusion") or r.get("status", ""), "title": (r.get("displayTitle") or "")[:90]})
    repos.sort(key=lambda r: -len(r["commits"]))
    return {"org": ", ".join(orgs), "orgs": orgs, "repos": repos, "runs": runs}


def vault_changes(day, vault):
    vault = Path(vault)
    if not vault.is_dir():
        return []
    d0 = dt.datetime.strptime(day, "%Y-%m-%d"); t0 = d0.timestamp(); t1 = t0 + 86400
    out = []
    for f in vault.rglob("*.md"):
        if any(part.startswith(".") for part in f.relative_to(vault).parts):
            continue
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        if t0 <= mt < t1:
            rel = f.relative_to(vault)
            out.append({"name": f.stem, "folder": rel.parts[0] if len(rel.parts) > 1 else "", "time": dt.datetime.fromtimestamp(mt).strftime("%H:%M"), "path": str(f)})
    out.sort(key=lambda n: n["time"])
    return out[:60]


def files_touched(day, roots, vault):
    """Files changed today under the browsable folders (Spotlight), leaving out git internals, caches and the vault (listed separately)."""
    d0 = dt.datetime.strptime(day, "%Y-%m-%d"); d1 = d0 + dt.timedelta(days=1)
    q = f"kMDItemContentModificationDate >= $time.iso({d0.strftime('%Y-%m-%dT00:00:00')}) && kMDItemContentModificationDate < $time.iso({d1.strftime('%Y-%m-%dT00:00:00')})"
    out = []
    for root in roots:
        if not Path(root).is_dir() or (vault and str(root) == str(vault)):
            continue
        for line in run(["mdfind", "-onlyin", str(root), q], timeout=60).splitlines():
            p = Path(line)
            if not p.is_file() or "/.git/" in line or any(part in SKIP or part.startswith(".") for part in p.parts):
                continue
            out.append({"name": p.name, "path": line, "time": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%H:%M")})
    out.sort(key=lambda f: f["time"])
    return out[:80]


def day_log(day, agent):
    """From the voice log: turns spoken, reminders fired, builds that changed state, approvals."""
    log = HOME / "backtalk" / "logs" / "backtalk.log"
    n_you = n_agent = 0; reminders = []; builds = []
    if log.exists():
        for line in log.read_text(errors="ignore").splitlines():
            if not line.startswith(day):
                continue
            m = re.match(r"^\S+ (\d\d:\d\d):\d\d \[([^\]]+)\]\s+(.*)$", line)
            if not m:
                continue
            clock, who, text = m.groups()
            if who == "you" and not text.startswith("("):
                n_you += 1
            elif who == agent:
                n_agent += 1
            elif who == "pulse" and text.startswith("reminder due:"):
                reminders.append({"time": clock, "text": text[len("reminder due:"):].strip()})
            elif who == "pulse" and text.startswith("github"):
                builds.append({"time": clock, "text": text[:160]})
    approvals = []
    fslog = P.LOGS / "fs.log"
    if fslog.exists():
        approvals = [l[:160] for l in fslog.read_text(errors="ignore").splitlines() if l.startswith(day) and ("approved" in l or "rejected" in l)][-20:]
    return {"turns_you": n_you, "turns_agent": n_agent, "reminders": reminders, "builds": builds, "approvals": approvals}


def gather(day):
    cfg = settings()
    roots = [r for r in cfg.get("file_roots", []) if Path(r).is_dir()]
    vault = cfg.get("vault", "")
    agent, owner = names()
    return {"date": day, "agent": agent, "owner": owner, "built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "local": local_commits(day, roots), "github": github_activity(day, [str(o).strip() for o in (cfg.get("github_orgs") or []) if str(o).strip()] or ([cfg["github_org"]] if cfg.get("github_org") else [])),
            "vault": vault_changes(day, vault), "files": files_touched(day, roots, vault), "log": day_log(day, agent)}


# ---------------------------------------------------------------- the narrative, from the brain
def narrative(facts, timeout=240):
    """Ask the agent for the 'what changed today' paragraph: the live voice line first (one shared
    session), otherwise a one-shot on the same saved session. Empty string if neither answers."""
    brief = {
        "date": facts["date"],
        "local_commits": [{"repo": r["name"], "branch": r["branch"], "uncommitted_changes": r["dirty"], "commits": [f"{c['time']} {c['author']}: {c['subject']}" for c in r["commits"][:12]]} for r in facts["local"][:12]],
        "github": {"org": facts["github"]["org"], "commits": [{"repo": r["name"], "commits": [f"{c['time']} {c['author']}: {c['subject']}" for c in r["commits"][:10]]} for r in facts["github"]["repos"][:10]],
                   "ci_runs": [f"{r['repo']} {r['workflow']} on {r['branch']}: {r['conclusion']}" for r in facts["github"]["runs"][:20]]},
        "vault_notes_changed": [f"{n['folder']}/{n['name']}" for n in facts["vault"][:30]],
        "files_touched": len(facts["files"]), "reminders_fired": [r["text"] for r in facts["log"]["reminders"]],
        "builds_that_changed_state": [b["text"] for b in facts["log"]["builds"]], "spoken_turns": facts["log"]["turns_you"],
    }
    prompt = (f"(written: end-of-day report for {facts['date']}: here are today's facts as data: {json.dumps(brief)} "
              f"Write the 'What changed today' summary for {facts['owner']}'s evening report, in plain text: four to six sentences, no lists, "
              f"no markdown. Say who committed what and where, what the builds did, what moved in the vault, what is still open, and one thing "
              f"worth doing tomorrow. If the day was quiet, say so in two sentences. This is written, not spoken: do not read it out.)")
    # the live line, if it is up
    try:
        req = urllib.request.Request("http://127.0.0.1:8796/ask", data=json.dumps({"text": prompt}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
            if d.get("reply"):
                return d["reply"].strip()
    except Exception:
        pass
    # otherwise the same saved session, one shot
    try:
        sid = (HOME / "backtalk" / ".backtalk_session").read_text().strip()
    except Exception:
        sid = ""
    cmd = ["claude", "-p", prompt, "--output-format", "text"] + (["--resume", sid] if sid else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(HOME), env={**os.environ, "PATH": PATH, "HOME": str(Path.home())})
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


# ---------------------------------------------------------------- the document
CSS = """
  @page { size: A4; margin: 18mm 16mm; }
  body { font: 11.5pt/1.5 -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1b2430; margin: 0; }
  .sheet { max-width: 760px; margin: 0 auto; padding: 32px 28px 48px; }
  header { border-bottom: 2px solid #c9a24a; padding-bottom: 14px; margin-bottom: 22px; display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; }
  header h1 { margin: 0; font-size: 22pt; letter-spacing: .02em; }
  header .k { color: #7a6a3a; font-size: 9.5pt; letter-spacing: .18em; text-transform: uppercase; }
  header .d { text-align: right; color: #5a6675; font-size: 10pt; }
  .stats { display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 22px; }
  .stat { flex: 1 1 120px; border: 1px solid #e3e6ea; border-radius: 10px; padding: 10px 12px; }
  .stat b { display: block; font-size: 18pt; color: #b08a2e; line-height: 1.1; }
  .stat span { font-size: 9pt; color: #5a6675; letter-spacing: .06em; text-transform: uppercase; }
  h2 { font-size: 12.5pt; letter-spacing: .08em; text-transform: uppercase; color: #7a6a3a; margin: 26px 0 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; page-break-after: avoid; }
  p.sum { font-size: 12pt; line-height: 1.6; border-left: 3px solid #c9a24a; padding: 2px 0 2px 14px; margin: 0 0 6px; }
  table { border-collapse: collapse; width: 100%; font-size: 10pt; page-break-inside: auto; }
  th { text-align: left; color: #5a6675; font-weight: 600; font-size: 9pt; letter-spacing: .06em; text-transform: uppercase; padding: 4px 8px 6px; border-bottom: 1px solid #e3e6ea; }
  td { padding: 5px 8px; border-bottom: 1px solid #f0f2f4; vertical-align: top; }
  tr { page-break-inside: avoid; }
  td.t { color: #8a94a0; white-space: nowrap; font-variant-numeric: tabular-nums; }
  td.a { white-space: nowrap; font-weight: 600; }
  .repo { font-weight: 700; margin: 12px 0 4px; }
  .repo small { color: #8a94a0; font-weight: 400; }
  .ok { color: #1d8a4f; font-weight: 600; } .bad { color: #c0392b; font-weight: 600; } .dim { color: #8a94a0; }
  .none { color: #8a94a0; font-style: italic; }
  footer { margin-top: 36px; color: #8a94a0; font-size: 9pt; border-top: 1px solid #eee; padding-top: 10px; }
"""


def esc(t):
    return html.escape(str(t or ""))


def render(facts, story):
    day = dt.datetime.strptime(facts["date"], "%Y-%m-%d")
    nice = day.strftime("%A %-d %B %Y")
    n_commits = sum(len(r["commits"]) for r in facts["local"]) + sum(len(r["commits"]) for r in facts["github"]["repos"])
    authors = sorted({c["author"] for r in facts["local"] + facts["github"]["repos"] for c in r["commits"] if c.get("author")})
    runs = facts["github"]["runs"]; failed = [r for r in runs if r["conclusion"] == "failure"]
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(facts['agent'])} · End of day · {esc(facts['date'])}</title><style>{CSS}</style></head><body><div class="sheet">
<header><div><div class="k">{esc(facts['agent'])} · End of day</div><h1>{esc(nice)}</h1></div><div class="d">for {esc(facts['owner'])}<br>built {esc(facts['built'])}</div></header>
<div class="stats"><div class="stat"><b>{n_commits}</b><span>commits</span></div><div class="stat"><b>{len(authors)}</b><span>people committing</span></div>
<div class="stat"><b>{len(runs)}</b><span>CI runs{(' · ' + str(len(failed)) + ' failed') if failed else ''}</span></div><div class="stat"><b>{len(facts['vault'])}</b><span>notes changed</span></div>
<div class="stat"><b>{facts['log']['turns_you']}</b><span>things you said</span></div></div>"""]
    parts.append("<h2>What changed today</h2>" + (f'<p class="sum">{esc(story)}</p>' if story else '<p class="none">No narrative this time (the brain was not reachable); the facts are below.</p>'))
    # local commits
    parts.append("<h2>On this Mac</h2>")
    if not facts["local"]:
        parts.append('<p class="none">No commits and no uncommitted changes in any repository today.</p>')
    for r in facts["local"]:
        if not r["commits"]:
            continue
        parts.append(f'<div class="repo">{esc(r["name"])} <small>{esc(r["branch"])} · {esc(r["path"])}{(" · " + str(r["dirty"]) + " uncommitted change" + ("s" if r["dirty"] != 1 else "")) if r["dirty"] else ""}</small></div>')
        parts.append("<table><tr><th>time</th><th>who</th><th>commit</th></tr>" + "".join(f'<tr><td class="t">{esc(c["time"])}</td><td class="a">{esc(c["author"])}</td><td>{esc(c["subject"])} <span class="dim">{esc(c["sha"])}</span></td></tr>' for c in r["commits"]) + "</table>")
    dirty_only = [r for r in facts["local"] if not r["commits"] and r["dirty"]]
    if dirty_only:
        parts.append('<div class="repo">Uncommitted changes, no commits today <small>' + esc(", ".join(f"{r['name']} ({r['dirty']})" for r in dirty_only)) + "</small></div>")
    # github
    gh = facts["github"]
    if gh["org"]:
        parts.append(f"<h2>On GitHub · {esc(gh['org'])}</h2>")
        if not gh["repos"] and not runs:
            parts.append('<p class="none">Nothing landed there today.</p>')
        for r in gh["repos"]:
            parts.append(f'<div class="repo">{esc(r["name"])}</div><table><tr><th>time</th><th>who</th><th>commit</th></tr>' + "".join(f'<tr><td class="t">{esc(c["time"])}</td><td class="a">{esc(c["author"])}</td><td>{esc(c["subject"])} <span class="dim">{esc(c["sha"])}</span></td></tr>' for c in r["commits"]) + "</table>")
        if runs:
            parts.append('<div class="repo">CI runs</div><table><tr><th>repo</th><th>workflow</th><th>branch</th><th>result</th></tr>' + "".join(f'<tr><td>{esc(r["repo"])}</td><td>{esc(r["workflow"])} <span class="dim">{esc(r["title"])}</span></td><td>{esc(r["branch"])}</td><td class="{"ok" if r["conclusion"] == "success" else "bad" if r["conclusion"] == "failure" else "dim"}">{esc(r["conclusion"])}</td></tr>' for r in runs) + "</table>")
    # vault
    parts.append("<h2>In the vault</h2>")
    parts.append('<p class="none">No notes changed today.</p>' if not facts["vault"] else "<table><tr><th>time</th><th>note</th><th>folder</th></tr>" + "".join(f'<tr><td class="t">{esc(n["time"])}</td><td>{esc(n["name"])}</td><td class="dim">{esc(n["folder"])}</td></tr>' for n in facts["vault"]) + "</table>")
    # the day
    lg = facts["log"]
    parts.append("<h2>The day</h2><table><tr><th>what</th><th>detail</th></tr>")
    parts.append(f'<tr><td>Conversation</td><td>{lg["turns_you"]} things you said, {lg["turns_agent"]} sentences back</td></tr>')
    parts.append(f'<tr><td>Reminders</td><td>{esc("; ".join(r["time"] + " " + r["text"] for r in lg["reminders"])) if lg["reminders"] else "<span class=dim>none fired</span>"}</td></tr>')
    parts.append(f'<tr><td>Builds</td><td>{esc(" · ".join(b["time"] + " " + b["text"] for b in lg["builds"])) if lg["builds"] else "<span class=dim>no build changed state</span>"}</td></tr>')
    parts.append(f'<tr><td>Approvals</td><td>{esc(" · ".join(lg["approvals"])) if lg["approvals"] else "<span class=dim>none</span>"}</td></tr>')
    parts.append(f'<tr><td>Files touched</td><td>{len(facts["files"])} outside the vault' + (": " + esc(", ".join(f["name"] for f in facts["files"][:25])) + (" …" if len(facts["files"]) > 25 else "") if facts["files"] else "") + "</td></tr></table>")
    parts.append(f'<footer>{esc(facts["agent"])} · end-of-day report · {esc(facts["date"])} · this document was built on your Mac from git, GitHub, Spotlight and the vault; the summary is {esc(facts["agent"])}\'s own words.</footer></div></body></html>')
    return "\n".join(parts)


def to_pdf(html_path, pdf_path):
    if not Path(CHROME).exists():
        return False
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", f"file://{html_path}"],
                       capture_output=True, timeout=90)
    except Exception:
        return False
    return Path(pdf_path).exists() and Path(pdf_path).stat().st_size > 1000


def send_telegram(pdf_path, caption):
    try:
        sys.path.insert(0, str(HERE))
        import telegram
        tok = telegram.token(); st = telegram.state()
        if not tok or not st.get("owner"):
            return False
        telegram.api_upload("sendDocument", tok, "document", str(pdf_path), "application/pdf", chat_id=st["owner"], caption=caption[:1000])
        return True
    except Exception as e:
        print("telegram:", repr(e), file=sys.stderr)
        return False


def build(day, send=True, story=True):
    REPORTS.mkdir(exist_ok=True)
    facts = gather(day)
    text = narrative(facts) if story else ""
    facts["narrative"] = text
    html_path = REPORTS / f"{day}.html"; pdf_path = REPORTS / f"{day}.pdf"; json_path = REPORTS / f"{day}.json"
    html_path.write_text(render(facts, text), encoding="utf-8")
    json_path.write_text(json.dumps(facts, indent=1))
    pdf_ok = to_pdf(html_path, pdf_path)
    sent = False
    if send:
        n = sum(len(r["commits"]) for r in facts["local"]) + sum(len(r["commits"]) for r in facts["github"]["repos"])
        cap = f"End of day, {dt.datetime.strptime(day, '%Y-%m-%d').strftime('%A %-d %B')}: {n} commit{'s' if n != 1 else ''}, {len(facts['vault'])} note{'s' if len(facts['vault']) != 1 else ''} changed." + (f"\n\n{text[:700]}" if text else "")
        sent = send_telegram(pdf_path if pdf_ok else html_path, cap)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent)); import db
        db.report_add(day, html=str(html_path), pdf=str(pdf_path) if pdf_ok else "", narrative=text, sent=sent); db.run_add("report", f"{day}: {'sent' if sent else 'built'}")
    except Exception:
        pass
    return {"date": day, "html": str(html_path), "pdf": str(pdf_path) if pdf_ok else "", "sent": sent, "narrative": bool(text)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--no-send", action="store_true")
    ap.add_argument("--no-narrative", action="store_true")
    a = ap.parse_args()
    r = build(a.date, send=not a.no_send, story=not a.no_narrative)
    print(json.dumps(r))
