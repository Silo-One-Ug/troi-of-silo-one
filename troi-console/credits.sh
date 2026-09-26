#!/bin/bash
# credits.sh — what is left of the ElevenLabs allowance (the voice, the sound loops), from the agent server, which holds
# the key and asks ElevenLabs at most every five minutes (GET /usage/elevenlabs; --fresh asks again now). One credit is one
# character spoken; a 30-second sound loop (sounds.py) is about 1,200. The Modes page draws the same numbers under the voice.
#   credits.sh [--fresh] [--json]
C="http://127.0.0.1:8796"; q=""; json=0
for a in "$@"; do case "$a" in --fresh) q="?fresh=1";; --json) json=1;; esac; done
out="$(curl -s -m 25 -w '\n%{http_code}' "$C/usage/elevenlabs$q")" || { echo "the agent server is not answering (is Troi up?)"; exit 2; }
code="${out##*$'\n'}"; body="${out%$'\n'*}"
[ "$code" = 404 ] && { echo "the agent server does not know /usage/elevenlabs yet: the paste in the Voice Line note, then a restart"; exit 2; }
[ "$json" = 1 ] && { echo "$body"; exit 0; }
printf '%s' "$body" | python3 -c '
import json, sys, datetime as dt
d = json.load(sys.stdin)
if not d.get("ok"):
    print("ElevenLabs credits: " + (d.get("error") or "unknown")); sys.exit(1)
used, limit, left = int(d.get("used") or 0), int(d.get("limit") or 0), int(d.get("left") or 0)
pct = round(100 * used / limit) if limit else 0
when = dt.datetime.fromtimestamp(d["resets"]).strftime("%-d %b") if d.get("resets") else "?"
tier = d.get("tier") or "?"
low = " · LOW" if limit and left / limit < 0.1 else ""
print(f"ElevenLabs: {left:,} of {limit:,} credits left ({pct}% used) · resets {when} · {tier} tier{low}")
print("one credit is one character spoken; a 30-second sound loop is about 1,200")'
