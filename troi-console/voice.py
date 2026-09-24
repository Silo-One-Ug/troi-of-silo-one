"""troi-console voice launcher: backtalk, plus a wake word for hands-free.

Run with backtalk's own Python, from the backtalk folder:
    uv run python ../troi-console/voice.py

Nothing in the backtalk repo is edited. Hands-free speech reaches the agent
through exactly one function, Ears.listen_once (push to talk uses a different
one), so this wraps that function: with the wake word on, an utterance that
does not contain the agent's name is dropped before the agent ever sees it.

Two things always pass without the wake word, because they are answers to a
question the agent just asked out loud: a pending permission check, and a
pending "say confirm".

The setting lives in data/console.json and is re-read on every
utterance, so the console can flip it live.
"""
import json
import os
import re
import sys
import threading
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import db as _DB  # noqa: E402  (small documents live in troi.db)

import sys as _sp, os as _osp; _sp.path.insert(0, _osp.path.dirname(_osp.path.abspath(__file__))); import paths as _Pa  # noqa: E402


def _cfg_names():
    """The agent's name (backtalk.json) and the owner's name (console.json)."""
    import json as _j, os as _o
    b = str(_Pa.BACKTALK / "backtalk.json"); c = str(_Pa.CONFIG)
    try: name = _j.load(open(b)).get("name", "Assistant")
    except Exception: name = "Assistant"
    try: owner = _j.load(open(c)).get("owner", "the owner")
    except Exception: owner = "the owner"
    return name, owner
AGENT, OWNER = _cfg_names()

HERE = Path(__file__).resolve().parent
SETTINGS = P.CONFIG
DEFAULTS = {"wake_word": True, "barge_in": True,
            "wake_names": ["troi", "troy", "troye", "troie", "troix", "troya", "toy", "troy's"]}
STOP_PHRASES = {"stop", "stop talking", "stop it", "please stop", "be quiet", "quiet", "silence",
                "shut up", "enough", "thats enough", "that is enough", "okay stop", "ok stop",
                "hold on", "pause", "never mind", "nevermind", "cancel"}

sys.path.insert(0, str(HERE.parent / "backtalk"))

from backtalk import main as bt_main          # noqa: E402
from backtalk.ears import Ears                # noqa: E402
from backtalk import ears as ears_mod         # noqa: E402
from backtalk.vlog import log                 # noqa: E402


def settings():
    try:
        return {**DEFAULTS, **json.loads(SETTINGS.read_text(encoding="utf-8"))}
    except Exception:
        return dict(DEFAULTS)


def _awaiting_answer():
    fut = bt_main._PERM.get("fut")
    return (fut is not None and not fut.done()) or bool(bt_main._CONFIRM.get("verb"))


# ---- the face gate (console.json "face_gate"): hands-free speech counts only while the owner's face is in
# front of the camera, so a television or a visitor cannot wake the agent by name. A pass is remembered for
# FACE_TTL seconds; the check uses the eyes' latest frame when it is fresh, otherwise one quick photo.
# Like voice ID, it fails CLOSED (no face print, no camera, no answer = not heard); the talk key always works.
FACE_TTL = 120
_face = {"ok_at": 0.0}


def _face_present():
    import subprocess, time
    if time.time() - _face["ok_at"] < FACE_TTL:
        return True
    if not (P.PRINTS / "face" / "owner.npy").exists() or not (HERE / ".venv-face" / "bin" / "python").exists():
        log("[face]   gate on but no face learnt / no face env: not heard (console: Modes > Face ID > Learn my face)")
        return False
    latest = P.blob_dir("looks") / "latest.jpg"
    args = [str(HERE / ".venv-face" / "bin" / "python"), str(HERE / "face.py"), "verify"]
    if latest.exists() and time.time() - latest.stat().st_mtime < 15:
        args.append(str(latest))
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        log(f"[face]   check failed ({e!r}): not heard"); return False
    if d.get("ok"):
        _face["ok_at"] = time.time(); log(f"[face]   owner present (sim {d.get('sim')})"); return True
    log(f"[face]   not the owner (sim {d.get('sim')} < {d.get('threshold')}): not heard"); return False


_listen_once = Ears.listen_once


def listen_once(self, *args, **kwargs):
    text = _listen_once(self, *args, **kwargs)
    if not text:
        return text
    cfg = settings()
    if _is_echo(text):
        log(f"[wake]   ignored (my own voice): {text[:160]}")
        return ""
    if not cfg["wake_word"] or _awaiting_answer():
        return text
    names = "|".join(re.escape(n) for n in cfg["wake_names"] if n)
    m = re.search(rf"\b({names})\b", text, re.IGNORECASE) if names else None
    if m:
        # With a television or other voices in the room, one "utterance" is
        # often a long blob of room audio with the person's request at the
        # end. Keep only the part from the name onward, so the request that
        # reaches the agent is the person's words, not the room's.
        text = text[m.start():].strip()
        # the name alone is not a request (and guards against the transcriber
        # echoing its own spelling hint on a noise burst)
        rest = re.sub(rf"\b({names}|hey|hi|ok|okay)\b|[^a-z]", "", text.lower())
        if rest:
            if cfg.get("face_gate") and not _face_present():
                log(f"[wake]   ignored (face gate): {text[:160]}")
                return ""
            return text
        log(f"[wake]   ignored (name only): {text[:160]}")
        return ""
    log(f"[wake]   ignored (no wake word): {text[:160]}")
    return ""


Ears.listen_once = listen_once


# ---- a silent stop. "<name>, stop" (or the console's Stop button) must cut the
# reply off WITHOUT starting a new one. backtalk interrupts the current reply
# for any new input, then asks console_match() whether the text is a control
# phrase; a verb it has no handler for runs as a no-op and says nothing. So
# teaching console_match one more verb gives a clean, quiet interrupt.
_console_match = bt_main.console_match

# backtalk only silences the voice when a reply is still being WRITTEN. A
# reply that is fully written but still being SPOKEN keeps playing from the
# audio queue, so the stop has to reach the mouth itself. The mouth is a local
# inside backtalk's main loop; remember it as it is created.
from backtalk.mouth import Mouth               # noqa: E402
from backtalk import signals                   # noqa: E402
_MOUTHS = []
_mouth_init = Mouth.__init__


def _remember_mouth(self, *a, **kw):
    _mouth_init(self, *a, **kw)
    _MOUTHS.append(self)


Mouth.__init__ = _remember_mouth

# ---- echo filter. On open speakers the microphone hears the agent's own
# voice, transcribes it perfectly, and (since the agent says its own name)
# sails through the wake word. So remember what was just spoken and drop any
# "utterance" that is mostly made of those words.
import time                                     # noqa: E402
_SPOKEN = []          # (monotonic time, set of words)
_ECHO_WINDOW_S = 45


def _note_spoken(text):
    words = set(re.findall(r"[a-z']+", str(text).lower()))
    if words:
        _SPOKEN.append((time.monotonic(), words))
        del _SPOKEN[:-60]


for _name in ("say", "say_chunk"):
    def _wrap(orig):
        def spoken(self, text, *a, **kw):
            if str(text).strip().lower().rstrip(".!") == "noted":
                return None          # watch mode's "nothing to say": stay silent
            if SILENT["on"]:
                return None          # a Telegram / call turn: the text goes back over that channel instead
            _note_spoken(text)
            return orig(self, text, *a, **kw)
        return spoken
    setattr(Mouth, _name, _wrap(getattr(Mouth, _name)))


# ---- the eyes. In "every" mode (console.json "eyes": "every" or "watch"),
# every request carries the newest camera frame so the agent answers knowing
# what is in front of it. eyes.py keeps data/cache/live.jpg fresh.
from backtalk.brain import WarmBrain           # noqa: E402
_ask_stream = WarmBrain.ask_stream
_LIVE = P.LIVE


import asyncio                                  # noqa: E402
import random                                   # noqa: E402
def _call():
    return settings().get("call") or "sir"


def _fillers():
    return (f"One moment, {_call()}.", "Working on it.", "Give me a second.", "Let me check.")


async def _filler_after(delay, done):
    """Speak a short filler if the reply's first sentence has not arrived by `delay`."""
    try:
        await asyncio.sleep(delay)
        if not done.is_set() and _MOUTHS:
            _MOUTHS[-1].say_chunk(random.choice(_fillers()), None)
            await asyncio.sleep(18)
            if not done.is_set() and _MOUTHS:
                _MOUTHS[-1].say_chunk(f"Still on it, {_call()}.", None)
    except asyncio.CancelledError:
        pass


SILENT = {"on": False}      # a remote turn (Telegram / call): the brain answers, the room stays quiet


_BUSY = HERE.parent / "backtalk" / ".voice_busy"


async def _with_fillers(gen, silent=False):
    done = asyncio.Event()
    SILENT["on"] = silent
    try:
        _BUSY.write_text(str(time.time()))          # the brain is at work until the turn ends, spoken or not
    except OSError:
        pass
    task = None if silent else asyncio.get_event_loop().create_task(_filler_after(5.0, done))
    try:
        async for sentence in gen:
            done.set()
            yield sentence
    finally:
        done.set()
        if silent:
            # nothing was spoken, so nothing will settle the bus: do it here so the line reads idle
            try:
                signals.static_stop(); signals.set_state("idle")
            except Exception:
                pass
        SILENT["on"] = False
        if task: task.cancel()
        try:
            _BUSY.unlink()
        except OSError:
            pass


def ask_stream(self, utterance):
    eyes = settings().get("eyes", "off")
    if eyes == "screen" and not str(utterance).startswith(("(camera watch:", "(session start", "(written:")):
        try:
            import subprocess as _sp
            r = _sp.run([str(HERE / "look-screen.sh")], capture_output=True, text=True, timeout=12)
            shot = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""
            if shot:
                utterance = (f"{utterance}\n\n(Your eyes: a screenshot of the screen taken just now is at {shot}. Read it first, quickly, so you "
                             f"answer knowing what is on the screen. Do not describe it unless asked or it matters to the answer.)")
        except Exception as ex:
            log(f"[eyes] screen capture failed: {ex!r}")
    if eyes in ("every", "watch") and _LIVE.exists() and not str(utterance).startswith("(camera watch:"):
        age = time.time() - _LIVE.stat().st_mtime
        if age < 15:
            utterance = (f"{utterance}\n\n(Your eyes: a camera frame from {age:.0f}s ago is at {_LIVE}. "
                         f"Read it first, quickly, so you answer knowing what you can see. Do not describe it "
                         f"unless asked or it matters to the answer.)")
    remote = str(utterance).lstrip().startswith(("(via telegram)", "(via call)", "(written:"))
    return _with_fillers(_ask_stream(self, utterance), silent=remote)


WarmBrain.ask_stream = ask_stream

# ---- the living greeting. backtalk speaks the rendered greeting ("Hello <address>.") the moment it starts; once the
# brain is warm, ONE "(session start ...)" line goes in through the typing pipe and the agent adds the
# human part itself: the time of day, the shape of the day, a dry remark. Never the same line twice.
_FIFO = HERE / ".typed"
_REMINDERS = _DB.doc("reminders")


def _session_start_line():
    import datetime
    now = datetime.datetime.now()
    due, top = [], []
    try:
        for r in json.loads(_REMINDERS.read_text()):
            if 0 <= r.get("at", 0) - time.time() < 14 * 3600:
                due.append(f"{r.get('text')} at {datetime.datetime.fromtimestamp(r['at']).strftime('%H:%M')}")
    except Exception:
        pass
    try:
        for line in (Path(settings().get("vault", "")) / "Active Priorities.md").read_text().splitlines():
            if line.startswith("- [ ]"):
                top.append(re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", line[5:]).strip()[:120])
            if len(top) >= 2:
                break
    except Exception:
        pass
    ctx = ("Reminders coming up: " + "; ".join(due) + ". " if due else "No reminders today. ")
    ctx += ("At the top of Active Priorities: " + " | ".join(top) + ". " if top else "")
    hello = settings().get("address") or OWNER
    if not settings().get("introduced"):                           # the first meeting, right after the welcome
        _remember_introduced()
        return (f"(session start: this is your first meeting. {OWNER} has just finished setting you up in the welcome, and it is "
                f"{now.strftime('%A %-d %B, %H:%M')}. You have already said \"Hello {hello}.\" out loud. Introduce yourself in two or three "
                f"short spoken sentences: who you are, and one thing you can do for them right now. Then ask what we are working on. "
                f"No lists, and do not say hello again.)")
    return (f"(session start: {OWNER} has just switched you on. It is {now.strftime('%A %-d %B, %H:%M')}. {ctx}"
            f"You have already said \"Hello {hello}.\" out loud. Now add what a fellow person would add: ONE or TWO short spoken "
            f"sentences that pick up on the time of day, or the day ahead, or a dry remark or a small joke now and then. Vary it every "
            f"time, never a stock line, no lists, do not say hello again, and end by asking what we are working on or by offering the "
            f"obvious next step.)")


def _remember_introduced():
    try:
        cur = json.loads(SETTINGS.read_text()); cur["introduced"] = True
        SETTINGS.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"[greeting] could not note the introduction: {e!r}")


def _greet_soon():
    def run():
        time.sleep(1.0)
        try:
            fd = os.open(str(_FIFO), os.O_WRONLY | os.O_NONBLOCK)
            os.write(fd, (_session_start_line() + "\n").encode()); os.close(fd)
        except OSError as e:
            log(f"[greeting] could not send the session-start line: {e!r}")
    threading.Thread(target=run, daemon=True).start()


async def _then(gen, fn):
    async for s in gen:
        yield s
    fn()


# ---- streaming: every text delta the model produces is mirrored into backtalk/.voice_partial, so
# the console can show the reply growing word by word instead of sentence by sentence. The file is
# emptied when the turn ends (or dies). The tap sits on the SDK client's message stream, so brain.py
# is untouched and re-tapped whenever the client is rebuilt.
_PARTIAL = HERE.parent / "backtalk" / ".voice_partial"
_TOOL = HERE.parent / "backtalk" / ".voice_tool"          # the tool the brain is using right now, or empty


def _write_partial(text):
    try:
        _PARTIAL.write_text(text)
    except OSError:
        pass


def _write_tool(name):
    try:
        _TOOL.write_text(name or "")
    except OSError:
        pass


def _tap(brain):
    client = getattr(brain, "_client", None)
    if client is None or getattr(client, "_troi_tapped", False):
        return
    orig = client.receive_response

    def receive_response(*a, **k):
        async def gen():
            buf, last = "", 0.0
            try:
                async for msg in orig(*a, **k):
                    t = type(msg).__name__
                    if t == "StreamEvent":
                        ev = getattr(msg, "event", {}) or {}
                        if ev.get("type") == "content_block_delta":
                            d = ev.get("delta", {}) or {}
                            if d.get("type") == "text_delta":
                                buf += d.get("text", "")
                                if time.time() - last > 0.08:
                                    last = time.time(); _write_partial(buf)
                        elif ev.get("type") == "content_block_start" and (ev.get("content_block") or {}).get("type") == "tool_use":
                            _write_tool((ev.get("content_block") or {}).get("name", "tool"))
                        elif ev.get("type") == "content_block_stop":
                            _write_tool("")
                    elif t == "ResultMessage":
                        _TURN["result"] = True
                        _write_partial(""); _write_tool("")
                    yield msg
            finally:
                _write_partial(""); _write_tool("")
        return gen()
    client.receive_response = receive_response
    client._troi_tapped = True


# ---- the voice: Kokoro on this Mac, or ElevenLabs when console.json says so (tts, elevenlabs_voice). backtalk reads
# its config once at start; this follows the console's choice on every turn, so the switch is live. The key is the
# Keychain item troi-of-silo-one.elevenlabs; Kokoro takes over the moment ElevenLabs cannot answer (backtalk's own fallback).
from backtalk import mouth as _mouth_mod                    # noqa: E402


def _follow_voice_choice():
    try:
        st = settings(); el = _mouth_mod.CFG.setdefault("elevenlabs", {})
        want = st.get("tts") == "elevenlabs" and bool(st.get("elevenlabs_voice"))
        if bool(el.get("enabled")) != want or (want and el.get("voice_id") != st.get("elevenlabs_voice")):
            el["enabled"] = want; el["voice_id"] = st.get("elevenlabs_voice", "") if want else el.get("voice_id", "")
            _mouth_mod._el_key_cache = None                 # look the key up again: it may have just been kept
            log(f"[mouth] voice: {'ElevenLabs ' + el['voice_id'] if want else 'Kokoro'}")
    except Exception as ex:
        log(f"[mouth] voice choice not applied: {ex!r}")


_orig_ask = ask_stream


# ---- the welcome: until the owner has been set up, Troi hears but does not answer. The welcome shows what it heard
# (the talk-key test); only the voice line's own warm-up and the welcome's voice test reach the brain. A Telegram
# message gets one line back, so a freshly paired phone knows it works.
_ONBOARDING_OK = ("Warmup ping", "(this is a voice test from the welcome")


async def _quiet():
    return
    yield                                                          # an empty reply: nothing is said


async def _one(line):
    yield line


def ask_stream(self, utterance):                                   # noqa: F811
    _tap(self); _follow_voice_choice()
    u = str(utterance)
    if not settings().get("welcomed", False) and not u.startswith(_ONBOARDING_OK):
        log(f"[welcome] heard during the setup, not answered: {u[:80]}")
        _TURN["result"] = True                                     # nothing was asked of the brain: no result is due, the link is fine
        if u.startswith("(via telegram)"):
            return _one("I'm here. Let's finish the setup on your Mac first; I'm all yours after that.")
        return _quiet()
    if u.startswith("Warmup ping") and settings().get("living_greeting", True) and settings().get("welcomed", False):
        return _then(_orig_ask(self, utterance), _greet_soon)
    return _orig_ask(self, utterance)


WarmBrain.ask_stream = ask_stream
_write_partial("")

# ---- a bigger mouth for tool results, and a brain that comes back. The SDK reads the agent's
# messages through a 1 MB buffer; one oversized tool result (a web page dumped whole) kills the
# reader and every turn after it is silence. Raise the buffer, and if a turn ever ends without
# its result message, rebuild the connection on the same session and say so.
from backtalk import brain as _brain_mod                    # noqa: E402
_OrigOptions = _brain_mod.ClaudeAgentOptions


def _options_with_buffer(*a, **k):
    k.setdefault("max_buffer_size", 16 * 1024 * 1024)
    return _OrigOptions(*a, **k)


_brain_mod.ClaudeAgentOptions = _options_with_buffer
_TURN = {"result": False}


async def _rebuild(brain):
    log("[brain] the message reader died; rebuilding the connection on the same session")
    try:
        await brain.stop()
    except Exception:
        pass
    try:
        sid = Path(_brain_mod.SESSION_FILE).read_text().strip()
        brain._resume_id = sid or None
    except Exception:
        pass
    await brain.start()
    _tap(brain)
    if _MOUTHS and not SILENT["on"]:
        _MOUTHS[-1].say_chunk(f"The line to my brain dropped for a moment. I have reconnected; say that again, {_call()}.", None)


_ask_before_guard = ask_stream


def ask_stream(self, utterance):                                   # noqa: F811
    async def run():
        _TURN["result"] = False
        n = 0
        try:
            async for s in _ask_before_guard(self, utterance):
                n += 1
                yield s
        except Exception as ex:
            log(f"[brain] turn failed: {ex!r}")
            await _rebuild(self)
            return
        if not _TURN["result"] and n == 0:
            await _rebuild(self)
    return run()


WarmBrain.ask_stream = ask_stream


def _is_echo(text):
    heard = re.findall(r"[a-z']+", text.lower())
    if len(heard) < 3:
        return False
    now = time.monotonic()
    recent = set()
    for t, words in _SPOKEN:
        if now - t <= _ECHO_WINDOW_S:
            recent |= words
    if not recent:
        return False
    hit = sum(1 for w in heard if w in recent)
    return hit / len(heard) >= 0.7


def console_match(text):
    verb = _console_match(text)
    if verb:
        return verb
    norm = re.sub(r"[^a-z ]", "", text.lower().replace("-", " "))
    words = [w for w in norm.split() if w not in set(settings()["wake_names"]) | {"hey", "please"}]
    if " ".join(words) in STOP_PHRASES:
        for m in _MOUTHS:
            try:
                m.shut_up()
            except Exception:
                pass
        try:
            signals.static_stop()
        except Exception:
            pass
        log("[stop]   reply cut off on request")
        return "quietstop"
    return None


bt_main.console_match = console_match


# ---- help the transcriber spell the name. Whisper has never seen the agent's name, so
# it writes "Troy", "Hi" or nothing; a short initial prompt biases it toward
# the name without changing anything else it hears.
try:
    import mlx_whisper
    _mlx_transcribe = mlx_whisper.transcribe

    # a larger, more accurate model, used as soon as get-model.sh has finished
    # downloading it (backtalk itself only knows the small one by name)
    _BIG = P.MODELS / "whisper-medium.en-mlx"

    def _transcribe(audio, **kw):
        kw.setdefault("initial_prompt", f"Hey {AGENT},")
        if (_BIG / ".done").exists():
            kw["path_or_hf_repo"] = str(_BIG)
        return _mlx_transcribe(audio, **kw)

    mlx_whisper.transcribe = _transcribe

    # load the big model at startup, not on the first sentence (it takes ~15s)
    import numpy as _np
    _warm_ears = ears_mod.warm

    def _warm():
        out = _warm_ears()
        if (_BIG / ".done").exists() and not getattr(_warm, "done", False):
            _warm.done = True
            log("[ears] loading the larger model (medium.en) on the Apple GPU...")
            ears_mod.transcribe(_np.zeros(16000, dtype=_np.int16))
            log("[ears] larger model ready")
        return out

    ears_mod.warm = _warm
    bt_main.warm_ears = _warm
except Exception:
    pass

# ---- voice ID. A voice-print of the owner (resemblyzer, local) so that in
# hands-free only the owner's voice reaches the agent: the television, other people
# and the agent's own echo are dropped before transcription. console.json:
#   "voice_id": "off" | "on" | "learn"   (learn = collect push-to-talk clips
#   until ~60 s of the owner's speech, build the print, then switch to "on")
# Push to talk is never gated: holding the key always gets you heard.
_VOICE_DIR = P.PRINTS / "voice"
_PRINT = _VOICE_DIR / "owner.npy"
_ENC = None
_VID_THRESHOLD = 0.78          # default; console.json "voice_id_threshold" overrides (0.6 loose … 0.95 strict)


def _encoder():
    global _ENC
    if _ENC is None:
        from resemblyzer import VoiceEncoder
        _ENC = VoiceEncoder("cpu", verbose=False)
    return _ENC


def _embed(pcm):
    import numpy as np
    from resemblyzer import preprocess_wav
    wav = preprocess_wav(pcm.astype(np.float32) / 32768.0, source_sr=16000)
    if len(wav) < 16000 * 0.35:
        return None
    return _encoder().embed_utterance(wav)


def _write_setting(key, val):
    try:
        cur = json.loads(SETTINGS.read_text())
    except Exception:
        cur = {}
    cur[key] = val
    SETTINGS.write_text(json.dumps(cur, indent=2))


_ears_transcribe = ears_mod.transcribe


def transcribe(pcm):
    import numpy as np
    vid = settings().get("voice_id", "off")
    if vid == "learn":
        # only push-to-talk clips teach (the room can't sneak into the print)
        if bt_main._MIC.get("btn") or bt_main._MIC.get("mode") != "open":
            _VOICE_DIR.mkdir(exist_ok=True)
            n = len(list(_VOICE_DIR.glob("clip-*.npy")))
            np.save(_VOICE_DIR / f"clip-{n:03d}.npy", pcm)
            total = sum(len(np.load(f)) for f in _VOICE_DIR.glob("clip-*.npy")) / 16000
            log(f"[voice-id] learning: {total:.0f}s of the owner collected")
            if total >= 60:
                embs = [e for e in (_embed(np.load(f)) for f in sorted(_VOICE_DIR.glob("clip-*.npy"))) if e is not None]
                if embs:
                    m = np.mean(embs, axis=0); m /= np.linalg.norm(m)
                    np.save(_PRINT, m)
                    _write_setting("voice_id", "on")
                    log("[voice-id] voice print built; voice ID on")
    elif vid == "on" and bt_main._MIC.get("mode") == "open" and not bt_main._MIC.get("btn") and _PRINT.exists():
        # hands-free with voice ID on: fail CLOSED. Anything that cannot be identified as the
        # owner (too short, an error, below the threshold) is dropped, never let through.
        try:
            th = float(settings().get("voice_id_threshold", _VID_THRESHOLD))
        except Exception:
            th = _VID_THRESHOLD
        try:
            e = _embed(pcm)
            if e is None:
                log("[voice-id] ignored (too short to identify)")
                return ""
            sim = float(np.dot(e, np.load(_PRINT)))
            if sim < th:
                log(f"[voice-id] ignored (not the owner's voice, {sim:.2f})")
                return ""
            log(f"[voice-id] the owner ({sim:.2f})")
        except Exception as ex:
            log(f"[voice-id] ignored (could not identify the voice: {ex!r})")
            return ""
    return _ears_transcribe(pcm)


ears_mod.transcribe = transcribe

# ---- music ducking. backtalk dips Spotify while the agent talks and restores it half a
# second after each pause; a reply is many sentences, so the music pumps up and down
# between them. Keep the music down for the whole reply, or leave it alone entirely.
from backtalk import ducking as _duck                    # noqa: E402
_duck.RESTORE_DEBOUNCE_S = 4.0
if not settings().get("duck_music", True):
    for _n in ("speech_start", "speech_end"):
        if hasattr(_duck.Ducker, _n):
            setattr(_duck.Ducker, _n, lambda self, *a, **k: None)

# ---- Apple Music too. backtalk's ducker only knows Spotify; when Music is the player (Spotify not
# running), read and set Music's volume through the same two hooks, so the dip works either way.
_spotify_volume_orig, _set_volume_orig = _duck._spotify_volume, _duck._set_volume


def _music_playing_volume():
    if _duck._osa('application "Music" is running') != "true": return None
    if _duck._osa('tell application "Music" to get player state') != "playing": return None
    try: return int(_duck._osa('tell application "Music" to get sound volume'))
    except (TypeError, ValueError): return None


def _any_player_volume():
    v = _spotify_volume_orig()
    return v if v is not None else _music_playing_volume()


def _any_player_set_volume(level):
    if _spotify_volume_orig() is not None: _set_volume_orig(level)
    else: _duck._osa(f'tell application "Music" to set sound volume to {int(level)}')


_duck._spotify_volume, _duck._set_volume = _any_player_volume, _any_player_set_volume

# ---- the settings guard. Some things lower the agent's guard: auto-approve, hands-free, clearing the
# session. Nobody but the owner gets to say them: a spoken order must come in the owner's verified
# voice (the voice print), a typed one must come from a console unlocked with the PIN (the server
# marks those lines "(verified) "), and anything else is filed for the owner's approval on Telegram.
PROTECTED_VERBS = {"noask": "auto-approve (stop asking for permission)", "micopen": "hands-free listening", "clear": "clearing the session"}
_LAST_PCM = {"pcm": None, "text": ""}


def _guard_on():
    return settings().get("guard_settings", True) is not False


def _has_verifier():
    """Is there any way to verify the owner at all? (a voice print, a PIN, or Telegram)"""
    if _PRINT.exists():
        return True
    try:
        import subprocess as _sp
        if _sp.run(["security", "find-generic-password", "-a", "troi-of-silo-one", "-s", "troi-of-silo-one.pin", "-w"], capture_output=True, text=True, timeout=5).returncode == 0:
            return True
        if _DB.doc("telegram").exists():
            return True
    except Exception:
        pass
    return False


def _voice_verified(pcm):
    """The clip is the owner's voice, by the voice print. No print: cannot verify."""
    if pcm is None or not _PRINT.exists():
        return False, "no voice print to check against"
    try:
        import numpy as np
        e = _embed(pcm)
        if e is None:
            return False, "too short to identify"
        sim = float(np.dot(e, np.load(_PRINT)))
        th = float(settings().get("voice_id_threshold", _VID_THRESHOLD))
        return (sim >= th), f"voice match {sim:.2f} against {th:.2f}"
    except Exception as ex:
        return False, f"could not identify the voice: {ex!r}"


def _face_check(say_first=True):
    """Ask the console server to look at the camera and compare with the owner's face print."""
    try:
        import urllib.request
        if say_first and _MOUTHS:
            _MOUTHS[-1].say_chunk("One moment, let me see you.", None)
        req = urllib.request.Request("http://127.0.0.1:8796/face-verify", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=70) as r:
            d = json.load(r)
        return bool(d.get("ok")), f"face {d.get('sim', '')} {d.get('error', '')}".strip()
    except Exception as ex:
        return False, f"face check unavailable: {ex!r}"


def _refuse(verb, how, why):
    label = PROTECTED_VERBS.get(verb, verb)
    log(f"[guard] refused {label} ({how}: {why})")
    try:
        if _MOUTHS:
            _MOUTHS[-1].say_chunk(f"That needs {OWNER}'s say-so. I have sent it to their phone.", None)
    except Exception:
        pass
    try:
        import urllib.request
        body = json.dumps({"src": f"{how}: {label}", "why": why, "phrase": verb}).encode()
        req = urllib.request.Request("http://127.0.0.1:8796/pending-setting", data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as ex:
        log(f"[guard] could not file the request: {ex!r}")


_transcribe_unguarded = transcribe


def transcribe(pcm):                                               # noqa: F811
    text = _transcribe_unguarded(pcm)
    if not text:
        return text
    _LAST_PCM["pcm"] = pcm; _LAST_PCM["text"] = text
    verb = bt_main.console_match(text)
    if verb in PROTECTED_VERBS and _guard_on() and _has_verifier():
        ok, why = _voice_verified(pcm)
        if not ok and (P.PRINTS / "face" / "owner.npy").exists():
            ok2, why2 = _face_check()
            if ok2:
                log(f"[guard] {PROTECTED_VERBS[verb]} allowed by face ({why2}; voice: {why})")
                return text
            why = f"{why}; {why2}"
        if not ok:
            _refuse(verb, "spoken", why)
            return ""
        log(f"[guard] {PROTECTED_VERBS[verb]} allowed: {why}")
    return text


ears_mod.transcribe = transcribe

_orig_typed_reader = bt_main._typed_reader


def _guard_typed(line):
    if line.startswith("(verified) "):
        return line[len("(verified) "):]
    verb = bt_main.console_match(line)
    if verb in PROTECTED_VERBS and _guard_on() and _has_verifier():
        if (P.PRINTS / "face" / "owner.npy").exists():
            ok2, why2 = _face_check()
            if ok2:
                log(f"[guard] {PROTECTED_VERBS[verb]} allowed by face ({why2})")
                return line
            _refuse(verb, "typed", f"the console was not unlocked; {why2}")
            return None
        _refuse(verb, "typed", "the console was not unlocked with the PIN")
        return None
    return line


# ---- the terminal echo of internal lines (the session-start prompt, written turns) is one short line, not the prompt
_orig_log = bt_main.log


def _short_echo(msg, *a, **k):
    m = str(msg)
    if m.startswith("[you]    (session start"):
        m = "[you]    (session start)"
    elif m.startswith("[you]    (written:"):
        m = m[:90] + ("…)" if len(m) > 90 else "")
    return _orig_log(m, *a, **k)


bt_main.log = _short_echo


def _typed_reader(q):
    class Proxy:
        def put(self, line):
            line = _guard_typed(line)
            if line:
                q.put(line)
        def __getattr__(self, name):
            return getattr(q, name)
    return _orig_typed_reader(Proxy())


bt_main._typed_reader = _typed_reader

if __name__ == "__main__":
    # talk-over (barge-in) is a launch flag in backtalk; the wake word makes it
    # safe, since only a sentence with the name in it can interrupt.
    if settings().get("barge_in") and "--barge-in" not in sys.argv:
        sys.argv.append("--barge-in")
    # a fresh start in place (the welcome's last step sends SIGUSR1): same window, same typing pipe, and the
    # settings, boot file and vault written since launch; backtalk reads its config only once, at start
    import signal
    signal.signal(signal.SIGUSR1, lambda *_: os.execv(sys.executable, [sys.executable, *sys.argv]))
    try:
        (P.CACHE / "voice.pid").write_text(str(os.getpid()))    # the server signals this process, never its uv parent
    except OSError:
        pass
    bt_main.main()
