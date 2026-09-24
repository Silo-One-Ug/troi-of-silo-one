#!/bin/bash
# Backs up the agent's memory (the vault) to its git remote (vault_repo in the settings), then the agent's own record.
# Runs nightly (launchd) and whenever the agent is asked to "back up the vault". Add-only: never deletes.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "$0")" && pwd)/settings.sh"
if [ -f "$VAULT/VAULT-INDEX.md" ] && cd "$VAULT" 2>/dev/null; then
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init -q -b main
REPO="${VAULT_REPO:-$BACKUP_ORG/troi-vault}"                                   # owner/name, or a full git URL
case "$REPO" in http*|git@*) URL="$REPO";; *) URL="https://github.com/$REPO.git";; esac
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$URL"
git add -A
git diff --cached --quiet || git commit -q -m "vault backup $(date '+%Y-%m-%d %H:%M')"
if [ "$(git rev-list --count HEAD 2>/dev/null)" = "0" ] || ! git rev-parse HEAD >/dev/null 2>&1; then echo "vault backup: nothing to push yet"
elif use_github_account; then
  O="$(git remote get-url origin)"; R="${O#https://github.com/}"; R="${R%.git}"
  case "$O" in https://github.com/*) gh repo view "$R" >/dev/null 2>&1 || { gh repo create "$R" --private --description "Troi of Silo One: the vault" >/dev/null 2>&1 && echo "vault backup: created the private repo $R"; };; esac
  if git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push -q origin HEAD:main 2>/dev/null; then echo "vault backup: pushed $(git rev-parse --short HEAD) to $O"
  else echo "vault backup: push failed (offline?): committed locally, will push next time"; fi
else echo "vault backup: committed locally ($GITHUB_ACCOUNT is not signed in to gh: gh auth login)"; fi
else echo "vault backup: no vault yet"; fi

# and the agent's own record (data/troi.db and the blob store) to its private backup repo
"$C/backup-data.sh"
