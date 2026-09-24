#!/usr/bin/env python3
"""the agent's hands on the music, and a movie mode. Apple Music through AppleScript; stdlib only.

  media.py now                      what is playing: {"state","name","artist","album","volume"} (JSON)
  media.py play [words]             resume, or play the library's best match for the words: a playlist
                                    by name, then tracks whose genre, artist, album or name contain them.
                                    Nothing in the library -> opens Apple Music's search for the words
                                    (the catalog is not scriptable) and says so, so ask the owner to tap.
  media.py pause | resume | next | prev | stop
  media.py volume <0-100> | louder | quieter
  media.py shuffle on|off
  media.py like                     mark the current track as loved
  media.py movie on|off             movie mode: push to talk (the TV can never wake the agent), cues
                                    off, the console panel hidden and dimmed; "off" puts it all back.
                                    Hands-free listening is a protected setting, so after "off" the
                                    owner says "go hands free" themselves if they want it back.

Music dips while the agent talks when "duck_music" is true in console.json (voice.py does the
dipping, for Spotify and Apple Music alike).
"""
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import db as _DB  # noqa: E402  (small documents live in troi.db)

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
CONSOLE = P.CONFIG
BACKTALK = HOME / "backtalk" / "backtalk.json"
MOVIE = _DB.doc("movie")
try:                                    # the playlist the agent fills for "play some <words>", named after the agent
    QUEUE = json.loads((P.BACKTALK / "backtalk.json").read_text()).get("name", "Troi") + " Queue"
except Exception:
    QUEUE = "Troi Queue"
PORT = 8796


def osa(script, timeout=8):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "AppleScript failed")
    return r.stdout.strip()


def music(script, timeout=8):
    return osa(f'tell application "Music"\n{script}\nend tell', timeout)


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def post(path, payload):
    import urllib.request
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3).read()
        return True
    except Exception:
        return False


def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception: return {}


def save(p, d):
    Path(p).write_text(json.dumps(d, indent=2))


def now():
    st = music("get player state")
    out = {"state": st}
    if st in ("playing", "paused"):
        try:                                     # a separator no tag contains; names can hold commas
            out.update(dict(zip(("name", "artist", "album"),
                                music('get (name of current track) & "|~|" & (artist of current track) & "|~|" & (album of current track)').split("|~|", 2))))
        except RuntimeError:
            pass
    try: out["volume"] = int(music("get sound volume"))
    except Exception: pass
    return out


def play(words):
    if not words:
        music("play"); return f"playing: {describe()}"
    w = words.strip()
    # 1. a playlist whose name contains the words
    names = [n for n in music("get name of every user playlist").split(", ") if n and n != QUEUE]
    hit = [n for n in names if w.lower() in n.lower()]
    if hit:
        music(f"play user playlist {q(hit[0])}"); return f"playing the playlist {hit[0]}: {describe()}"
    # 2. tracks whose genre / artist / album / name contain the words
    n = 0
    for field in ("genre", "artist", "album", "name"):
        n = int(music(f"get count of (every track of library playlist 1 whose {field} contains {q(w)})") or 0)
        if n: break
    if n:
        if QUEUE not in music("get name of every user playlist").split(", "):
            music(f"make new user playlist with properties {{name:{q(QUEUE)}}}")
        music(f"delete every track of user playlist {q(QUEUE)}")
        music(f"duplicate (every track of library playlist 1 whose {field} contains {q(w)}) to user playlist {q(QUEUE)}")
        music(f"set shuffle enabled to true\nplay user playlist {q(QUEUE)}")
        return f"playing {n} tracks matching {w!r} ({field}), shuffled: {describe()}"
    # 3. not in the library: open the catalog search for the owner to tap
    subprocess.run(["open", "music://music.apple.com/search?term=" + urllib.parse.quote(w)], check=False)
    return f"nothing in the library matches {w!r}; opened Apple Music's search for it. Ask the owner to tap what they want (the catalog can't be played by script)."


STREAMING = ("Music did not start: those are Apple Music streaming tracks, and by script only local or downloaded "
             "tracks play (streaming needs the Mac signed in with an active Apple Music subscription). "
             "Ask the owner to press play in the Music app, or pick something from the local library.")


def describe():
    import time; time.sleep(1.2)                 # Music needs a moment to start before it reports a track
    d = now()
    if d["state"] == "stopped": return STREAMING
    return f"{d.get('name', '?')} by {d.get('artist', '?')}" if d.get("name") else d["state"]


def movie(on):
    cfg = load(CONSOLE); bt = load(BACKTALK)
    if on:
        prev = {"cues": cfg.get("cues", True), "mic_mode": bt.get("mic_mode", "ptt")}
        save(MOVIE, prev)
        if prev["mic_mode"] == "open":
            post("/say", {"text": "push to talk mode", "when": "idle"})
        cfg["cues"] = False; save(CONSOLE, cfg)
        post("/ui", {"panel": "hide", "dim": True, "cues": False, "hint": "Movie mode: push to talk, cues off, console dimmed. Say \"movie mode off\" when the credits roll."})
        return "movie mode on: push to talk, cues off, console hidden and dimmed" + (" (was hands-free: say \"go hands free\" to get it back after)" if prev["mic_mode"] == "open" else "")
    prev = load(MOVIE)
    cfg["cues"] = prev.get("cues", True); save(CONSOLE, cfg)
    post("/ui", {"panel": "show", "dim": False, "cues": cfg["cues"], "hint": "Movie mode off."})
    MOVIE.unlink(missing_ok=True)
    return "movie mode off: cues and console back" + (". Hands-free was on before: say \"go hands free\" if you want it back" if prev.get("mic_mode") == "open" else "")


def main(a):
    c = a[0] if a else "help"; rest = " ".join(a[1:])
    try:
        if c == "now": print(json.dumps(now()))
        elif c == "play": print(play(rest))
        elif c == "pause": music("pause"); print("paused")
        elif c == "resume": music("play"); print(f"playing: {describe()}")
        elif c == "stop": music("stop"); print("stopped")
        elif c == "next": music("next track"); print(f"next: {describe()}")
        elif c == "prev": music("previous track"); print(f"previous: {describe()}")
        elif c == "volume":
            music(f"set sound volume to {max(0, min(100, int(rest)))}"); print(f"volume {now().get('volume')}")
        elif c in ("louder", "quieter"):
            v = now().get("volume", 50); v = v + 15 if c == "louder" else v - 15
            music(f"set sound volume to {max(0, min(100, v))}"); print(f"volume {now().get('volume')}")
        elif c == "shuffle": music(f"set shuffle enabled to {'true' if rest == 'on' else 'false'}"); print(f"shuffle {rest}")
        elif c == "like": music("set loved of current track to true"); print(f"loved: {describe()}")
        elif c == "movie": print(movie(rest.strip() == "on"))
        else: print(__doc__.strip())
    except RuntimeError as e:
        print(f"Music says: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
