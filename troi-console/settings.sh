#!/bin/bash
# Shared settings for the shell tools (sourced): the agent's name, the owner's name, the vault path, the GitHub org.
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
