---
status: active
project: meta
type: guide
---
# CI Failure Response

**The job:** A build on `main` failed (the pulse tells you, or __OWNER__ asks "why did CI fail"). Diagnose it, fix it if it is small, and keep __OWNER__ informed, end to end.

## The procedure
1. Get the facts: `gh run list -R <org>/<repo> -b main -L 3`, then `gh run view <id> -R <org>/<repo> --log-failed`. Read the whole failing step.
2. Classify: flaky or infrastructure (a download, a rate limit, a runner hiccup) → re-run it (`gh run rerun <id> -R <org>/<repo> --failed`) and say so; a real defect → go on.
3. Find the change that broke it (`gh pr list --state merged -L 5`, the diff) and decide whether the fix is small (one file, one idea, no behaviour change beyond the fix).
4. Small fix: branch from main (`fix/<short-name>`), make the change, run the same checks locally where you can, push, open the PR with a plain-language description and the failing run linked. **Do not merge.** Tell __OWNER__ on Telegram: what failed, why, the PR link, and "merges on green when you say so".
5. Not small: write up the diagnosis and the options, and tell __OWNER__ with your recommendation.
6. When __OWNER__ says merge and CI is green: merge, and log it in today's daily note.

## Quality bar
- Facts from the log, never from guesswork; quote the failing line. One PR, one fix. Never merge without green CI and __OWNER__'s word. Never force anything.

## Lessons (fold corrections in here over time)
- Transient downloads are the first suspect for "command not found" walls.
