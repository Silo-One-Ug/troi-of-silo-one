#!/bin/bash
# the agent's remote control for its own console page.
#   console.sh view face|hands          what is behind the panel
#   console.sh vault show|clear         the Vault view (the vault as a wall of cards) / back to the face
#   console.sh tidy                     put the console's panes back in their places
#   console.sh routines open|close      the Routines pane (schedules, reminders, end-of-day reports)
#   console.sh camera open|close        the Eyes pane (the live frame, a look on demand, face ID)
#   console.sh browser open|close       the Browser pane (the agent's Chrome, live, click-through)
#   console.sh images open|close        the picture gallery
#   console.sh panel hide|show          collapse or expand the panel
#   console.sh eyes off|every|watch     the camera
#   console.sh wake on|off              the wake word for hands-free
#   console.sh face-gate on|off         hands-free only while the owner's face is at the camera (turning it off is protected)
#   console.sh voice-id off|on|learn    voice identification
#   console.sh voice list|kokoro|elevenlabs ["<voice name or id>"]   which voice speaks (ElevenLabs needs the key in the Keychain)
#   console.sh mode "<phrase>"          a voice-console phrase, sent once the voice line is idle:
#                                       "push to talk mode" / "go hands free" / "start asking again" /
#                                       "stop asking for permission" / "switch to the deep model" /
#                                       "back to the fast model" / "set effort to low|medium|high|max"
#   console.sh files "<folder>"        open that folder as a galaxy in the Files view
#   console.sh focus "<path>"          light up that file or folder in the galaxy
#   console.sh gestures on|off         hand tracking on the Files galaxy
#   console.sh apps open               the Apps galaxy;  console.sh modes open|close|toggle
#   console.sh hands <pinch_close|pinch_open|ext|dwell_ms|magnet> <value>   tune the hand tracking
#   console.sh hint "<text>"            a line under the typing box
#   console.sh talk column|floating     the conversation as a full column, or a floating pane over every page
#   console.sh approvals open|close     the Approvals page;  console.sh reports open|close   the Reports page
#   console.sh go <place>               any place: conversation library modes routines reports approvals eyes browser
#                                       face hands files apps vault
C="http://127.0.0.1:8796"; J="Content-Type: application/json"
post() { curl -s -m 10 -X POST -H "$J" -H "Origin: $C" -d "$2" "$C$1"; echo; }
case "$1" in
  view)     post /ui "{\"view\":\"$2\"}";;
  vault)    post /ui "{\"vault\":\"$2\"}";;
  tidy)     post /ui "{\"tidy\":true}";;
  routines) post /ui "{\"routines\":\"$2\"}";;
  camera)   post /ui "{\"camera\":\"$2\"}";;
  browser)  post /ui "{\"browser\":\"$2\"}";;
  images)   post /ui "{\"images\":\"$2\"}";;
  panel)    post /ui "{\"panel\":\"$2\"}";;
  files)    post /ui "$(python3 -c 'import json,sys; print(json.dumps({"files": sys.argv[1]}))' "$2")";;
  focus)    post /ui "$(python3 -c 'import json,sys; print(json.dumps({"focus": sys.argv[1]}))' "$2")";;
  gestures) post /ui "{\"gestures\":$([ "$2" = on ] && echo true || echo false)}";;
  apps)     post /ui "{\"apps\":\"$2\"}";;
  modes)    post /ui "{\"modes\":\"$2\"}";;
  talk)     post /ui "{\"talk\":\"$2\"}";;
  approvals) post /ui "{\"approvals\":\"$2\"}";;
  reports)  post /ui "{\"reports\":\"$2\"}";;
  go)       post /ui "{\"go\":\"$2\"}";;
  hands)    post /settings "$(python3 -c 'import json,sys; print(json.dumps({"hands": {sys.argv[1]: float(sys.argv[2])}}))' "$2" "$3")";;
  hint)     post /ui "$(python3 -c 'import json,sys; print(json.dumps({"hint": sys.argv[1]}))' "$2")";;
  eyes)     post /settings "{\"eyes\":\"$2\"}";;
  wake)     post /settings "{\"wake_word\":$([ "$2" = on ] && echo true || echo false)}";;
  face-gate) post /settings "{\"face_gate\":$([ "$2" = on ] && echo true || echo false)}";;
  voice-id) post /settings "{\"voice_id\":\"$2\"}";;
  mode)     post /say "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1], "when": "idle"}))' "$2")";;
  voice)
    case "$2" in
      list)  curl -s -m 20 "$C/voices" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("error") or "\n".join(f"{v[\"name\"]:24} {v[\"voice_id\"]}  {v[\"labels\"]}" for v in d["voices"]))';;
      kokoro) post /settings '{"tts":"kokoro"}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("Kokoro speaks now" if d.get("ok") else d.get("error"))';;
      elevenlabs) python3 - "$3" <<'PY'
import json, sys, urllib.request
C = "http://127.0.0.1:8796"; want = (sys.argv[1] or "").strip().lower()
d = json.load(urllib.request.urlopen(C + "/voices", timeout=20))
if not d.get("ok"): print(d.get("error")); sys.exit(1)
vs = d["voices"]; pick = None
if want: pick = next((v for v in vs if v["voice_id"].lower() == want or v["name"].lower() == want), None) or next((v for v in vs if want in v["name"].lower()), None)
if not pick and not want: pick = next((v for v in vs if v.get("category") == "cloned"), None) or (vs[0] if vs else None)
if not pick: print(f"no voice called {sys.argv[1]!r}; console.sh voice list"); sys.exit(1)
req = urllib.request.Request(C + "/settings", data=json.dumps({"tts": "elevenlabs", "elevenlabs_voice": pick["voice_id"]}).encode(), headers={"Content-Type": "application/json", "Origin": C})
r = json.load(urllib.request.urlopen(req, timeout=10)); print(f"ElevenLabs speaks now: {pick['name']} ({pick['voice_id']})" if r.get("ok") else r.get("error"))
PY
      ;;
      *) echo "console.sh voice list | kokoro | elevenlabs [name or id]";;
    esac;;
  *) sed -n 2,26p "$0";;
esac
