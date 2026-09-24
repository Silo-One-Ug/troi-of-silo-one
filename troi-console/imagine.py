#!/usr/bin/env python3
"""Make a picture from words.

  imagine.py "a gold globe on a dark desk"                 → prints the path of the PNG
  imagine.py "..." --show                                  also puts it on the hands board
  imagine.py "..." --size 1536x1024 --name globe           landscape, with a name for the file
  imagine.py "..." --from photo.jpg                        start from an existing picture (edit / restyle)
  imagine.py check                                         which backends are available

Pictures land in data/blobs/imagined/ (the Library shows them) with a .txt beside each
holding the prompt. Backends, first available wins:
  openai   key in the keychain:  keychain.py set openai   (or onboarding / Settings)
  gemini   key in the keychain:  keychain.py set gemini
Keys live in the keychain only, never in a file. Standard library only; runs on the system python.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402
import keychain as KC  # noqa: E402

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
OUT = P.blob_dir("imagined")
PREFER = ("openai", "gemini")


def keychain(service):
    try:
        return KC.get(service)
    except Exception:
        return ""


def post_json(url, payload, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def mime_of(path):
    ext = Path(path).suffix.lower()
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(ext.lstrip("."), "image/png")


# ---------------------------------------------------------------- backends
def via_openai(prompt, size, source):
    key = KC.get("openai")
    if not key:
        return None, "no OpenAI key"
    try:
        if source:
            # the edits endpoint takes multipart form data
            b = b"----troi" + os.urandom(8).hex().encode()
            body = b""
            for k, v in (("model", "gpt-image-1"), ("prompt", prompt), ("size", size), ("n", "1")):
                body += b"--" + b + f"\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
            body += (b"--" + b + f"\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{Path(source).name}\"\r\nContent-Type: {mime_of(source)}\r\n\r\n".encode()
                     + Path(source).read_bytes() + b"\r\n--" + b + b"--\r\n")
            req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "multipart/form-data; boundary=" + b.decode()})
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.load(r)
        else:
            d = post_json("https://api.openai.com/v1/images/generations", {"model": "gpt-image-1", "prompt": prompt, "size": size, "n": 1}, {"Authorization": f"Bearer {key}"}, timeout=240)
        item = (d.get("data") or [{}])[0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"]), ""
        if item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=120) as r:
                return r.read(), ""
        return None, "OpenAI returned no image"
    except urllib.error.HTTPError as e:
        return None, f"OpenAI {e.code}: {e.read()[:300].decode(errors='ignore')}"
    except Exception as e:
        return None, f"OpenAI: {e!r}"


def via_gemini(prompt, size, source):
    key = KC.get("gemini")
    if not key:
        return None, "no Gemini key"
    parts = [{"text": prompt + ("" if not source else " (use the attached picture as the starting point)")}]
    if source:
        parts.append({"inline_data": {"mime_type": mime_of(source), "data": base64.b64encode(Path(source).read_bytes()).decode()}})
    w, h = size.split("x"); ratio = "1:1" if w == h else ("3:2" if int(w) > int(h) else "2:3")
    payload = {"contents": [{"parts": parts}], "generationConfig": {"responseModalities": ["IMAGE", "TEXT"], "imageConfig": {"aspectRatio": ratio}}}
    last = ""
    for model in ("gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"):
        try:
            d = post_json(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", payload, {"x-goog-api-key": key}, timeout=240)
            for c in d.get("candidates", []):
                for p in (c.get("content") or {}).get("parts", []):
                    blob = p.get("inline_data") or p.get("inlineData")
                    if blob and blob.get("data"):
                        return base64.b64decode(blob["data"]), ""
            last = "Gemini returned no image"
        except urllib.error.HTTPError as e:
            last = f"Gemini {e.code}: {e.read()[:300].decode(errors='ignore')}"
            if e.code == 404:
                continue
            break
        except Exception as e:
            last = f"Gemini: {e!r}"; break
    return None, last


BACKENDS = {"openai": via_openai, "gemini": via_gemini}


def available():
    return [b for b in PREFER if keychain("troi-" + b)]


# ---------------------------------------------------------------- the tool
def imagine(prompt, size="1024x1024", name="", source="", show=False, backend=""):
    OUT.mkdir(parents=True, exist_ok=True)
    order = [backend] if backend else available()
    if not order:
        return {"ok": False, "error": "no image backend is set up. Put a key in the keychain: keychain.py set openai (or gemini)  (or troi-gemini)"}
    errors = []
    for b in order:
        data, err = BACKENDS[b](prompt, size, source)
        if data:
            slug = re.sub(r"[^a-z0-9]+", "-", (name or prompt).lower()).strip("-")[:40] or "picture"
            path = OUT / f"{dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}-{slug}.png"
            path.write_bytes(data)
            path.with_suffix(".txt").write_text(f"{prompt}\n\nbackend: {b}\nsize: {size}\n" + (f"from: {source}\n" if source else ""))
            shown = False
            if show:
                r = subprocess.run([str(HERE / "show-image.sh"), str(path), (name or prompt)[:60]], capture_output=True, text=True, timeout=30)
                shown = r.returncode == 0
            return {"ok": True, "path": str(path), "backend": b, "shown": shown}
        errors.append(err)
    return {"ok": False, "error": "; ".join(errors)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        av = available()
        print("image backends: " + (", ".join(av) if av else "none (add a key: keychain.py set openai (or gemini))"))
        print(f"pictures go to {OUT}")
        sys.exit(0 if av else 1)
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--size", default="1024x1024", help="1024x1024, 1536x1024 (landscape) or 1024x1536 (portrait)")
    ap.add_argument("--name", default="")
    ap.add_argument("--from", dest="source", default="")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--backend", default="", choices=["", "openai", "gemini"])
    a = ap.parse_args()
    if a.source and not Path(a.source).is_file():
        print(json.dumps({"ok": False, "error": f"no such picture: {a.source}"})); sys.exit(1)
    r = imagine(a.prompt, a.size, a.name, a.source, a.show, a.backend)
    print(json.dumps(r) if not r.get("ok") else r["path"] + ("  (on the board)" if r.get("shown") else ""))
    sys.exit(0 if r.get("ok") else 1)
