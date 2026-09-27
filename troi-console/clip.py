#!/usr/bin/env python3
"""The clipboard (Silo One, 2026-09-27): what the owner just copied, and putting words there.

  clip.py get            what is on the clipboard: text (printed), copied files (their paths), or a picture (saved to
                         data/blobs/clips/<time>.png and its path printed)
  clip.py set "<text>"   put text on the clipboard (pbcopy)
  clip.py kind           text | files | image | empty, without showing anything

Caution: something that looks like a secret (a key, a token, a private key block, one long random string) is never printed:
`get` says so and stops, and the owner pastes it where it goes themselves. Text is cut at 4,000 characters. There is no
clipboard history: only what is on it now, when asked. Stdlib and the Mac's own tools (pbpaste, pbcopy, osascript).
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

LIMIT = 4000
SECRETS = [r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\bsk-[A-Za-z0-9_-]{16,}", r"\bgh[pousr]_[A-Za-z0-9]{20,}", r"\bAKIA[0-9A-Z]{16}\b",
           r"\bxox[abprs]-[A-Za-z0-9-]{10,}", r"\bey[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}", r"(?i)\b(password|passwd|secret|token|api[_ -]?key)\s*[:=]\s*\S{6,}"]


def looks_secret(t):
    s = t.strip()
    if any(re.search(p, s) for p in SECRETS):
        return True
    if " " not in s and "\n" not in s and 24 <= len(s) <= 200 and re.search(r"[A-Za-z]", s) and re.search(r"[0-9]", s) and not re.match(r"^https?://", s) and "/" not in s and "." not in s[:-8]:
        return True                                                  # one long random word: a token, a hash, a password
    return False


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
    return r.returncode == 0, (r.stdout or "").strip()


def kind():
    ok, info = osa("clipboard info")
    if not ok or not info:
        return "empty"
    low = info.lower()
    if "furl" in low or "file url" in low:
        return "files"
    if "pngf" in low or "tiff" in low or "jpeg" in low:
        return "image" if "utf8" not in low and "string" not in low else "text"
    return "text"


def get_text():
    r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10)
    return r.stdout if r.returncode == 0 else ""


def cmd_get():
    k = kind()
    if k == "files":
        ok, out = osa('set l to (the clipboard as list)\nset o to ""\nrepeat with x in l\ntry\nset o to o & POSIX path of (x as «class furl») & linefeed\nend try\nend repeat\nreturn o')
        paths = [p for p in out.splitlines() if p.strip()] if ok else []
        if paths:
            print("files on the clipboard:"); [print("  " + p) for p in paths]; return 0
        k = "text"
    if k == "image":
        d = P.DATA / "blobs" / "clips"; d.mkdir(parents=True, exist_ok=True)
        dest = d / f"{time.strftime('%Y-%m-%d_%H-%M-%S')}.png"
        ok, _ = osa(f'set f to open for access POSIX file "{dest}" with write permission\ntry\nwrite (the clipboard as «class PNGf») to f\nend try\nclose access f')
        if ok and dest.exists() and dest.stat().st_size > 0:
            print(f"a picture on the clipboard, saved: {dest}"); return 0
        print("a picture is on the clipboard but it could not be saved"); return 1
    t = get_text()
    if not t.strip():
        print("the clipboard is empty"); return 0
    if looks_secret(t):
        print(f"(the clipboard holds what looks like a secret: {len(t)} characters, not shown. Paste it where it goes yourself.)"); return 0
    shown = t if len(t) <= LIMIT else t[:LIMIT] + f"\n… ({len(t) - LIMIT} more characters)"
    print(shown); return 0


def cmd_set(a):
    text = " ".join(a)
    if not text:
        print('usage: clip.py set "<text>"'); return 2
    r = subprocess.run(["pbcopy"], input=text, text=True, timeout=10)
    if r.returncode != 0:
        print("pbcopy refused"); return 1
    print(f"on the clipboard: {len(text)} characters"); return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    if a[0] == "get":
        return cmd_get()
    if a[0] == "set":
        return cmd_set(a[1:])
    if a[0] == "kind":
        print(kind()); return 0
    print("clip.py get | set \"<text>\" | kind"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
