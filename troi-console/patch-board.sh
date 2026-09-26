#!/bin/bash
# The board's tools in place. The board itself is Silo One's own page (troi-console/barehands/board.html, served by
# board-server.py at the address the console embeds); the one file that must live in the vendored folder is the agent's
# eyes on the board, barehands/bin/board-state.sh, because the boot file names that path. Idempotent; run at every start.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"
mkdir -p "$ROOT/barehands/bin"
if [ -f "$C/barehands/board-state.sh" ]; then
  cp "$C/barehands/board-state.sh" "$ROOT/barehands/bin/board-state.sh" && chmod +x "$ROOT/barehands/bin/board-state.sh" && echo "board: board-state.sh in place"
fi
