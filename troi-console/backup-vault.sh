#!/bin/bash
# Backs up the agent's memory (the vault) to its git remote (vault_repo in the settings), then the agent's own record.
# Runs nightly (launchd) and whenever the agent is asked to "back up the vault". Add-only: never deletes.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"
if cd "$VAULT" 2>/dev/null; then
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { git init -q -b main; [ -n "$VAULT_REPO" ] && git remote add origin "$VAULT_REPO"; }
git add -A
if git diff --cached --quiet; then echo "vault backup: nothing new"; else
  git commit -q -m "vault backup $(date '+%Y-%m-%d %H:%M')"
  if git remote get-url origin >/dev/null 2>&1; then git push -q origin main && echo "vault backup: pushed $(git rev-parse --short HEAD)" || echo "vault backup: push failed (offline?) — committed locally, will push next time"
  else echo "vault backup: committed locally (no remote: git remote add origin <url> in the vault, or set vault_repo in console.json)"; fi
fi
else echo "vault backup: no vault yet"; fi

# and the agent's own record (data/troi.db and the blob store) to its private backup repo
"$C/backup-data.sh"
