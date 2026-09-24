#!/usr/bin/env python3
"""the agent's meeting ears: record an online meeting, then turn it into a speaker-labelled
transcript with ElevenLabs Scribe. Stdlib only (ffmpeg and curl do the heavy lifting).

  meeting.py devices                         audio inputs ffmpeg can record from
  meeting.py start <name> [--device NAME]    record in the background to data/blobs/meetings/<date> <name>.m4a
                                             (Meeting In when it exists, else the Mac's microphone)
  meeting.py stop                            stop the recording; prints the file
  meeting.py status                          is a recording running, and for how long
  meeting.py transcribe <audio or video> [--lang CODE] [--speakers N]
                                             -> <same folder>/<name>.transcript.md (+ .json); prints the path
  meeting.py list                            recordings and transcripts in data/blobs/meetings/

Input: "Meeting In" when it exists (an aggregate of the Mac's microphone and BlackHole, so it hears
you AND the meeting cleanly), else the Mac's microphone (which hears the meeting only through the
speakers). While Meeting In records, the Mac's sound output is switched to "Meeting Out" (speakers or
headphones plus BlackHole) and put back on stop; the volume keys do not work on that output, use the
app's own volume. Both devices come from BlackHole (brew install blackhole-2ch) plus one CoreAudio
call; without them everything still works on the microphone alone.

Credits: transcription draws on the ElevenLabs account behind the voice (keychain item
troi-of-silo-one.elevenlabs, or ELEVENLABS_API_KEY); every run prints what it cost. Recordings and
transcripts stay on this Mac; the meeting note itself is the agent's job (the vault).
"""
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HOME = P.ROOT
OUT = P.blob_dir("meetings")
PIDF = OUT / ".recording.json"
FFMPEG = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
MIC = "Microphone"                      # without Meeting In: the first input with this in its name (the Mac's own)
MEETING_IN, MEETING_OUT = "Meeting In", "troi-meeting-out"          # the aggregate input's name, the multi-output's uid
API = "https://api.elevenlabs.io/v1"


# ---- CoreAudio, just enough to read and set the default output device (stdlib ctypes)
def _ca():
    import ctypes
    ca = ctypes.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]

    class Addr(ctypes.Structure):
        _fields_ = [("sel", ctypes.c_uint32), ("scope", ctypes.c_uint32), ("elem", ctypes.c_uint32)]

    def fcc(s): return int.from_bytes(s.encode(), "big")

    def get(obj, sel):
        a = Addr(fcc(sel), fcc("glob"), 0); size = ctypes.c_uint32(0)
        if ca.AudioObjectGetPropertyDataSize(obj, ctypes.byref(a), 0, None, ctypes.byref(size)) or not size.value: return None
        buf = ctypes.create_string_buffer(size.value)
        return buf.raw if ca.AudioObjectGetPropertyData(obj, ctypes.byref(a), 0, None, ctypes.byref(size), buf) == 0 else None

    def uid(dev):
        raw = get(dev, "uid ")
        if not raw: return ""
        ref = ctypes.c_void_p.from_buffer_copy(raw).value; out = ctypes.create_string_buffer(256)
        cf.CFStringGetCString(ref, out, 256, 0x08000100); return out.value.decode()

    def devices():
        raw = get(1, "dev#") or b""; return [int.from_bytes(raw[i:i + 4], "little") for i in range(0, len(raw), 4)]

    def default_output():
        raw = get(1, "dOut"); return uid(int.from_bytes(raw[:4], "little")) if raw else ""

    def set_default_output(want):
        for d in devices():
            if uid(d) == want:
                a = Addr(fcc("dOut"), fcc("glob"), 0); v = ctypes.c_uint32(d)
                return ca.AudioObjectSetPropertyData(1, ctypes.byref(a), 0, None, 4, ctypes.byref(v)) == 0
        return False
    return default_output, set_default_output


def die(msg):
    print(msg, file=sys.stderr); sys.exit(1)


def key():
    r = subprocess.run(["security", "find-generic-password", "-a", "troi-of-silo-one", "-s", "troi-of-silo-one.elevenlabs", "-w"],
                       capture_output=True, text=True)
    k = r.stdout.strip() or os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        die("no ElevenLabs key: keychain item troi-of-silo-one.elevenlabs (or ELEVENLABS_API_KEY) is empty")
    return k


def devices():
    """[(index, name)] of the audio inputs ffmpeg's avfoundation sees."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                       capture_output=True, text=True)
    out, seen = [], False
    for line in r.stderr.splitlines():
        if "audio devices" in line: seen = True; continue
        m = re.search(r"\[(\d+)\] (.+)$", line) if seen else None
        if m: out.append((int(m.group(1)), m.group(2).strip()))
    return out


def cmd_devices():
    for i, n in devices(): print(f"[{i}] {n}")


def cmd_start(name, device=None):
    if PIDF.exists() and _alive(): die(f"already recording: {json.load(open(PIDF))['file']}  (meeting.py stop)")
    OUT.mkdir(parents=True, exist_ok=True)
    devs = devices()
    if device is None: device = MEETING_IN if any(n == MEETING_IN for _, n in devs) else MIC
    match = [i for i, n in devs if n == device] or [i for i, n in devs if device.lower() in n.lower()]
    if not match: die(f"no audio input called {device!r}; meeting.py devices lists them")
    prev_out = ""
    if device == MEETING_IN:                     # route the Mac's sound through Meeting Out so BlackHole carries it
        try:
            default_output, set_default_output = _ca(); prev_out = default_output()
            if prev_out != MEETING_OUT and not set_default_output(MEETING_OUT): prev_out = ""
        except Exception:
            prev_out = ""
    safe = re.sub(r"[^\w .-]+", "", name).strip() or "meeting"
    f = OUT / f"{dt.date.today():%Y-%m-%d} {safe}.m4a"
    n = 2
    while f.exists(): f = OUT / f"{dt.date.today():%Y-%m-%d} {safe} ({n}).m4a"; n += 1
    log = open(OUT / ".recording.log", "w")
    p = subprocess.Popen([FFMPEG, "-hide_banner", "-loglevel", "warning", "-f", "avfoundation", "-i", f":{match[0]}",
                          "-ac", "1", "-ar", "16000", "-c:a", "aac", "-b:a", "48k", str(f)],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    time.sleep(1.5)
    if p.poll() is not None:
        die("ffmpeg could not start recording (microphone permission? see data/blobs/meetings/.recording.log)")
    json.dump({"pid": p.pid, "file": str(f), "device": device, "started": time.time(), "prev_out": prev_out}, open(PIDF, "w"))
    print(f"recording on {device!r} -> {f}" + (" (sound output switched to Meeting Out until stop)" if prev_out else "")
          + "\n(say when to stop: meeting.py stop)")


def _alive():
    try:
        st = json.load(open(PIDF)); os.kill(st["pid"], 0); return True
    except Exception:
        return False


def cmd_stop():
    if not PIDF.exists(): die("nothing is recording")
    st = json.load(open(PIDF))
    if _alive():
        os.kill(st["pid"], signal.SIGINT)                       # ffmpeg finalises the file on SIGINT
        for _ in range(40):
            if not _alive(): break
            time.sleep(0.25)
    PIDF.unlink(missing_ok=True)
    if st.get("prev_out"):
        try: _ca()[1](st["prev_out"])                    # the sound output goes back where it was
        except Exception: pass
    mins = (time.time() - st["started"]) / 60
    print(f"stopped after {mins:.1f} min: {st['file']}")


def cmd_status():
    if PIDF.exists() and _alive():
        st = json.load(open(PIDF)); print(f"recording {st['file']} for {(time.time() - st['started']) / 60:.1f} min")
    else:
        print("not recording")


def _credits(k):
    r = subprocess.run(["curl", "-sS", "-H", f"xi-api-key: {k}", f"{API}/user/subscription"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout); return d.get("character_count"), d.get("character_limit")
    except Exception:
        return None, None


def _mmss(s):
    s = int(s); return f"{s // 60:02d}:{s % 60:02d}"


def cmd_transcribe(path, lang=None, speakers=None):
    src = Path(path).expanduser()
    if not src.is_file(): die(f"no such file: {src}")
    k = key()
    used0, limit = _credits(k)
    form = ["-F", "model_id=scribe_v1", "-F", "diarize=true", "-F", "timestamps_granularity=word",
            "-F", "tag_audio_events=true", "-F", f"file=@{src}"]
    if lang: form += ["-F", f"language_code={lang}"]
    if speakers: form += ["-F", f"num_speakers={int(speakers)}"]
    r = subprocess.run(["curl", "-sS", "--max-time", "1800", "-X", "POST", "-H", f"xi-api-key: {k}", *form,
                        f"{API}/speech-to-text"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        die(f"transcription failed: {r.stdout[:300]} {r.stderr[:300]}")
    if "words" not in d:
        die(f"transcription refused: {json.dumps(d)[:400]}")
    raw = src.with_suffix(".transcript.json"); raw.write_text(json.dumps(d, indent=2))

    # words -> segments: a new one on a speaker change, a gap over 2 s, or after ~60 s
    segs, cur = [], None
    for w in d["words"]:
        if w.get("type") == "spacing": continue
        spk = w.get("speaker_id") or "speaker_0"
        text = w["text"] if w.get("type") != "audio_event" else f"({w['text'].strip('[]')})"
        if cur and (cur["spk"] != spk or w["start"] - cur["end"] > 2.0 or w["start"] - cur["start"] > 60):
            segs.append(cur); cur = None
        if cur is None: cur = {"spk": spk, "start": w["start"], "end": w["end"], "words": []}
        cur["words"].append(text); cur["end"] = w["end"]
    if cur: segs.append(cur)
    names = {}
    for s in segs: names.setdefault(s["spk"], f"Speaker {len(names) + 1}")
    dur = max((s["end"] for s in segs), default=0)
    lines = [f"# Transcript: {src.stem}", "",
             f"Recorded: {dt.datetime.fromtimestamp(src.stat().st_mtime):%A, %B %-d, %Y %H:%M}  ·  "
             f"Length: {_mmss(dur)}  ·  Language: {d.get('language_code', '?')} "
             f"({float(d.get('language_probability', 0)):.0%})  ·  Speakers: {len(names)}", "",
             "Speaker labels are automatic; rename them once you know who is who.", ""]
    for s in segs:
        body = re.sub(r"\s+([,.;:!?])", r"\1", " ".join(s["words"]))
        lines.append(f"**[{_mmss(s['start'])}] {names[s['spk']]}:** {body}"); lines.append("")
    md = src.with_suffix(".transcript.md"); md.write_text("\n".join(lines))
    used1, _ = _credits(k)
    cost = (used1 - used0) if (used0 is not None and used1 is not None) else None
    print(md)
    print(f"{len(segs)} segments, {len(names)} speakers, {_mmss(dur)} of audio"
          + (f"; credits used: {cost} (now {used1} of {limit} this month)" if cost is not None else ""))


def cmd_list():
    OUT.mkdir(parents=True, exist_ok=True)
    fs = sorted(p for p in OUT.iterdir() if not p.name.startswith("."))
    if not fs: print("no meetings yet"); return
    for p in fs: print(f"{dt.datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d %H:%M}  {p.stat().st_size / 1e6:6.1f} MB  {p.name}")


def main(a):
    if not a or a[0] in ("-h", "--help"): print(__doc__.strip()); return
    c, rest = a[0], a[1:]
    opts = {rest[i].lstrip("-"): rest[i + 1] for i in range(len(rest) - 1) if rest[i].startswith("--")}
    args = [x for i, x in enumerate(rest) if not x.startswith("--") and not (i and rest[i - 1].startswith("--"))]
    if c == "devices": cmd_devices()
    elif c == "start":
        name = " ".join(args)
        if not name:                              # no name given: the meeting on the calendar right now, if any
            try:
                ev = json.loads(subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "agenda.py"), "current"],
                                               capture_output=True, text=True, timeout=70).stdout or "{}")
                name = ev.get("title", "")
            except Exception:
                name = ""
        cmd_start(name or "meeting", opts.get("device"))
    elif c == "stop": cmd_stop()
    elif c == "status": cmd_status()
    elif c == "transcribe":
        if not args: die("meeting.py transcribe <file>")
        cmd_transcribe(args[0], opts.get("lang"), opts.get("speakers"))
    elif c == "list": cmd_list()
    else: die(__doc__.strip())


if __name__ == "__main__":
    main(sys.argv[1:])
