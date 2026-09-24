#!/bin/bash
# the agent in a project: a Claude Code session INSIDE a project folder that still boots as the agent.
#
#   code.sh list                      the projects it knows (console.json "projects", plus every folder under "projects_root")
#   code.sh <project> [prompt...]     open the session here, in this terminal (the project's own CLAUDE.md and memory
#                                     load as usual; the agent's boot file, deletion guard and vault come along)
#   code.sh <project> --window [...]  the same in a new Terminal window (what the agent runs for "work on <project>")
#
# How it stays the agent outside its home: the boot file rides in as --append-system-prompt, the home's
# .claude/settings.json (the guard hook, denied destructive commands, vault access) as --settings, and the
# vault and the home as --add-dir. The session's first message names the project's vault folder so the
# agent reads that index before anything else.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/paths.sh"; export ROOT CONFIG; H="$ROOT"
[ -n "$1" ] || { sed -n 2,12p "$0" | sed 's/^# \{0,1\}//'; exit 0; }

resolve() {   # name -> "folder|vault folder|display name" (json), via python for the fuzzy match
python3 - "$1" <<'PY'
import json, os, sys
cfg = json.load(open(os.environ["CONFIG"]))
want = sys.argv[1].lower().replace("-", " ").replace("_", " ")
projects = cfg.get("projects", {})
root = cfg.get("projects_root", "")
def out(name, folder, vault=""):
    print(json.dumps({"name": name, "folder": folder, "vault": vault})); sys.exit(0)
for name, p in projects.items():                      # 1. configured projects, by name or alias
    keys = [name] + p.get("aliases", [])
    if any(want == k.lower() or want in k.lower() for k in keys): out(name, os.path.expanduser(p["folder"]), p.get("vault", ""))
if root and os.path.isdir(os.path.expanduser(root)):  # 2. any folder under the projects root
    for d in sorted(os.listdir(os.path.expanduser(root))):
        if want == d.lower().replace("-", " ").replace("_", " ") or want in d.lower():
            out(d, os.path.join(os.path.expanduser(root), d))
if os.path.isdir(os.path.expanduser(sys.argv[1])):    # 3. a path
    out(os.path.basename(os.path.expanduser(sys.argv[1]).rstrip("/")), os.path.expanduser(sys.argv[1]))
sys.exit(1)
PY
}

if [ "$1" = "list" ]; then
python3 - <<'PY'
import json, os
cfg = json.load(open(os.environ["CONFIG"]))
for name, p in cfg.get("projects", {}).items(): print(f"{name:<18} {p['folder']:<52} vault: {p.get('vault', '-')}")
root = cfg.get("projects_root", "")
if root: print(f"(any other folder under {root} by name)")
PY
exit 0
fi

J="$(resolve "$1")" || { echo "no project called '$1' (code.sh list)"; exit 1; }
shift
NAME="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["name"])' "$J")"
FOLDER="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["folder"])' "$J")"
VFOLDER="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["vault"])' "$J")"
VAULT="$(python3 -c 'import json,os; print(json.load(open(os.environ["CONFIG"]))["vault"])')"
AGENT="$(python3 -c 'import json,os; print(json.load(open(os.environ["ROOT"] + "/backtalk/backtalk.json")).get("name","the agent"))')"

WINDOW=0; [ "$1" = "--window" ] && { WINDOW=1; shift; }
FIRST="(You are working in the project folder $FOLDER as $AGENT."
[ -n "$VFOLDER" ] && FIRST="$FIRST Its memory in the vault is \"$VAULT/$VFOLDER/\": read that folder's index note first, then whatever the task needs."
FIRST="$FIRST The project's own CLAUDE.md and notes apply on top of yours. Source code is read-only until the owner confirms a change, as your rules say.)"
[ $# -gt 0 ] && FIRST="$FIRST $*"

if [ $WINDOW = 1 ]; then
  osascript -e "tell application \"Terminal\"
    activate
    do script \"exec '$C/code.sh' '$NAME'\"
  end tell" >/dev/null && echo "opened a Terminal window: $AGENT in $NAME ($FOLDER)"
  exit 0
fi

cd "$FOLDER" || exit 1
echo "$AGENT in $NAME: $FOLDER"
# --add-dir takes a list, so it goes first and the prompt comes after a single-value flag
exec claude --add-dir "$VAULT" "$H" \
  --settings "$H/.claude/settings.json" \
  --append-system-prompt "$(cat "$H/CLAUDE.md")" \
  --name "$AGENT: $NAME" \
  "$FIRST"
