#!/bin/bash
# Shared settings for the shell tools (sourced): the agent's name, the owner's name, the vault path, the GitHub org,
# and the GitHub account and organization the backups belong to.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"
_get() { python3 -c 'import json,sys
try: c=json.load(open(sys.argv[1]))
except Exception: c={}
v=c.get(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else "")
print(v if not isinstance(v, (list, dict)) else json.dumps(v))' "$@"; }
AGENT="$(_get "$ROOT/backtalk/backtalk.json" name Troi)"
OWNER="$(_get "$CONFIG" owner "the owner")"
VAULT="$(_get "$CONFIG" vault "$HOME/Vault")"
GH_ORG="$(_get "$CONFIG" github_org "")"
VAULT_REPO="$(_get "$CONFIG" vault_repo "")"
GITHUB_ACCOUNT="$(_get "$CONFIG" github_account "ayesigapaul")"     # the gh account every Troi repo is written as
BACKUP_ORG="$(_get "$CONFIG" backup_org "Silo-One-Ug")"             # where the backups live
# act on GitHub as that account, whichever gh account is active (Paul-Ayesiga may be, for other work): exports GH_TOKEN,
# which gh and "gh auth git-credential" both honour, and makes every commit carry that same account (its name and its
# public email, or its GitHub noreply address), so GitHub credits the account that pushed. Fails when it is not signed in.
use_github_account() {
  local t who; t="$(gh auth token -u "$GITHUB_ACCOUNT" 2>/dev/null)"; [ -n "$t" ] || return 1; export GH_TOKEN="$t"
  who="$(gh api user --jq '"\(.name // .login)\t\(.email // "\(.id)+\(.login)@users.noreply.github.com")"' 2>/dev/null)" || return 0
  [ -n "$who" ] && export GIT_AUTHOR_NAME="${who%%$'\t'*}" GIT_AUTHOR_EMAIL="${who##*$'\t'}" GIT_COMMITTER_NAME="${who%%$'\t'*}" GIT_COMMITTER_EMAIL="${who##*$'\t'}"
  return 0
}
