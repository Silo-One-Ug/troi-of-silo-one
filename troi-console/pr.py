#!/usr/bin/env python3
"""PR review on demand: the agent reviews a pull request (or a local branch) the way the owner's
Code Review job says, in a headless session of its own, and reports back. Stdlib only, plus gh and git.

  pr.py list [owner/repo]                         open PRs on the owner's repos (or one repo)
  pr.py review <repo> <number> [--post] [--no-send] [--tests]
        <repo> is owner/name, a project name from console.json, or a clone path. The PR head is
        checked out into a throwaway worktree (the owner's working tree is never touched), the
        review runs there with read-only tools, and the report lands in data/blobs/reviews/ and
        on Telegram. --post also posts it as a PR comment: only when the owner said so.
        --tests lets the reviewer run the project's test command (off by default: cost and time).
  pr.py review <project> --local [--base main]    the working tree and local commits against the base
  pr.py show <repo> <number>                      print the last report for that PR

The reviewer is the agent itself (boot file, rules, vault), so findings follow the owner's standards.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
OUT = P.blob_dir("reviews")
WORK = OUT / "work"
PATH = f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")
os.environ["PATH"] = PATH
READ_ONLY_TOOLS = ["Read", "Grep", "Glob", "LS", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git blame:*)",
                   "Bash(git status:*)", "Bash(git ls-files:*)", "Bash(gh pr view:*)", "Bash(gh pr diff:*)", "Bash(cat:*)", "Bash(head:*)",
                   "Bash(tail:*)", "Bash(wc:*)", "Bash(ls:*)", "Bash(find:*)", "Bash(grep:*)", "Bash(rg:*)", "Bash(awk:*)", "Bash(sed -n:*)",
                   "Bash(sort:*)", "Bash(uniq:*)", "Bash(cut:*)", "Bash(jq:*)", "Bash(diff:*)", "Bash(php -l:*)", "Bash(node --check:*)",
                   "Bash(python3 -m py_compile:*)"]


def split_diff(diff, folder):
    """One file per changed path under folder/, plus an index: the Read tool cannot swallow a 2 MB diff whole."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.diff"): old.unlink()
    chunks, cur, name = [], [], None
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if name: chunks.append((name, "".join(cur)))
            name = line.split(" b/", 1)[-1].strip(); cur = []
        cur.append(line)
    if name: chunks.append((name, "".join(cur)))
    index = []
    for i, (path, text) in enumerate(chunks, 1):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", path)[:120]
        (folder / f"{i:03d}_{safe}.diff").write_text(text)
        index.append(f"{i:03d}_{safe}.diff\t{text.count(chr(10))} lines\t{path}")
    (folder / "INDEX.txt").write_text("\n".join(index) + "\n")
    return len(chunks)


def sh(args, cwd=None, timeout=300, check=True, input=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, input=input)
    if check and r.returncode != 0:
        raise SystemExit(f"{' '.join(args[:3])} failed: {(r.stderr or r.stdout).strip()[:400]}")
    return r.stdout


def cfg():
    try: return json.loads((P.CONFIG).read_text())
    except Exception: return {}


def owner_login():
    try: return sh(["gh", "api", "user", "--jq", ".login"]).strip()
    except SystemExit: return ""


def origin_slug(folder):
    try: url = sh(["git", "-C", folder, "remote", "get-url", "origin"]).strip()
    except SystemExit: return ""
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def project_folder(name):
    c = cfg(); p = c.get("projects", {})
    for k, v in p.items():
        if name.lower() in [k.lower()] + [a.lower() for a in v.get("aliases", [])]: return os.path.expanduser(v["folder"])
    root = os.path.expanduser(c.get("projects_root", ""))
    if root and os.path.isdir(os.path.join(root, name)): return os.path.join(root, name)
    return name if os.path.isdir(os.path.expanduser(name)) else ""


def resolve_repo(arg):
    """-> (owner/name, local clone folder or "")"""
    if "/" in arg and not os.path.isdir(os.path.expanduser(arg)):
        slug = arg
    else:
        folder = project_folder(arg)
        slug = origin_slug(folder) if folder else ""
        if not slug:
            me = owner_login(); slug = f"{me}/{arg}" if me else ""
    root = os.path.expanduser(cfg().get("projects_root", ""))
    clone = ""
    if root and os.path.isdir(root):
        for d in sorted(os.listdir(root)):
            f = os.path.join(root, d)
            if os.path.isdir(os.path.join(f, ".git")) and origin_slug(f).lower() == slug.lower(): clone = f; break
    return slug, clone


def checkout_pr(slug, number, clone):
    """A detached worktree (or shallow clone) at the PR head; never the owner's working tree."""
    WORK.mkdir(parents=True, exist_ok=True)
    wt = WORK / f"{slug.replace('/', '-')}-{number}"
    if wt.exists():
        if clone: subprocess.run(["git", "-C", clone, "worktree", "remove", "--force", str(wt)], capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)
    if clone:
        sh(["git", "-C", clone, "fetch", "-q", "origin", f"pull/{number}/head:refs/pr/{number}"], timeout=600)
        sh(["git", "-C", clone, "worktree", "add", "--detach", "-q", str(wt), f"refs/pr/{number}"])
    else:
        sh(["gh", "repo", "clone", slug, str(wt), "--", "--depth", "200", "-q"], timeout=900)
        sh(["gh", "pr", "checkout", str(number)], cwd=str(wt), timeout=600)
    return wt


def cleanup(wt, clone):
    if clone: subprocess.run(["git", "-C", clone, "worktree", "remove", "--force", str(wt)], capture_output=True)
    shutil.rmtree(wt, ignore_errors=True)


def job_text():
    try: return (Path(cfg()["vault"]) / "10 - Resources" / "Jobs" / "Code Review.md").read_text()
    except Exception: return "Review for correctness first (logic, edge cases, error handling, races, data loss), then security, then the project's conventions, then simplification. Rank findings by severity with file:line and a concrete failure scenario."


def vault_hint(slug):
    """The vault folder for this repo's project, if the mapping knows it."""
    for k, v in cfg().get("projects", {}).items():
        f = os.path.expanduser(v.get("folder", ""))
        if f and origin_slug(f).lower() == slug.lower() and v.get("vault"): return f"{cfg()['vault']}/{v['vault']}/"
    return ""


def run_review(cwd, title, meta, diff_path, slug, tests):
    agent = json.loads((HOME / "backtalk" / "backtalk.json").read_text()).get("name", "the agent")
    hint = vault_hint(slug)
    prompt = f"""You are reviewing: {title}

{meta}

The full diff is split per changed file under {diff_path}/ (start with {diff_path}/INDEX.txt: one line per file with its size; read every listed .diff, one at a time, largest ones with offset/limit if needed). This folder is a checkout of the change itself, so read any surrounding code you need directly. Prefer the Read and Grep tools; only the listed read-only shell commands are allowed, and pipelines of several commands may be refused, so keep shell one command at a time. {("The project's memory in your vault is " + hint + " (read its index and the working-rules / conventions notes first; project rules override generic taste).") if hint else "If the vault has notes on this project, read them first."}

Follow your Code Review job below to the letter. Read the WHOLE diff, every file, front to back; never sample. {"You may run the project's test command if one is obvious and cheap." if tests else "Do not run test suites or install anything; reading and git commands only."} Do not modify any file, commit, push, or post anything.

Write the report in Markdown, in this shape and nothing else:
# Review: {title}
**Verdict:** one line (ready / needs changes / do not merge) with the single most important reason.
## Findings
Ranked, most severe first. Each: `path:line` — what is wrong — a concrete failure scenario — the fix. Skip nitpicks unless nothing else is wrong.
## Looks good
What is done well, briefly, and anything worth watching.
## Checked
What you read and ran (files, tests), in a few lines.

--- Your Code Review job ---
{job_text()}
"""
    args = ["claude", "-p", "--output-format", "json", "--max-turns", "400",
            "--add-dir", str(Path(cfg().get("vault", "")).expanduser()), str(HOME),
            "--settings", str(HOME / ".claude" / "settings.json"),
            "--allowedTools", *READ_ONLY_TOOLS,
            "--append-system-prompt", (HOME / "CLAUDE.md").read_text(),
            "--name", f"{agent}: review", prompt]
    log = Path(str(diff_path).rstrip("/") + ".log")
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=2400, stdin=subprocess.DEVNULL)
    log.write_text(f"exit {r.returncode}\n--- stderr ---\n{r.stderr}\n--- stdout ---\n{r.stdout}")
    try:
        d = json.loads(r.stdout)
    except Exception:
        raise SystemExit(f"the review session gave no usable answer (exit {r.returncode}); see {log}")
    if d.get("is_error") or d.get("subtype") not in (None, "success"):
        raise SystemExit(f"the review session ended with {d.get('subtype')}: {str(d.get('result', ''))[:300]} (see {log})")
    print(f"session: {d.get('num_turns')} turns, {d.get('duration_ms', 0) // 1000}s", flush=True)
    return (d.get("result") or "").strip()


def send(text):
    py = HOME / "backtalk" / ".venv" / "bin" / "python"
    subprocess.run([str(py), str(HERE / "telegram.py"), "send", text[:3900]], capture_output=True, timeout=60)


def review_pr(repo, number, post=False, no_send=False, tests=False):
    slug, clone = resolve_repo(repo)
    if not slug: raise SystemExit(f"cannot tell which GitHub repo {repo!r} is (owner/name, a project name, or a clone path)")
    pr = json.loads(sh(["gh", "pr", "view", str(number), "-R", slug, "--json", "title,body,author,baseRefName,headRefName,url,additions,deletions,changedFiles,files"]))
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{slug.replace('/', '-')}-{number}"
    diff_path = OUT / f"{stem}.diff"
    meta = (f"PR #{number} on {slug} by {pr['author']['login']}: {pr['headRefName']} -> {pr['baseRefName']}; "
            f"{pr['changedFiles']} files, +{pr['additions']} -{pr['deletions']}. {pr['url']}\n\nDescription:\n{(pr.get('body') or '(none)')[:4000]}\n\nFiles:\n"
            + "\n".join(f"- {f['path']} (+{f['additions']} -{f['deletions']})" for f in pr.get("files", [])[:200]))
    print(f"reviewing {slug}#{number} \"{pr['title']}\" ({pr['changedFiles']} files, +{pr['additions']} -{pr['deletions']})", flush=True)
    wt = checkout_pr(slug, number, clone)
    try:
        # the diff comes from git in the checkout (GitHub's API refuses diffs over 20,000 lines)
        sh(["git", "-C", str(wt), "fetch", "-q", "origin", pr["baseRefName"]], timeout=600)
        diff = sh(["git", "-C", str(wt), "diff", f"origin/{pr['baseRefName']}...HEAD"], timeout=300)
        diff_path.write_text(diff)
        parts = OUT / stem; n = split_diff(diff, parts)
        print(f"diff: {diff.count(chr(10))} lines in {n} files", flush=True)
        report = run_review(str(wt), f"{slug}#{number} {pr['title']}", meta, str(parts), slug, tests)
    finally:
        cleanup(wt, clone)
    path = OUT / f"{stem}.md"
    path.write_text(f"<!-- reviewed {dt.datetime.now():%Y-%m-%d %H:%M} · {pr['url']} -->\n" + report + "\n")
    if post:
        sh(["gh", "pr", "comment", str(number), "-R", slug, "-F", str(path)], timeout=120); print("posted as a PR comment")
    if not no_send: send(f"Review of {slug}#{number} \"{pr['title']}\"\n\n" + re.sub(r"^#+ ", "", report, flags=re.M))
    print(path); print(report)


def review_local(project, base=None, no_send=False, tests=False):
    folder = project_folder(project)
    if not folder or not os.path.isdir(os.path.join(folder, ".git")): raise SystemExit(f"{project!r} is not a git project I know")
    base = base or (sh(["git", "-C", folder, "symbolic-ref", "refs/remotes/origin/HEAD"], check=False).strip().rsplit("/", 1)[-1] or "main")
    diff = sh(["git", "-C", folder, "diff", f"{base}...HEAD"], check=False) + sh(["git", "-C", folder, "diff", "HEAD"], check=False)
    untracked = sh(["git", "-C", folder, "ls-files", "--others", "--exclude-standard"], check=False).strip()
    if not diff.strip() and not untracked: raise SystemExit(f"nothing to review in {folder} against {base}")
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"local-{os.path.basename(folder)}-{dt.datetime.now():%Y%m%d-%H%M}"
    diff_path = OUT / f"{stem}.diff"; diff_path.write_text(diff)
    parts = OUT / stem; split_diff(diff, parts)
    if untracked: (parts / "UNTRACKED.txt").write_text(untracked + "\n")
    slug = origin_slug(folder)
    meta = (f"Local changes in {folder} against {base} (commits on the branch plus the working tree)." + (f" Remote: {slug}." if slug else "")
            + (" New untracked files are listed in UNTRACKED.txt next to the diffs; read them in the folder." if untracked else ""))
    print(f"reviewing local changes in {folder} against {base}", flush=True)
    report = run_review(folder, f"{os.path.basename(folder)} local changes vs {base}", meta, str(parts), slug, tests)
    path = OUT / f"{stem}.md"; path.write_text(report + "\n")
    if not no_send: send(f"Review of local changes in {os.path.basename(folder)} vs {base}\n\n" + re.sub(r"^#+ ", "", report, flags=re.M))
    print(path); print(report)


def main(a):
    flags = {x for x in a if x.startswith("--")}; args = [x for x in a if not x.startswith("--")]
    base = next((a[i + 1] for i, x in enumerate(a) if x == "--base" and i + 1 < len(a)), None)
    if base: args = [x for x in args if x != base]
    c = args[0] if args else "help"
    if c == "list":
        me = owner_login()
        repos = [args[1]] if len(args) > 1 else json.loads(sh(["gh", "repo", "list", me, "--limit", "60", "--json", "nameWithOwner"]))
        for r in repos:
            slug = r if isinstance(r, str) else r["nameWithOwner"]
            for p in json.loads(sh(["gh", "pr", "list", "-R", slug, "--json", "number,title,headRefName,author"], check=False) or "[]"):
                print(f"{slug}#{p['number']}\t{p['title']}\t{p['headRefName']}\t{p['author']['login']}")
    elif c == "review" and "--local" in flags and len(args) >= 2:
        review_local(args[1], base, "--no-send" in flags, "--tests" in flags)
    elif c == "review" and len(args) >= 3:
        review_pr(args[1], int(args[2]), "--post" in flags, "--no-send" in flags, "--tests" in flags)
    elif c == "show" and len(args) >= 3:
        slug, _ = resolve_repo(args[1]); p = OUT / f"{slug.replace('/', '-')}-{args[2]}.md"
        print(p.read_text() if p.exists() else f"no report yet for {slug}#{args[2]}")
    else: print(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
