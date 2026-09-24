#!/usr/bin/env python3
"""The agent on Telegram, two-way. Stdlib only.

  you -> the agent   messages to the bot are answered by the agent (a Claude Code
                session in the agent's folder (the repo root): same identity, memory and rules,
                the deletion guard included). Photos are looked at too.
  the agent -> you   anything can send you a message with `telegram.py send "text"`
                or a voice note with `telegram.py say "text"` (the pulse sends
                reminders, CI and server changes and calendar heads-ups this way).
  voice notes   a voice note you send is transcribed with the agent's own ears and
                answered with text AND a voice note in the agent's voice.
                Run with backtalk's Python so the ears and voice are available.

Setup, once:
  1. In Telegram, talk to @BotFather: /newbot, pick a name; it gives a token.
  2. Keep the token in the macOS Keychain (never in a file): the welcome's "Your phone" step,
     or troi-console/keychain.py set telegram and paste the token at the prompt.
  3. Restart the bridge: python3 troi-console/setup.py services restart telegram (the welcome does it).
  4. Message the bot the 6-digit pairing code the welcome shows (it is also in data/logs/telegram.log).
     That Telegram account becomes the owner; everyone else is ignored forever.
"""
import json
import os
import random
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import keychain as KC  # noqa: E402
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


def CALL():
    """How the agent addresses the owner mid-conversation (the welcome's choice: sir, boss, madam, their name)."""
    try:
        return json.loads(_Pa.CONFIG.read_text()).get("call") or "sir"
    except Exception:
        return "sir"
import os as _os2, json as _j2
try: VAULT = _j2.load(open(str(_Pa.CONFIG))).get("vault", str(_Pa.DATA / "vault"))
except Exception: VAULT = str(_Pa.DATA / "vault")

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
sys.path.insert(0, str(HOME / "backtalk"))       # the ears and the voice, when run with backtalk's Python
FFMPEG = "/opt/homebrew/bin/ffmpeg"
STATE = _DB.doc("telegram")          # owner id + conversation id (no secrets), in troi.db
LOGF = P.LOGS / "telegram.log"
INBOX = P.blob_dir("telegram")
CLAUDE = str(Path.home() / ".local" / "bin" / "claude")
MODEL = "claude-sonnet-5"
PATH = "/opt/homebrew/bin:/usr/local/bin:" + str(Path.home() / ".local" / "bin") + ":" + os.environ.get("PATH", "")


def log(line):
    LOGF.parent.mkdir(exist_ok=True)
    with LOGF.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    print(line, flush=True)


def token():
    try:
        return KC.get("telegram")
    except Exception:
        return ""


def api(method, tok, **params):
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def api_upload(method, tok, field, path, mime, **params):
    """multipart/form-data upload with the standard library."""
    b = b"----troi" + os.urandom(8).hex().encode()
    body = b""
    for k, v in params.items():
        body += b"--" + b + f"\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (b"--" + b + f"\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{Path(path).name}\"\r\n"
             f"Content-Type: {mime}\r\n\r\n".encode() + Path(path).read_bytes() + b"\r\n--" + b + b"--\r\n")
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=body,
                                 headers={"Content-Type": "multipart/form-data; boundary=" + b.decode()})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def transcribe_file(path):
    """Any audio Telegram sends (ogg/opus, m4a, mp3) -> text, with the agent's own ears."""
    import numpy as np
    from backtalk import ears
    r = subprocess.run([FFMPEG, "-v", "quiet", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, timeout=120)
    pcm = np.frombuffer(r.stdout, dtype="<i2")
    if len(pcm) < 8000:
        return ""
    return ears.transcribe(pcm)


def voice_note(text):
    """the agent's voice as an .ogg (Opus) file, the format Telegram voice bubbles use."""
    import numpy as np, wave
    from backtalk.config import CFG
    from kokoro import KPipeline
    if not hasattr(voice_note, "pipe"):
        voice_note.pipe = KPipeline(lang_code=CFG.get("voice", "bm_lewis")[0])
    clean = " ".join(text.replace("`", "").replace("*", "").replace("#", "").split())
    chunks = [np.asarray(a, dtype="float32") for _, _, a in voice_note.pipe(clean[:1500], voice=CFG.get("voice", "bm_lewis"))]
    if not chunks:
        return None
    INBOX.mkdir(parents=True, exist_ok=True)
    wav = INBOX / "troi.wav"; ogg = INBOX / f"troi-{time.strftime('%H%M%S')}.ogg"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes((np.clip(np.concatenate(chunks), -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run([FFMPEG, "-v", "quiet", "-y", "-i", str(wav), "-c:a", "libopus", "-b:a", "32k", "-application", "voip", str(ogg)],
                   timeout=120)
    return ogg if ogg.exists() else None


def say(text, tok=None):
    """Send the owner a voice note (and the text) from anywhere: telegram.py say "..." """
    st = state(); tok = tok or token()
    if not tok or not st.get("owner"):
        return False
    ogg = voice_note(text)
    if ogg:
        api_upload("sendVoice", tok, "voice", ogg, "audio/ogg", chat_id=st["owner"], caption=text[:1000])
    else:
        api("sendMessage", tok, chat_id=st["owner"], text=text)
    return True


def state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save(st):
    STATE.write_text(json.dumps(st, indent=2))


def send(text, tok=None):
    st = state(); tok = tok or token()
    if not tok or not st.get("owner"):
        return False
    for i in range(0, len(text), 3900):
        api("sendMessage", tok, chat_id=st["owner"], text=text[i:i + 3900])
    return True


def shared_session():
    """The one session everything shares: the voice line's (it resumes it on every launch)."""
    try:
        return (HOME / "backtalk" / ".backtalk_session").read_text().strip()
    except Exception:
        return ""


def ask_troi(text, st, image=None):
    """One turn with the agent, in the ONE shared conversation: through the live voice line when it is
    running (the room stays silent for these), otherwise by resuming the same session ourselves."""
    prompt = text
    if image:
        prompt = f"{text or '(no caption)'} (the owner sent this photo on Telegram: {image}. Read it and respond to it.)"
    tagged = ("(via telegram) " + prompt + " (This arrived on Telegram from the owner's phone: reply in plain text, no markdown, "
              "a few short paragraphs at most.)")
    try:
        req = urllib.request.Request("http://127.0.0.1:8796/ask", data=json.dumps({"text": tagged}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
        if d.get("live") and d.get("reply"):
            return d["reply"]
        if d.get("live"):
            return f"I heard you, {CALL()}, but the reply got lost on the way back; ask me again."
    except Exception as e:
        log(f"live brain not reachable ({e!r}); resuming the shared session myself")
    cmd = [CLAUDE, "-p", tagged, "--model", MODEL, "--permission-mode", "bypassPermissions",
           "--settings", str(HOME / ".claude" / "settings.json"), "--add-dir", str(VAULT),
           "--max-turns", "12", "--output-format", "json"]
    sid = shared_session()
    if sid:
        cmd += ["--resume", sid]
    r = subprocess.run(cmd, cwd=HOME, capture_output=True, text=True, timeout=600,
                       env={**os.environ, "PATH": PATH}, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(r.stdout)
        sid2 = out.get("session_id")
        if sid2:                                   # keep the shared pointer current for the next voice launch
            (HOME / "backtalk" / ".backtalk_session").write_text(sid2)
        return out.get("result") or "(no reply)"
    except Exception:
        log(f"claude error: {r.stderr[-300:]}")
        return f"Something went wrong on my end, {CALL()}. The error is in data/logs/telegram.log."


def photo_path(tok, file_id, ext=".jpg"):
    info = api("getFile", tok, file_id=file_id)["result"]
    INBOX.mkdir(parents=True, exist_ok=True)
    dst = INBOX / f"{time.strftime('%Y-%m-%d_%H-%M-%S')}{ext}"
    urllib.request.urlretrieve(f"https://api.telegram.org/file/bot{tok}/{info['file_path']}", dst)
    return str(dst)


def main():
    tok = token()
    if not tok:
        log("no bot token in the keychain yet (see the setup note at the top of telegram.py); idle")
        while not token():
            time.sleep(60)
        tok = token()
    st = state()
    if not st.get("owner"):
        st["code"] = st.get("code") or f"{random.randint(100000, 999999)}"
        save(st)
        log(f"PAIRING: send the code {st['code']} to the bot from your Telegram account")
    def _warm():
        try:
            from backtalk import ears; ears.warm(); log("ears ready for voice notes")
        except Exception as e:
            log(f"ears unavailable ({e!r}); voice notes will fail until run with backtalk's Python")
    import threading; threading.Thread(target=_warm, daemon=True).start()
    me = api("getMe", tok)["result"]["username"]
    log(f"up as @{me}" + (f", owner {st['owner']}" if st.get("owner") else ""))
    offset = st.get("offset", 0)
    while True:
        try:
            upd = api("getUpdates", tok, offset=offset, timeout=50)["result"]
        except Exception as e:
            log(f"poll error: {e!r}"); time.sleep(10); continue
        for u in upd:
            offset = u["update_id"] + 1; st["offset"] = offset; save(st)
            m = u.get("message") or {}
            chat, text = m.get("chat", {}).get("id"), m.get("text") or m.get("caption") or ""
            if chat is None:
                continue
            if not st.get("owner"):
                if text.strip() == st.get("code"):
                    st["owner"] = chat; st.pop("code", None); save(st)
                    api("sendMessage", tok, chat_id=chat, text=f"Paired. This is {AGENT}. Talk to me here any time.")
                    log(f"paired with chat {chat}")
                continue
            if chat != st["owner"]:
                continue                                # strangers are ignored
            image = None; spoken = False
            if m.get("photo"):
                try:
                    image = photo_path(tok, m["photo"][-1]["file_id"])
                except Exception as e:
                    log(f"photo error: {e!r}")
            snd = m.get("voice") or m.get("audio") or (m.get("document") if str((m.get("document") or {}).get("mime_type", "")).startswith("audio/") else None)
            if snd:
                try:
                    api("sendChatAction", tok, chat_id=chat, action="typing")
                    heard = transcribe_file(photo_path(tok, snd["file_id"], ext=".ogg"))
                    if heard:
                        text = (text + " " + heard).strip() if text else heard; spoken = True
                    else:
                        api("sendMessage", tok, chat_id=chat, text=f"I couldn't make out that voice note, {CALL()}."); continue
                except Exception as e:
                    log(f"voice note error: {e!r}"); api("sendMessage", tok, chat_id=chat, text=f"That voice note didn't come through, {CALL()}."); continue
            low = text.strip().lower().lstrip("/")
            if low in ("approve", "yes approve", "approved", "reject", "no reject", "rejected"):
                ok = low.startswith(("approve", "yes"))
                try:
                    req = urllib.request.Request("http://127.0.0.1:8796/approve", data=json.dumps({"ok": ok, "via": "telegram"}).encode(), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=40) as r:
                        d = json.load(r)
                    api("sendMessage", tok, chat_id=chat, text=(d.get("done") or d.get("error") or "done"))
                except Exception as e:
                    api("sendMessage", tok, chat_id=chat, text=f"Couldn't reach the console: {e}")
                continue
            if low in ("call", "call me", "ring me", "phone", "call troi", "voice call"):
                # the owner calls the agent: start a call (the agent joins and sends the link here)
                api("sendMessage", tok, chat_id=chat, text="Ringing. Tap the link that follows to talk to me.")
                subprocess.Popen([sys.executable, str(HERE / "agora_call.py"), "call"], cwd=HOME,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "PATH": PATH})
                log("[you] /call -> starting a call"); continue
            if not text and not image:
                continue
            log(f"[you] {text[:120]}" + (" +photo" if image else "") + (" (voice)" if spoken else ""))
            api("sendChatAction", tok, chat_id=chat, action="record_voice" if spoken else "typing")
            reply = ask_troi(text, st, image)
            log(f"[troi] {reply[:120]}")
            for i in range(0, len(reply), 3900):
                api("sendMessage", tok, chat_id=chat, text=reply[i:i + 3900])
            if spoken or st.get("voice_replies"):
                try:
                    ogg = voice_note(reply)
                    if ogg: api_upload("sendVoice", tok, "voice", ogg, "audio/ogg", chat_id=chat)
                except Exception as e:
                    log(f"voice reply error: {e!r}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "photo":
        tok = token(); st = state(); p = sys.argv[2]; cap = " ".join(sys.argv[3:])[:1000]
        if tok and st.get("owner") and Path(p).is_file():
            api_upload("sendPhoto", tok, "photo", p, "image/jpeg" if p.lower().endswith((".jpg", ".jpeg")) else "image/png", chat_id=st["owner"], caption=cap)
            print("sent"); sys.exit(0)
        print("no photo sent (token, pairing or file missing)"); sys.exit(1)
    if len(sys.argv) > 2 and sys.argv[1] == "send":
        sys.exit(0 if send(" ".join(sys.argv[2:])) else 1)
    if len(sys.argv) > 2 and sys.argv[1] == "say":
        sys.exit(0 if say(" ".join(sys.argv[2:])) else 1)
    main()
