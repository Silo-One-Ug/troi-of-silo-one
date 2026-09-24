#!/bin/bash
# the agent's toolbox at a glance. Run it whenever you wonder what you can do.
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "TROI'S TOOLBOX  (all in $HERE/ unless noted; every script prints its own usage with no arguments)"
cat <<'TXT'
  browser      mcp__playwright__*  (navigate, click, type, snapshot, screenshot, tabs)  — a Chrome you control; the owner's logins are not in it
  cursor.sh    the real pointer/keyboard, any app: where | under | move | click | double | right | drag | type | key   (look-screen.sh first; risky buttons need the owner's approval)
  look.sh      one camera photo -> path (then Read it)          look-screen.sh   one screenshot -> path (then Read it)
  apps.sh      list | running | open | focus | quit | kill(asks the owner)
  fs.sh        move | rename | copy | mkdir | reveal | open [app] | undo | trash(asks the owner) | pending     (only inside the file roots in the settings, the vault and the agent folder)
  console.sh   view face|hands|files|apps|vault · vault show|clear · tidy · routines open|close · images open · apps open · files <folder> · focus <path> · gestures on|off · eyes off|every|watch · wake on|off · face-gate on|off · voice-id · mode "<phrase>" · panel hide|show · hint
  console.sh hands <key> <value>   tune hand tracking (pinch_close, pinch_open, ext, dwell_ms, magnet); press P in the galaxy to sample a pose
  show-image.sh <file> [title]      put a picture / 3D model on the hands board
  barehands/bin/board.sh '{"a":"present",...}'   and   board-state.sh      the hands board itself
  remind.sh    20m "text" | 15:00 "text" | list | cancel N
  show.py     '<json tree>' | chart ... | table ... | vocabulary   draw interface in the conversation: charts, tables, stats, galleries (never an HTML file)
  media.py     now · play [words] · pause · resume · next · prev · volume N · louder · quieter · shuffle on|off · like · movie on|off   Apple Music by voice, and movie mode
  db.py        tail [N] · sessions · stats     the record: data/troi.db (conversation, cards, approvals, pictures, reports, runs)
  meeting.py   devices · start <name> [--device NAME] · stop · status · transcribe <file> [--lang xx] [--speakers N] · list   record a meeting, transcript with speaker labels (ElevenLabs Scribe) in data/blobs/meetings/
  ci-status.sh                      CI, PRs, releases per repo of your GitHub org
  pr.py        list [repo] · review <repo> <n> [--post] [--tests] · review <project> --local · show <repo> <n>   a PR review by you, headless, in a throwaway checkout; report to data/blobs/reviews/ and Telegram
  code.sh      list · <project> [--window]   a Claude Code session inside a project folder that still boots as the agent (boot file, guard, vault come along)
  servers.py   list · add <name> <ssh-host> [role] · check [name] [--json]   read-only health of your servers over SSH (the pulse watches every 15 min)
  agenda.py  today · next · week · soon [min] · current   the Mac's Calendar app (Google etc.); the pulse warns 15 min before an event
  face.py enrol|verify|check        face ID (its own env: .venv-face); the lock and the settings guard can check your face
  browser-mcp.sh chrome             open your own Chrome (port 9223); the Browser pane on the console mirrors it live and the owner can click in it
  news.py brief [uganda|world|all] [--show] · topic "<words>" · read <url> · videos <outlet> · social <outlet>   the news, Uganda first (news.json lists the outlets)
  pictures.py search "topic" [--n 6] [--show] · page <url> [--show] · shot <url> [--show] · board <title> <files…> · focus <n|word> · unfocus · clear   research pictures (free, credited) as a grid on the board
  telegram.py photo <file> [caption]   a picture to the owner's phone
  imagine.py "prompt" [--show] [--size 1536x1024] [--from img]   make a picture (needs an image key in the keychain; imagine.py check)
  report.py [--date D] [--no-send]  the end-of-day report: commits (who, what, where), CI, notes, files; HTML+PDF in reports/, PDF to Telegram        backup-vault.sh   push the vault + this code now
  telegram.py send "text" | say "text"   (run with backtalk/.venv/bin/python)   message / voice-note the owner's phone
  agora_call.py call | check          (run with backtalk/.venv/bin/python)      ring the owner for a voice call
  doctor.sh                         health check of every piece, in plain words      housekeeping.sh   rotate logs, thin old captures
  gh, gcloud, docker, kubectl         installed and logged in; the vault at ~/the agent-Vault is your memory
TXT
