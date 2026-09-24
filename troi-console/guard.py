#!/usr/bin/env python3
"""The guard. A Claude Code PreToolUse hook: it reads the tool call about to run and blocks it (exit 2) if it would
delete or destroy anything, or reach for the owner's safeguards.

The owner's rules: the agent never deletes. If something must go, the agent files a trash REQUEST
(troi-console/fs.sh trash) and the owner approves it. And the agent never changes its own safeguards: the
owner's secrets in the Keychain, approvals and unlocks, the settings file, the voice and face prints, the record,
Claude Code's settings and hooks, the boot file, and the code that checks all of these. Settings change through
the console server (console.sh), which asks the owner for anything that lowers the guard.

Hard block, whatever the permission mode (ask or auto-approve), in typed and voice sessions alike. Wired in the
repo's .claude/settings.json for Bash, MCP tools, and the file-writing tools.
"""
import json
import re
import sys
from pathlib import Path

BLOCKED = [
    # shell deletion
    (r"(?<![-\w/.])rm\s", "rm"), (r"(?<![-\w/.])rm$", "rm"),
    (r"\brmdir\b", "rmdir"), (r"\bunlink\b", "unlink"), (r"\bshred\b", "shred"),
    (r"\bsrm\b", "srm"), (r"(?<![-\w/.])trash\b", "trash"), (r"\brimraf\b", "rimraf"),
    (r"\bfind\b.*\s-delete\b", "find -delete"), (r"\bxargs\b.*\brm\b", "xargs rm"),
    (r"\bmv\b.*\s/dev/null", "mv to /dev/null"), (r"(?<![\w])dd\b.*\bof=", "dd"),
    (r"\bmkfs\b", "mkfs"), (r"\bdiskutil\s+(erase|partition|reformat)", "diskutil erase"),
    (r"(?<![\w])truncate\s", "truncate"), (r"(^|[;&|]\s*):\s*>\s*\S", ":> file"),
    # code that deletes
    (r"\brmtree\b", "shutil.rmtree"), (r"\bos\.(remove|unlink|rmdir|removedirs)\b", "os.remove"),
    (r"\.unlink\(", "Path.unlink"), (r"\b(unlinkSync|rmSync|rmdirSync|fs\.rm|fs\.unlink)\b", "fs.rm"),
    (r"\bFile\.delete\b|\bFileUtils\.rm", "File.delete"),
    # git history and working-tree destruction
    (r"\bgit\s+clean\b", "git clean"), (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+push\b.*(\s-f\b|--force)", "git push --force"), (r"\bgit\s+branch\s+(-D|--delete|-d)\b", "git branch delete"),
    (r"\bgit\s+checkout\s+--\s", "git checkout -- (discards edits)"), (r"\bgit\s+restore\b", "git restore (discards edits)"),
    (r"\bgit\s+stash\s+(drop|clear)\b", "git stash drop"), (r"\bgit\s+tag\s+-d\b", "git tag -d"),
    (r"\bgit\s+push\b.*\s--delete\b", "git push --delete"), (r"\bgit\s+push\b.*\s:\S", "git push :branch"),
    # databases
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|USER|ROLE)\b", "SQL DROP"),
    (r"\bDELETE\s+FROM\b", "SQL DELETE"), (r"\bTRUNCATE\s+(TABLE\s+)?\w", "SQL TRUNCATE"),
    (r"\bdropdb\b", "dropdb"), (r"\bmigrate:(fresh|reset)\b", "migrate:fresh"), (r"\bdb:wipe\b", "db:wipe"),
    (r"\bflushall\b|\bflushdb\b", "redis flush"),
    # infrastructure and services
    (r"\bkubectl\s+delete\b", "kubectl delete"), (r"\bdocker\s+(rm|rmi|system\s+prune|volume\s+(rm|prune)|container\s+prune|image\s+prune|stack\s+rm|service\s+rm)\b", "docker rm"),
    (r"\bgcloud\b.*\bdelete\b", "gcloud delete"), (r"\bgsutil\s+(rm|rb)\b", "gsutil rm"),
    (r"\bgh\s+(repo|release|pr|issue|gist|secret|variable)\s+delete\b", "gh delete"),
    (r"\bbrew\s+(uninstall|remove|rm)\b", "brew uninstall"), (r"\bdefaults\s+delete\b", "defaults delete"),
    (r"\bosascript\b.*\bdelete\b", "osascript delete"),
    (r"(?<![-\w/.])cliclick\b", "cliclick directly (use troi-console/cursor.sh, which has the guards)"),
    (r"\bcurl\b.*-X\s*DELETE\b", "HTTP DELETE"), (r"\bhttp\s+DELETE\b", "HTTP DELETE"),
]
TOOL_NAME_BLOCK = re.compile(r"(delete|remove|trash|destroy|purge|wipe|drop)", re.I)

ROOT = Path(__file__).resolve().parents[1]
# the safeguards, as they appear in a command line
GUARDED = (r"(data/console\.json|data/prints\b|data/troi\.db|\.claude/settings|(?<![\w-])CLAUDE\.md"
           r"|troi-console/(guard|keychain|server|voice|telegram|setup|paths)\.py|troi-console/templates/)")
# a write reaches a safeguard when the safeguard is its target, not whenever both appear in one command line
# (so `telegram.py send "npm install failed"` and `setup.py services install` stay allowed)
WRITES = [r">{1,2}\s*[\"']?[^\s;&|]*" + GUARDED,                                                  # a redirect into one
          r"\b(tee|cp|mv|ln|install|rsync|ditto|truncate|patch)\b[^;&|\n]*" + GUARDED,              # a file tool with one as an argument
          r"\bsed\b[^;&|\n]*\s-i[^;&|\n]*" + GUARDED + r"|\bperl\s+-\w*i[^;&|\n]*" + GUARDED]  # edited in place
CODE_WRITES = r"write_text|\.write\(|\.dump\(|open\([^)]*[\"'][wa+]"                              # inline code that writes, with one named
SAFEGUARDS = [
    (r"\b(find|add|delete|set)-generic-password\b|\bdump-keychain\b|\bsecurity\s+(export|unlock-keychain)\b", "the owner's secrets in the Keychain"),
    (r"keychain\.py|\bimport\s+keychain\b|\bkeychain\.(get|put)\(", "the owner's secrets in the Keychain"),
    (r"(127\.0\.0\.1|localhost):8796/(approve|unlock|keychain|setup/|face-verify)", "the owner's approvals, unlocks and setup"),
    (r"troi-console/\.typed\b|(^|[\s>\"'])\.typed\b", "the voice line's typing pipe"),
    (r"\bface\.py\s+enrol\b", "the owner's face print (learning a face is a protected change: the owner does it in Modes)"),
    (r"\bsqlite3\b[^|;&]*troi\.db(?=[^|;&]*\b(UPDATE|INSERT|REPLACE|ALTER|CREATE|ATTACH|VACUUM)\b)", "the agent's record (troi.db)"),
]


def guarded_path(fp):
    """Is this file one of the safeguards (for Edit, Write, MultiEdit, NotebookEdit)?"""
    try:
        p = Path(str(fp)).expanduser().resolve()
    except Exception:
        return False
    home = Path.home() / ".claude"
    tc = ROOT / "troi-console"
    return (p == ROOT / "CLAUDE.md" or p.parent == ROOT / "data" and (p.name == "console.json" or p.name.startswith("troi.db"))
            or ROOT / "data" / "prints" in p.parents or ROOT / ".claude" in p.parents or p in (home / "settings.json", home / "settings.local.json")
            or p in [tc / f"{n}.py" for n in ("guard", "keychain", "server", "voice", "telegram", "setup", "paths")] or tc / "templates" in p.parents)


def refuse(what):
    print(f"BLOCKED by the guard: that reaches {what}, which only the owner changes. Tell the owner what you wanted and why; "
          f"they do it themselves (the console's Modes, Approvals or the welcome), or approve it when you file it.", file=sys.stderr)
    return 2


def main():
    try:
        call = json.load(sys.stdin)
    except Exception:
        return 0
    name = str(call.get("tool_name", ""))
    inp = call.get("tool_input") or {}
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        # the sanctioned removal path: fs.sh only FILES a request; the console server
        # performs nothing until the owner approves, so this must never be blocked
        if "troi-console/fs.sh" in cmd and not re.search(r"(?<![-\w/.])rm\s|\brmdir\b|\bgit\s+(clean|reset\s+--hard)", cmd):
            return 0
        for pat, label in BLOCKED:
            if re.search(pat, cmd, re.M):
                print(f"BLOCKED by the deletion guard ({label}). You never delete. If the owner wants it gone, run "
                      f"{Path(__file__).resolve().parent}/fs.sh trash \"<path>\" \"<why>\" (files an approval request) and say it is waiting.",
                      file=sys.stderr)
                return 2
        for pat, what in SAFEGUARDS:
            if re.search(pat, cmd, re.M | re.I):
                return refuse(what)
        if any(re.search(w, cmd, re.M) for w in WRITES) or (re.search(GUARDED, cmd) and re.search(CODE_WRITES, cmd)):
            return refuse("the agent's safeguards (settings, prints, record, boot file or guard code)")
    elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if guarded_path(inp.get("file_path") or inp.get("notebook_path") or ""):
            return refuse("the agent's safeguards (settings, prints, record, boot file or guard code)")
    elif name.startswith("mcp__") and TOOL_NAME_BLOCK.search(name):
        print(f"BLOCKED by the deletion guard: the tool {name} deletes. Tell the owner what you wanted to remove and let them do it.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
