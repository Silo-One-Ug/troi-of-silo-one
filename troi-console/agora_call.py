#!/usr/bin/env python3
"""Talk to the agent from anywhere, over an Agora voice channel.

Run with backtalk's Python (it has the ears, the mouth and the Agora SDK):
    backtalk/.venv/bin/python troi-console/agora_call.py <command>   (from the repo root)

  check            what is configured, what is missing
  link             print a fresh call link (a channel + a 24 h token)
  answer <channel> join that channel as the agent and talk until the caller leaves
  call             link + send it to the owner on Telegram + answer   ("the agent, call me")

Credentials live in the macOS keychain, never in files:
    keychain.py set agora-appid   (paste the App ID)
    keychain.py set agora-cert    (paste the App Certificate)
The phone side is call.html (served by the console at /call.html; host it
anywhere static for use away from home and set "call_page" in console.json).
"""
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import keychain as KC  # noqa: E402

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
import os as _os2, json as _j2
try: VAULT = _j2.load(open(str(_Pa.CONFIG))).get("vault", _os2.path.expanduser("~/Vault"))
except Exception: VAULT = _os2.path.expanduser("~/Vault")

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
sys.path.insert(0, str(HOME / "backtalk"))
LOGF = P.LOGS / "agora.log"
SETTINGS = P.CONFIG
TROI_UID, OWNER_UID = "1", 2
RATE = 16000
CLAUDE = str(Path.home() / ".local" / "bin" / "claude")
PATH = "/opt/homebrew/bin:/usr/local/bin:" + str(Path.home() / ".local" / "bin") + ":" + os.environ.get("PATH", "")


def log(line):
    LOGF.parent.mkdir(exist_ok=True)
    with LOGF.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    print(line, flush=True)


def secret(service):
    try:
        return KC.get(service)                              # troi-of-silo-one.<service> in the Keychain
    except Exception:
        return ""


def settings():
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


def lan_ip():
    try:
        return subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True, timeout=5).stdout.strip() or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def token_for(channel, uid, hours=24):
    from agora_token_builder import RtcTokenBuilder
    appid, cert = secret("agora-appid"), secret("agora-cert")
    if not cert:            # a project with no certificate (Agora "testing mode") joins with no token
        return ""
    return RtcTokenBuilder.buildTokenWithUid(appid, cert, channel, uid, 1, int(time.time()) + hours * 3600)


def make_link():
    channel = "troi-" + secrets.token_hex(3)
    base = settings().get("call_page") or f"http://{lan_ip()}:8796/call.html"
    from urllib.parse import quote
    url = (f"{base}?appid={quote(secret('agora-appid'))}&channel={quote(channel)}&uid={OWNER_UID}"
           f"&token={quote(token_for(channel, OWNER_UID), safe='')}")
    return channel, url


# ---------------- the brain, the ears and the mouth for a call ----------------
def ask_troi(text, session):
    """One turn in the ONE shared conversation: via the live voice line if it is up (silent in the room), else resume it."""
    prompt = (f"(via call) {text} (the owner is talking to you on a voice call from his phone. Reply as speech: short, plain, "
              f"no lists or markdown, one to three sentences unless he asks for detail.)")
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8796/ask", data=json.dumps({"text": prompt, "timeout": 120}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=150) as r:
            d = json.load(r)
        if d.get("live") and d.get("reply"):
            return d["reply"]
    except Exception as e:
        log(f"live brain not reachable ({e!r}); resuming the shared session")
    try:
        sid = (HOME / "backtalk" / ".backtalk_session").read_text().strip()
    except Exception:
        sid = ""
    cmd = [CLAUDE, "-p", prompt, "--model", "claude-sonnet-5", "--permission-mode", "bypassPermissions",
           "--settings", str(HOME / ".claude" / "settings.json"), "--add-dir", str(VAULT),
           "--max-turns", "8", "--output-format", "json"] + (["--resume", sid] if sid else [])
    r = subprocess.run(cmd, cwd=HOME, capture_output=True, text=True, timeout=300, env={**os.environ, "PATH": PATH},
                       stdin=subprocess.DEVNULL)
    try:
        out = json.loads(r.stdout)
        if out.get("session_id"):
            (HOME / "backtalk" / ".backtalk_session").write_text(out["session_id"])
        return out.get("result") or "Sorry, sir, I lost that one."
    except Exception:
        log(f"claude error: {r.stderr[-200:]}"); return "Something went wrong on my end, sir."


def synth16k(text):
    """the agent's voice as 16 kHz mono int16 bytes."""
    import numpy as np
    from backtalk.config import CFG
    from kokoro import KPipeline
    if not hasattr(synth16k, "pipe"):
        synth16k.pipe = KPipeline(lang_code=CFG.get("voice", "bm_lewis")[0])
    chunks = [np.asarray(a, dtype="float32") for _, _, a in synth16k.pipe(text, voice=CFG.get("voice", "bm_lewis"))]
    if not chunks:
        return b""
    a24 = np.concatenate(chunks)
    n = int(len(a24) * RATE / 24000)
    a16 = np.interp(np.linspace(0, len(a24) - 1, n), np.arange(len(a24)), a24)
    pcm = (np.clip(a16, -1, 1) * 32767).astype("<i2").tobytes()
    pad = (-len(pcm)) % 320                     # whole 10 ms frames
    return pcm + b"\x00" * pad


HALLUCINATIONS = {"thank you", "thanks", "thank you for watching", "thanks for watching", "you", "bye", "so", "the",
                  "of the", "okay", "ok", "mm-hmm", "hmm", "uh", "um", "yeah", "oh", "subtitles by the amara.org community"}


def is_hallucination(text):
    t = " ".join(text.lower().replace("-", " ").split()).strip(" .,!?")
    return t in HALLUCINATIONS or len(t) < 3


def is_owner(pcm):
    """Voice-ID gate, if the owner has taught the agent his voice (data/prints/voice/owner.npy)."""
    print_path = P.PRINTS / "voice" / "owner.npy"
    if not print_path.exists():
        return True
    try:
        import numpy as np
        from resemblyzer import VoiceEncoder, preprocess_wav
        if not hasattr(is_owner, "enc"):
            is_owner.enc = VoiceEncoder("cpu", verbose=False); is_owner.ref = np.load(print_path)
        wav = preprocess_wav(pcm.astype(np.float32) / 32768.0, source_sr=RATE)
        if len(wav) < RATE * 0.8:
            return True
        return float(np.dot(is_owner.enc.embed_utterance(wav), is_owner.ref)) >= 0.7
    except Exception as e:
        log(f"voice-id error, letting it through: {e!r}"); return True


def answer(channel):
    import numpy as np
    import webrtcvad
    from agora.rtc.agora_service import AgoraService
    from agora.rtc import agora_base as ab
    from agora.rtc.audio_frame_observer import IAudioFrameObserver
    from agora.rtc.rtc_connection_observer import IRTCConnectionObserver
    from backtalk import ears

    appid = secret("agora-appid")
    if not appid:
        log("no Agora App ID in the keychain"); return 1
    ears.warm()
    inbox: "queue.Queue[bytes]" = queue.Queue()
    state = {"caller": False, "speaking": False, "gone": False}

    class Conn(IRTCConnectionObserver):
        def on_connected(self, *a): log("connected to the channel")
        def on_user_joined(self, conn, uid): state["caller"] = True; log(f"caller joined ({uid})")
        def on_user_left(self, conn, uid, reason): state["gone"] = True; log(f"caller left ({uid})")
        def on_connection_failure(self, *a): state["gone"] = True; log("connection failed")

    class Audio(IAudioFrameObserver):
        def on_playback_audio_frame_before_mixing(self, agora_local_user, channelId, uid, frame, vad_result_state, vad_result_bytearray):
            try:
                inbox.put(bytes(frame.buffer))
            except Exception:
                pass
            return 1

    cfg = ab.AgoraServiceConfig(); cfg.appid = appid; cfg.enable_audio_processor = 1; cfg.enable_audio_device = 0
    cfg.audio_scenario = getattr(ab.AudioScenarioType, "AUDIO_SCENARIO_AI_SERVER", getattr(ab.AudioScenarioType, "AUDIO_SCENARIO_CHORUS", 7))
    cfg.log_path = str(P.LOGS / "agora-sdk.log")
    svc = AgoraService(); svc.initialize(cfg)
    cc = ab.RTCConnConfig(); cc.client_role_type = getattr(ab.ClientRoleType, "CLIENT_ROLE_BROADCASTER", 1)
    cc.channel_profile = getattr(ab.ChannelProfileType, "CHANNEL_PROFILE_LIVE_BROADCASTING", 1); cc.auto_subscribe_audio = 1
    pc = ab.RtcConnectionPublishConfig(); pc.is_publish_audio = True
    pc.audio_publish_type = getattr(ab.AudioPublishType, "AUDIO_PUBLISH_TYPE_PCM", 0)
    conn = svc.create_rtc_connection(cc, pc)
    conn.register_observer(Conn())
    conn.get_local_user().set_playback_audio_frame_before_mixing_parameters(1, RATE)
    conn.register_audio_frame_observer(Audio(), 0, None)
    if conn.connect(token_for(channel, int(TROI_UID)), channel, TROI_UID) != 0:
        log("connect() failed"); return 1
    conn.publish_audio()
    log(f"{AGENT} is in channel {channel}, waiting for the owner")

    def say(text):
        """Feed the agent's voice to the channel in 200 ms pieces, staying half a
        second ahead of real time: the SDK paces playback itself, so bigger
        pieces with a lead never starve it (10 ms pieces paced by sleeps did).
        The mic is only closed while audio is actually going out, not while
        the sentence is being synthesised."""
        try:
            pcm = synth16k(text)
            state["speaking"] = True
            chunk = 6400                                  # 200 ms at 16 kHz mono
            t0 = time.time(); sent_ms = 0
            for i in range(0, len(pcm), chunk):
                if state["gone"]:
                    break
                while sent_ms - (time.time() - t0) * 1000 > 500:
                    time.sleep(0.02)
                piece = pcm[i:i + chunk]
                piece += b"\x00" * ((-len(piece)) % 32)
                conn.push_audio_pcm_data(bytearray(piece), RATE, 1)
                sent_ms += len(piece) / 32
            # keep the mic closed until the tail has actually played out
            while sent_ms - (time.time() - t0) * 1000 > 0 and not state["gone"]:
                time.sleep(0.02)
        except Exception as e:
            log(f"say() failed: {e!r}")
        finally:
            state["speaking"] = False

    session = {}
    synth16k("Ready.")                              # load the voice now, not on the first sentence
    FILLERS = ("One moment, sir.", "Working on it.", "Give me a second.", "Let me check.")

    def reply_with_fillers(text):
        """Ask the agent in the background; if the answer takes a while, say so instead of going quiet."""
        import random
        box = {}
        th = threading.Thread(target=lambda: box.update(r=ask_troi(text, session)), daemon=True); th.start()
        th.join(4.0)
        if th.is_alive():
            say(random.choice(FILLERS))
            th.join(20.0)
            if th.is_alive():
                say("Still on it, sir. This one is taking a while.")
                th.join(240.0)
        return box.get("r") or "Sorry, sir, that took too long. Ask me again."

    vad = webrtcvad.Vad(2)
    level_frames = 0; level_sum = 0.0
    frames, speech_run, silence_run, in_utt = [], 0, 0, False
    started = time.time()
    heard_any = False
    threading.Thread(target=lambda: (time.sleep(2), say("Hello the owner, the agent here. What do you need?")), daemon=True).start()
    while not state["gone"]:
        try:
            buf = inbox.get(timeout=0.5)
        except queue.Empty:
            if not state["caller"] and time.time() - started > 180:
                log("nobody joined in three minutes, hanging up"); break
            continue
        if not heard_any:
            heard_any = True; log(f"hearing the caller ({len(buf)} bytes per frame)")
        for j in range(0, len(buf) - 319, 320):
            f = buf[j:j + 320]
            lvl = float(np.abs(np.frombuffer(f, dtype="<i2")).mean())
            level_frames += 1; level_sum = max(level_sum, lvl)
            if level_frames >= 500:                # every five seconds: the loudest frame heard
                log(f"caller level (5 s peak): {level_sum:.0f}" + ("  [the agent speaking, mic ignored]" if state["speaking"] else ""))
                level_frames = 0; level_sum = 0.0
            if state["speaking"]:
                continue                           # simple half-duplex: no listening while talking
            # webrtcvad is tuned for clean audio; phone audio is compressed, so
            # a plain level test backs it up
            sp = vad.is_speech(f, RATE) or lvl > 250
            if sp:
                speech_run += 1; silence_run = 0
                if speech_run >= 3: in_utt = True
                frames.append(f)
            else:
                silence_run += 1
                if in_utt: frames.append(f)
                too_long = in_utt and len(frames) >= 1200      # 12 s cap
                if (in_utt and silence_run >= 25) or too_long:   # 500 ms of quiet ends the sentence
                    pcm = np.frombuffer(b"".join(frames), dtype="<i2")
                    frames, speech_run, silence_run, in_utt = [], 0, 0, False
                    if len(pcm) < RATE * 1.0:
                        continue                        # under a second: a cough, a scrap, not a sentence
                    if not is_owner(pcm):
                        log("(not the owner's voice, ignored)"); continue
                    log(f"utterance {len(pcm) / RATE:.1f}s, transcribing")
                    text = ears.transcribe(pcm)
                    if not text or is_hallucination(text):
                        log(f"(dropped: {text!r})"); continue
                    log(f"[owner] {text}")
                    if any(w in text.lower() for w in ("goodbye troi", "hang up", "end the call", "bye troi")):
                        say("Goodbye, sir."); state["gone"] = True; break
                    reply = reply_with_fillers(text)
                    log(f"[troi] {reply}")
                    say(reply)
                elif not in_utt and silence_run > 50:
                    frames = frames[-8:]
    conn.unpublish_audio(); conn.disconnect(); conn.release(); svc.release()
    log("call ended")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print("App ID:", "set" if secret("agora-appid") else "MISSING (keychain.py set agora-appid)")
        print("Certificate:", "set" if secret("agora-cert") else "not set: fine only if the Agora project is in testing mode (App ID only); with a certificate enabled, joins fail until it is in the keychain as troi-agora-cert")
        print("call page:", settings().get("call_page") or f"http://{lan_ip()}:8796/call.html (LAN only until hosted)")
        try:
            import agora.rtc.agora_service, agora_token_builder, webrtcvad  # noqa
            print("SDK: ok")
        except Exception as e:
            print("SDK: missing", e)
        return 0
    if not secret("agora-appid"):
        print("Agora is not set up yet: add the App ID (and certificate) to the keychain (see the top of this file).")
        return 1
    if cmd == "link":
        ch, url = make_link(); print(url); return 0
    if cmd == "answer":
        return answer(sys.argv[2])
    if cmd == "call":
        ch, url = make_link()
        subprocess.run([sys.executable, str(HERE / "telegram.py"), "send", f"Tap to talk to me: {url}"], timeout=30)
        print(f"link sent; answering {ch}")
        return answer(ch)
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main())
