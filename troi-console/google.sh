#!/bin/bash
# The owner's Google account as one of the brain's tool servers (listed in .mcp.json as "google"): the Google Workspace
# MCP server, run with uvx, with the OAuth client and the sign-in kept in data/google/ by google.py.
#   google.sh mcp                the tool server on stdio (what the brain runs)
#   google.sh <anything else>    handed to google.py: status | setup <client_secret.json> | enable [project] | signin <email>
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = "mcp" ]; then
  while IFS='=' read -r k v; do [ -n "$k" ] && export "$k=$v"; done < <(python3 "$HERE/google.py" env)
  exec uvx workspace-mcp --single-user --transport stdio --tools calendar gmail drive docs sheets tasks contacts
fi
exec python3 -u "$HERE/google.py" "$@"
