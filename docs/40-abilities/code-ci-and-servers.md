---
title: Code, CI and servers
description: Coding sessions inside a project, PR reviews in a throwaway checkout, the CI watch of your GitHub org, and the read-only server watch.
order: 11
---

## Working in a project

"Work on the website", "open the my-app project": a Terminal window opens with a Claude Code session
inside that project's folder that is still your agent: the boot file, the deletion guard and the
vault ride along, and its first message names the project's vault folder to read first. That window
is where the coding happens. `troi-console/code.sh list` shows the projects (`projects` in the
settings; any folder under `projects_root` works by name).

Project source code is read-only to the agent by default: before editing a code file, a config that
affects a running system, or any commit, push or deploy, it states the exact change and waits for
your word.

## PR review on demand

"Review PR 3 on my-app", "look at the open PRs", "review my changes in the website": the agent
checks the PR out into a throwaway worktree, runs your Code Review job in a headless session of its
own with read-only tools, saves the report in `data/blobs/reviews/` and sends it to your phone. The
report goes on the PR as a comment only when you say "post it". `pr.py list` shows open PRs;
`pr.py show <repo> <n>` reads a report back.

## The CI watch

Run `gh auth login`, then add the GitHub orgs and users to follow under Routines › **CI watch**: type
a name and press Watch, × stops watching one; as many as you like (`github_orgs` in the settings).
The pulse checks the newest run on `main` of every repo of each of them every three minutes: a
failure is spoken by the agent, or sent to Telegram when the voice line is down, and the agent then
follows the CI Failure Response job: the log, a diagnosis, a small fix as a PR, a Telegram report,
and never a merge without green CI and your word. "How is CI", "any failed builds" gives the status
on demand.

## The server watch

`troi-console/servers.py add <name> <ssh-host> [role]` registers a server (kept in
`data/servers.json`). The pulse checks every server over SSH every 15 minutes, read-only: load,
disk, memory, failed services, containers, updates, reboot needed. It speaks only what changed, and
the agent then follows its Server Maintenance job: look first, propose the fix, and change nothing
on a server without your go. "How are the servers", "check prod" runs the check now, worst first.

A node that needs your own sign-in is **signed out**, not down: a Google Cloud VM behind an IAP
tunnel with OS Login's 2-step, or gcloud itself asking to be signed in again. The watch does not
announce it, the check lists it as SIGNED OUT, and the agent asks you once to sign in from your own
terminal (`ssh <the node>`; the session then stays open for hours through its control socket), sets
itself a reminder, and picks the task up again when the node answers. It never tries to pass the
2-step itself.
