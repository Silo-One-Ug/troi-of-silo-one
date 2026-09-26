#!/bin/bash
# the agent's toolbox at a glance. Run it whenever you wonder what you can do.
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "TROI'S TOOLBOX  (all in $HERE/ unless noted. Read a script's header for its usage: several of them ACT when run"
echo "with no arguments: backup-vault.sh, report.py, housekeeping.sh, look.sh, look-screen.sh, doctor.sh, ci-status.sh)"
cat <<'TXT'
  browser      mcp__playwright__*  (navigate, click, type, snapshot, screenshot, tabs)  — the browser you drive: Arc when it is installed (the owner's Arc, their logins included: money, deletions and messages need their go-ahead), else a Chrome of your own
  hands        mcp__hands__*  (apps, launch, focus, windows, inspect, find, read, press, set, perform, menu, type, key, wait, click)  — every app by name through
               its accessibility tree, the result read back, no screenshot; risky labels are filed for approval. hands.sh <command> is the same from a terminal (docs/HANDS.md)
  cursor.sh    the pointer/keyboard fallback for what has no name: where | under | move | click | double | right | drag | type | key   (look-screen.sh first; risky buttons need the owner's approval)
  look.sh      one camera photo -> path (then Read it)          look-screen.sh [display]   one screenshot -> path (then Read it)
  apps.sh      list | running | open | focus | quit | kill (asks the owner)
  fs.sh        move | rename | copy | mkdir | reveal | open [app] | undo | trash (asks the owner) | pending     (only inside the file roots in the settings; the vault is one)
  read.py      <file> [--sheet NAME] [--rows N]   a file the Read tool cannot open, as text: xlsx sheets as tables, csv, pptx slides, docx/rtf (textutil), pdf (pdftotext)
  google.sh    mcp | status | setup <client_secret.json> | enable [project] | signin <email>   the owner's Google account as your mcp__google__* tools (Calendar, Gmail, Drive, Docs, Sheets, Tasks, Contacts); sending, sharing and invitations need the owner's go-ahead
  stt.py       <file>   the words in an audio file, with your own ears (run with backtalk/.venv/bin/python; the server keeps one as a worker for the console's voice notes)
  console.sh   go <place> · view face|hands|files|apps|vault · vault show|clear · files <folder> · focus <path> · apps open · images open|close
               modes|routines|approvals|reports open|close · camera open|close · browser open|close · talk column|floating · panel hide|show
               tidy · hint "<text>" · gestures on|off · speak on|off (text only saves ElevenLabs credits) · eyes off|every|watch|screen · wake on|off · face-gate on|off · voice-id off|on|learn
               voice list|kokoro|elevenlabs ["<name>"] · mode "<phrase>"      (console.sh with no arguments prints them all)
  console.sh hands <key> <value>   tune hand tracking (pinch_close, pinch_open, ext, dwell_ms, magnet); press P in the galaxy to sample a pose
  show-image.sh <file> [title] [x] [y]   put a picture (or a video) on the board; without x and y it flows into free space
  ../barehands/bin/board.sh '{"a":"add_card",...}'   add_card | add_img | present | yank | hover | clear | add_ui | ui | layout | tidy   the board (mouse-driven, white, it keeps what is up)
  ../barehands/bin/board-state.sh [events|json]    what is on the board (or the saved scene), and the last clicks on its buttons
  remind.sh    20m "text" | 15:00 "text" | list | cancel N
  brain.sh     status · models · deep | fast · model <name> · effort low|medium|high|xhigh|max · for "<task>" [--deep|--model <name>] [--effort <level>] · back · rest [<level>]   the brain for the job (the names: the voice line's models map)
  share.sh     start | stop | status | build   screen sharing: the Mac's picker, then the shared frames for your eyes (look-screen.sh) and hands (click --share)
  show.py     '<json tree>' [--board|--both] | chart ... | table ... | board "<title>" <op> | board tidy|clear | vocabulary   draw interface from data, in the conversation or as a tile on the board (never an HTML file)
  media.py     now · play [words] · pause · resume · stop · next · prev · volume N · louder · quieter · shuffle on|off · like · movie on|off   Apple Music by voice, and movie mode
  db.py        tail [N] · sessions · stats · star <id|path> · retain   the record: data/troi.db (conversation, cards, approvals, pictures, reports, runs);
               captures (looks, screens, Telegram) go to the Trash after 14 days unless starred
  meeting.py   devices · start <name> [--device NAME] · stop · status · transcribe <file> [--lang xx] [--speakers N] · list   record a meeting, transcript with speaker labels (ElevenLabs Scribe) in data/blobs/meetings/
  ci-status.sh                      CI, PRs, releases per repo of your GitHub org
  pr.py        list [repo] · review <repo> <n> [--post] [--tests] · review <project> --local · show <repo> <n>   a PR review by you, headless, in a throwaway checkout, following the Code Review job; report to data/blobs/reviews/ and Telegram
  code.sh      list · <project> [--window]   a Claude Code session inside a project folder that still boots as the agent (boot file, guard, vault come along)
  servers.py   list · add <name> <ssh-host> [role] · check [name] [--json]   read-only health of the servers in data/servers.json over SSH (the pulse watches every 15 min)
  grafana.py   check · alerts [--all] · rules · silences · query '<PromQL>' [--range 1h] [--show] · logs '<LogQL>' [--since 15m] · dashboards [words] · panel <uid> <id> [--show] · watch   Grafana, read-only (data/grafana.json; the token is the Keychain item grafana); the pulse watches the alerts every minute
  agenda.py    today · next · week · soon [min] · current   the Mac's Calendar app (Google etc.); the pulse warns 15 min before an event
  face.py verify|check              face ID (its own env: .venv-face); learning the owner's face is theirs to do (Modes › Face ID)
  browser-mcp.sh open | which       open the browser with its port 9223 (Arc, or Chrome) / say which it is; the console's Browser page mirrors it live and the owner can click in it
  news.py brief [uganda|world|all] [--n N] [--hours H] [--show] · topic "<words>" · read <url> · videos <outlet> · social <outlet> · sources   the news, Uganda first (news.json lists the outlets)
  pictures.py search "topic" [--n 6] [--show] [--add] · page <url> [--show] · shot <url> [--show] · board <title> <files…> · focus <n|word> · unfocus · clear   research pictures (free, credited) as a grid on the board
  telegram.py photo <file> [caption]   a picture to the owner's phone
  imagine.py "prompt" [--show] [--size 1536x1024] [--from img] · check   make a picture (needs an image key in the Keychain, kept by the owner)
  report.py [--date D] [--no-send] [--no-narrative]   the end-of-day report: commits (who, what, where), CI, notes, files; HTML+PDF in data/blobs/reports/, PDF to Telegram
  backup-vault.sh                   back up now: commit and push the vault, then send the record (troi.db + new files) to the private backup repo
  telegram.py send "text" | say "text"   (run with backtalk/.venv/bin/python)   message / voice-note the owner's phone
  agora_call.py call | check | link   (run with backtalk/.venv/bin/python)      ring the owner for a voice call (needs call_page on https)
  doctor.sh                         health check of every piece, in plain words      housekeeping.sh   rotate logs, send old captures to the Trash
  setup.py services status|restart  the background services (pulse, globe, Telegram, nightly backup)
  gh                                GitHub (and gcloud, docker, kubectl where this Mac has them); the vault (data/console.json "vault") is your memory
TXT
