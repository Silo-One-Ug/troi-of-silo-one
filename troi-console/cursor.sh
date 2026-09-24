#!/bin/bash
# the agent's real hands (see cursor.py for the commands and the guards).
D="$(cd "$(dirname "$0")" && pwd)"; exec "$D/.venv-ring/bin/python" "$D/cursor.py" "$@"
