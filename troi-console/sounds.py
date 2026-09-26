#!/usr/bin/env python3
"""sounds.py: the room's soundscape while the owner works (Silo One). A mood is a 30-second seamless loop made ONCE by
ElevenLabs Sound Effects (about 1,200 credits: 40 a second) and kept in data/blobs/sounds/<mood>.mp3, where the Library
shows it under Sounds; after that it plays for nothing. A small player loops it on the Mac's output, follows this
file's orders live, and dips to a third while the agent speaks (it watches backtalk/.voice_state), the way Apple Music
ducks. Actual music stays with media.py (Apple Music).
  sounds.py play <mood>            play a mood (made with ElevenLabs the first time, then from the kept loop)
  sounds.py stop                   quiet
  sounds.py volume <0-100>         the player's volume (default 40, remembered); the Mac's own volume still applies
  sounds.py status [--json]        what plays, the volume, whether the player runs, the moods
  sounds.py list                   the moods, ready or not, with their prompts
  sounds.py add <mood> "<prompt>" [--label "<Label>"]   a mood of the owner's (data/sounds.json)
  sounds.py regen <mood>           make a mood's loop again (credits again); the old loop goes to data/trash/<date>/
The Modes page's Mood switch and its volume slider come here through the board server (GET/POST /sounds); the spoken
"play rain sounds" / "sounds off" reach the agent as requests and it runs these. ffmpeg (Homebrew) decodes the MP3
into a WAV in the cache for the player, which runs in backtalk's venv (sounddevice, soundfile, numpy).
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths as P  # noqa: E402

LOOPS = P.BLOBS / "sounds"                 # the kept loops (mp3, one per mood): the record's Sounds
WAVS = P.CACHE / "sounds"                  # the decoded loops the player reads (disposable, remade from the mp3)
STATE = P.CACHE / "sounds.json"            # the player's orders and its report: mood, file, volume, pid, making, error
USER = P.DATA / "sounds.json"              # the owner's moods and the volume to come back to
LOG = P.LOGS / "sounds.log"
VOICE_STATE = P.BACKTALK / ".voice_state"  # "speaking" while the agent talks: the loop dips
VENV = P.BACKTALK / ".venv" / "bin" / "python"
SECONDS = 30                                # the longest loop ElevenLabs makes; 40 credits a second
CREDITS = 40 * SECONDS
DUCK = 0.33                                 # the gain while the agent speaks
DEFAULT_VOLUME = 40
NAME_RE = re.compile(r"[a-z0-9_-]{1,32}")

MOODS = {
    "focus":  {"label": "Focus",  "prompt": "soft steady rain on a window, gentle and even, no thunder, no voices; a calm ambient loop"},
    "calm":   {"label": "Calm",   "prompt": "distant ocean waves rolling slowly onto a sandy beach, soothing and even; a calm ambient loop"},
    "cafe":   {"label": "Café",   "prompt": "a quiet coffee shop: the soft murmur of a few people, cups set down, a distant espresso machine, no music; an ambient loop"},
    "forest": {"label": "Forest", "prompt": "a forest in the morning: birdsong, leaves rustling in a light breeze, a distant stream; an ambient loop"},
    "night":  {"label": "Night",  "prompt": "a warm summer night outdoors: crickets, a faint breeze, far-off frogs; a calm ambient loop"},
    "storm":  {"label": "Storm",  "prompt": "heavy rain with slow rolling thunder far away, steady and enveloping; an ambient loop"},
    "fire":   {"label": "Fire",   "prompt": "a crackling fireplace: soft pops, embers, a gentle steady burn, no talking; an ambient loop"},
    "hum":    {"label": "Hum",    "prompt": "soft brown noise like a distant fan, smooth, constant and low, no changes; an ambient loop"},
}


def _log(s):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(f"{dt.datetime.now():%F %T} {s}\n")
    except Exception:
        pass


def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def _write(p, d):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp"); tmp.write_text(json.dumps(d, indent=2)); os.replace(tmp, p)


def moods():
    """The built-in moods plus the owner's (data/sounds.json: "moods": name -> {label, prompt})."""
    out = {k: dict(v) for k, v in MOODS.items()}
    for k, v in (_read(USER, {}).get("moods") or {}).items():
        if isinstance(v, dict) and v.get("prompt") and NAME_RE.fullmatch(k):
            out[k] = {"label": v.get("label") or k.title(), "prompt": v["prompt"]}
    return out


def loop_path(mood): return LOOPS / f"{mood}.mp3"
def wav_path(mood): return WAVS / f"{mood}.wav"
def loop_ready(mood): return loop_path(mood).is_file() and loop_path(mood).stat().st_size > 1000


def state(): return _read(STATE, {})


def set_state(**kv):
    d = state(); d.update(kv); _write(STATE, d); return d


def saved_volume():
    try:
        return max(0, min(100, int(_read(USER, {}).get("volume", DEFAULT_VOLUME))))
    except Exception:
        return DEFAULT_VOLUME


def alive(pid):
    """Is the player with this pid running? A ps lookup: nothing is signalled."""
    if not pid:
        return False
    try:
        return subprocess.run(["/bin/ps", "-p", str(int(pid)), "-o", "pid="], capture_output=True, text=True, timeout=5).stdout.strip() != ""
    except Exception:
        return False


def status_dict():
    st = state(); ms = moods(); running = alive(st.get("pid"))
    playing = st.get("mood") if running and st.get("mood") else ""
    return {"ok": True, "playing": playing, "label": ms.get(playing, {}).get("label", playing) if playing else "",
            "making": st.get("making") or "", "volume": int(st.get("volume", saved_volume())), "player": running,
            "error": st.get("error") or "", "credits_per_loop": CREDITS, "seconds": SECONDS,
            "moods": [{"name": k, "label": v["label"], "prompt": v["prompt"], "ready": loop_ready(k)} for k, v in ms.items()]}


# ---------------------------------------------------------------- making a loop (ElevenLabs Sound Effects, once)
def make_loop(mood, prompt):
    """Ask ElevenLabs for a seamless loop of SECONDS seconds and keep it (mp3, in the record). Costs CREDITS."""
    import keychain as KC
    key = KC.get("elevenlabs") or os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        set_state(making="", error="no ElevenLabs key in the Keychain yet")
        raise SystemExit("no ElevenLabs key in the Keychain yet: the welcome's Extras step, or Modes > Keys, is the owner's to fill")
    LOOPS.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"text": prompt, "duration_seconds": SECONDS, "loop": True, "prompt_influence": 0.3,
                       "model_id": "eleven_text_to_sound_v2"}).encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"}, method="POST")
    set_state(making=mood, error="")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            mp3 = r.read()
    except urllib.error.HTTPError as e:
        msg = e.read()[:300].decode(errors="replace")
        set_state(making="", error=f"ElevenLabs refused the {mood} loop: {e.code} {msg}")
        raise SystemExit(f"ElevenLabs refused the {mood} loop: {e.code} {msg}")
    except Exception as e:
        set_state(making="", error=f"ElevenLabs did not answer: {str(e)[:120]}")
        raise SystemExit(f"ElevenLabs did not answer: {e}")
    if len(mp3) < 1000:
        set_state(making="", error="ElevenLabs sent an empty loop")
        raise SystemExit("ElevenLabs sent an empty loop")
    loop_path(mood).write_bytes(mp3)
    set_state(making="")
    _log(f"made {mood}: {len(mp3)} bytes of mp3 in {time.time() - t0:.0f}s, {CREDITS} credits")
    try:
        import db
        db.blob_add(str(loop_path(mood)), kind="sounds", title=f"{moods()[mood]['label']} loop",
                    meta={"mood": mood, "prompt": prompt, "credits": CREDITS, "seconds": SECONDS, "made": time.time()})
    except Exception as e:
        _log(f"record: {e}")
    try:                                                              # the credits meter catches up
        urllib.request.urlopen("http://127.0.0.1:8796/usage/elevenlabs?fresh=1", timeout=8).read()
    except Exception:
        pass
    return loop_path(mood)


def decoded(mood):
    """The WAV the player reads (48 kHz stereo), decoded from the kept mp3 by ffmpeg when missing or older."""
    src, dst = loop_path(mood), wav_path(mood)
    if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime and dst.stat().st_size > 1000:
        return dst
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if not Path(ff).exists():
        raise SystemExit("ffmpeg is missing (brew install ffmpeg): it decodes the loops for the player")
    WAVS.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.wav")
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(src), "-ar", "48000", "-ac", "2", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0 or not tmp.is_file():
        raise SystemExit(f"ffmpeg could not decode the {mood} loop: {r.stderr[:200]}")
    os.replace(tmp, dst)
    return dst


# ---------------------------------------------------------------- the player
def _speaking():
    try:
        return VOICE_STATE.read_text().strip() == "speaking"
    except Exception:
        return False


def _open(sd, sr, ch, cb):
    for attempt in (1, 2):
        try:
            s = sd.OutputStream(samplerate=sr, channels=ch, dtype="float32", blocksize=1024, callback=cb)
            s.start()
            return s
        except Exception as e:
            _log(f"output would not open ({attempt}): {e}")
            try:
                sd._terminate(); sd._initialize()                     # the mouth's cure: PortAudio's device list went stale
            except Exception:
                pass
            time.sleep(0.5)
    return None


def daemon():
    """Loop the state's file on the default output; follow the state file (mood, volume, stop); dip while the agent speaks."""
    try:
        import numpy as np
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        if VENV.exists() and Path(sys.executable).resolve() != VENV.resolve():
            os.execv(str(VENV), [str(VENV), __file__, "_daemon"])
        raise SystemExit("the player needs backtalk's venv (sounddevice, soundfile, numpy)")
    me = os.getpid()
    set_state(pid=me, error="")
    _log(f"player up, pid {me}")
    cur = {"file": None, "gen": None, "buf": None, "pos": 0, "gain": 0.0, "target": 0.0, "ramp": 12000.0}
    lock = threading.Lock()

    def cb(out, frames, t, status):
        with lock:
            buf = cur["buf"]
            if buf is None:
                out.fill(0); return
            n = len(buf); pos = cur["pos"]
            idx = (pos + np.arange(frames)) % n
            g0 = cur["gain"]; g1 = g0 + (cur["target"] - g0) * min(1.0, frames / max(1.0, cur["ramp"]))
            out[:] = buf[idx] * np.linspace(g0, g1, frames, dtype="float32")[:, None]
            cur["gain"] = float(g1); cur["pos"] = int((pos + frames) % n)

    stream = None; sr_open = None
    while True:
        st = state()
        if st.get("pid") != me:
            _log("another player took over"); break
        mood = st.get("mood") or ""; path = st.get("file") or ""; gen = st.get("gen")
        if not mood or not path or not Path(path).is_file():                  # asked for quiet: fade, then leave
            with lock:
                cur["target"] = 0.0; cur["ramp"] = 4800.0
            time.sleep(0.6)
            again = state()
            if again.get("pid") == me and again.get("mood") and again.get("file"):
                continue                                                      # a new order arrived during the fade
            break
        if (path, gen) != (cur["file"], cur["gen"]):
            try:
                data, sr = sf.read(path, dtype="float32", always_2d=True)
            except Exception as e:
                set_state(error=f"could not read {Path(path).name}: {str(e)[:100]}", mood=""); _log(f"read failed: {e}"); break
            if stream is None or sr != sr_open or data.shape[1] != stream.channels:
                if stream is not None:
                    try:
                        stream.stop(); stream.close()
                    except Exception:
                        pass
                stream = _open(sd, sr, data.shape[1], cb); sr_open = sr
                if stream is None:
                    set_state(error="no output device would open", mood=""); break
            with lock:
                cur["buf"] = data; cur["pos"] = 0; cur["file"] = path; cur["gen"] = gen; cur["gain"] = 0.0
            _log(f"playing {mood} ({len(data) / sr:.0f}s at {sr} Hz)")
        vol = max(0, min(100, int(st.get("volume", DEFAULT_VOLUME))))
        target = (vol / 100.0) ** 1.5 * (DUCK if _speaking() else 1.0)        # a gentle curve: 40 feels like 40
        with lock:
            cur["target"] = float(target); cur["ramp"] = float((sr_open or 48000) * 0.25)
        time.sleep(0.25)
    try:
        if stream is not None:
            stream.stop(); stream.close()
    except Exception:
        pass
    if state().get("pid") == me:
        set_state(pid=0)
    _log("player down")


# ---------------------------------------------------------------- the commands
def cmd_play(mood):
    ms = moods()
    if mood not in ms:
        raise SystemExit(f"no mood called {mood}; the moods: {', '.join(ms)} (sounds.py add makes a new one)")
    made = False
    if not loop_ready(mood):
        print(f"making the {ms[mood]['label']} loop with ElevenLabs ({CREDITS:,} credits, once)…", flush=True)
        make_loop(mood, ms[mood]["prompt"]); made = True
    wav = decoded(mood)
    st = state(); vol = int(st.get("volume", saved_volume()))
    set_state(mood=mood, file=str(wav), volume=vol, making="", error="", since=time.time(), gen=int(st.get("gen") or 0) + 1)
    if not alive(st.get("pid")):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        py = str(VENV) if VENV.exists() else sys.executable
        with LOG.open("a") as lg:
            subprocess.Popen([py, __file__, "_daemon"], stdout=lg, stderr=lg, start_new_session=True, cwd=str(HERE))
        for _ in range(24):
            time.sleep(0.25)
            s2 = state()
            if s2.get("error") or alive(s2.get("pid")):
                break
    err = state().get("error")
    if err:
        raise SystemExit(f"the player could not start: {err}")
    print(f"{ms[mood]['label']} playing from the Mac at volume {vol}"
          + (f"; the loop was made just now ({CREDITS:,} credits)" if made else "")
          + "; it dips while the agent speaks. sounds.py stop for quiet.")


def cmd_stop():
    st = state()
    was = st.get("mood") if alive(st.get("pid")) else ""
    set_state(mood="", making="")
    print(f"quiet; {moods().get(was, {}).get('label', was)} stopped" if was else "nothing was playing")


def cmd_volume(n):
    try:
        n = max(0, min(100, int(n)))
    except ValueError:
        raise SystemExit("sounds.py volume 0-100")
    set_state(volume=n)
    u = _read(USER, {}); u["volume"] = n; _write(USER, u)
    print(f"mood volume {n}" + ("" if alive(state().get("pid")) else " (nothing playing; it applies to the next play)"))


def cmd_status(as_json=False):
    d = status_dict()
    if as_json:
        print(json.dumps(d)); return
    if d["making"]:
        print(f"making the {d['making']} loop with ElevenLabs…")
    elif d["playing"]:
        print(f"{d['label']} playing at volume {d['volume']} (player pid {state().get('pid')})")
    else:
        print(f"quiet; volume {d['volume']}" + (f"; last error: {d['error']}" if d["error"] else ""))
    print("ready: " + (", ".join(m["name"] for m in d["moods"] if m["ready"]) or "none yet") + " · not yet made: "
          + (", ".join(m["name"] for m in d["moods"] if not m["ready"]) or "none"))


def cmd_list():
    for m in status_dict()["moods"]:
        print(f"  {m['name']:<8} {m['label']:<8} {'ready' if m['ready'] else f'not made ({CREDITS:,} credits on first play)':<38} {m['prompt']}")


def cmd_add(name, prompt, label=""):
    if not NAME_RE.fullmatch(name or ""):
        raise SystemExit("a mood's name is lowercase letters, digits, - or _, up to 32 characters")
    if not prompt or len(prompt) < 8:
        raise SystemExit("give the sound in words, e.g. \"a quiet library: pages turning, a distant clock; an ambient loop\"")
    u = _read(USER, {}); u.setdefault("moods", {})[name] = {"label": label or name.title(), "prompt": prompt}; _write(USER, u)
    print(f"{name} added ({label or name.title()}); its loop is made on first play ({CREDITS:,} credits)")


def cmd_regen(mood):
    ms = moods()
    if mood not in ms:
        raise SystemExit(f"no mood called {mood}")
    if loop_ready(mood):
        keep = P.TRASH / dt.date.today().isoformat(); keep.mkdir(parents=True, exist_ok=True)
        dst = keep / f"sounds-{mood}-{int(time.time())}.mp3"
        shutil.move(str(loop_path(mood)), str(dst)); print(f"the old loop is in {dst}")
    make_loop(mood, ms[mood]["prompt"])
    st = state()
    if st.get("mood") == mood and alive(st.get("pid")):
        set_state(file=str(decoded(mood)), gen=int(st.get("gen") or 0) + 1)
    print(f"{ms[mood]['label']} made again ({CREDITS:,} credits)")


def main(a):
    if not a or a[0] in ("-h", "--help", "help"):
        print(__doc__.strip()); return
    cmd, rest = a[0], a[1:]
    if cmd == "_daemon": daemon()
    elif cmd == "play": cmd_play(rest[0] if rest else "")
    elif cmd == "stop": cmd_stop()
    elif cmd == "volume": cmd_volume(rest[0] if rest else "")
    elif cmd == "status": cmd_status("--json" in rest)
    elif cmd == "list": cmd_list()
    elif cmd == "add":
        label = rest[rest.index("--label") + 1] if "--label" in rest and rest.index("--label") + 1 < len(rest) else ""
        words = [x for i, x in enumerate(rest) if x != "--label" and not (i > 0 and rest[i - 1] == "--label")]
        cmd_add(words[0] if words else "", " ".join(words[1:]), label)
    elif cmd == "regen": cmd_regen(rest[0] if rest else "")
    else:
        raise SystemExit(f"sounds.py: no command {cmd}; sounds.py --help")


if __name__ == "__main__":
    main(sys.argv[1:])
