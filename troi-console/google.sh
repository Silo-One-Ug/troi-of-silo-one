#!/bin/bash
# The owner's Google account as one of the brain's tool servers (listed in .mcp.json as "google"): the Google Workspace
# MCP server, installed as a uv tool by install.sh (uvx resolves it as the fallback, slower and network-bound, which is
# how a session once started without its Google tools), with the OAuth client and the sign-in kept in data/google/ by
# google.py, and the per-service permission levels from google.py (Gmail at drafts, Contacts read-only, the rest full).
#   google.sh mcp                the tool server on stdio (what the brain runs)
#   google.sh <anything else>    handed to google.py: status | setup <client_secret.json> | enable [project] | signin <email>
#                                | signout <email> | permissions
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = "mcp" ]; then
  while IFS='=' read -r k v; do [ -n "$k" ] && export "$k=$v"; done < <(python3 "$HERE/google.py" env)
  LEVELS="$(python3 "$HERE/google.py" permissions)"
  BIN="$(command -v workspace-mcp || true)"; [ -z "$BIN" ] && [ -x "$HOME/.local/bin/workspace-mcp" ] && BIN="$HOME/.local/bin/workspace-mcp"
  # shellcheck disable=SC2086 # the levels are one word each
  if [ -n "$BIN" ]; then exec "$BIN" --single-user --transport stdio --permissions $LEVELS; fi
  exec uvx workspace-mcp --single-user --transport stdio --permissions $LEVELS
fi
exec python3 -u "$HERE/google.py" "$@"
