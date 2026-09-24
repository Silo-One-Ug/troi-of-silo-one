#!/usr/bin/env python3
"""stt.py: the words in an audio file, with the agent's own ears (backtalk's whisper). Run with backtalk's Python.

  stt.py <file>        print the words
  stt.py --serve       a resident worker for the server: one JSON line in ({"path": "..."}), one JSON line out
                       ({"text": "..."}); the model loads once and stays. The console's voice notes come this way.

Any format ffmpeg reads (webm/opus, mp4/aac, ogg, m4a, wav, aiff).
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
sys.path.insert(0, str(HOME / "backtalk"))       # the ears, when run with backtalk's Python
FFMPEG = "/opt/homebrew/bin/ffmpeg"


def words(path):
    import numpy as np
    from backtalk import ears
    r = subprocess.run([FFMPEG, "-v", "quiet", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, timeout=120)
    pcm = np.frombuffer(r.stdout, dtype="<i2")
    if len(pcm) < 8000:
        return ""
    return ears.transcribe(pcm)


def serve():
    proto, sys.stdout = sys.stdout, sys.stderr             # the ears may print; the protocol keeps stdout to itself
    try:
        from backtalk import ears
        ears.warm()
    except Exception:
        pass
    for line in sys.stdin:
        try:
            out = {"text": words(json.loads(line)["path"])}
        except Exception as e:
            out = {"text": "", "error": f"{type(e).__name__}: {e}"}
        proto.write(json.dumps(out) + "\n"); proto.flush()


def main(a):
    if a[:1] == ["--serve"]:
        serve(); return 0
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    print(words(a[0])); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
