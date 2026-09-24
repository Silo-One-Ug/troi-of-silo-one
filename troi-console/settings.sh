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
# which gh and "gh auth git-credential" both honour; fails when that account is not signed in to gh
use_github_account() { local t; t="$(gh auth token -u "$GITHUB_ACCOUNT" 2>/dev/null)"; [ -n "$t" ] || return 1; export GH_TOKEN="$t"; }
