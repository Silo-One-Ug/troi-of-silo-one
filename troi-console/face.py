#!/usr/bin/env python3
"""Face ID: the owner's face as a second way to prove it is them (beside the voice print, the PIN
and Telegram). A real face-recognition model (facenet, VGGFace2 weights) in its own environment
(.venv-face), never the voice line's. Everything stays on this Mac.

  face.py enrol [--shots 5]     five photos a second apart → data/prints/face/owner.npy (look at the camera)
  face.py verify [image]        a fresh photo (or the given file) against the print → {"ok", "sim", "threshold"}
  face.py check                 what is in place

Threshold: console.json "face_id_threshold" (default 0.70; the same person scores ~0.75–0.95,
strangers ~0.2–0.6). A photo held up to the camera can fool it; the PIN cannot.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
DIR = P.PRINTS / "face"
PRINT = DIR / "owner.npy"
SETTINGS = P.CONFIG
_MODELS = {}


def settings():
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


def snap(path, warm=1.2):
    r = subprocess.run(["/opt/homebrew/bin/imagesnap", "-q", "-w", str(warm), str(path)], capture_output=True, text=True, timeout=30)
    return r.returncode == 0 and Path(path).exists()


def models():
    if not _MODELS:
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1
        torch.set_num_threads(4)
        _MODELS["mtcnn"] = MTCNN(image_size=160, margin=24, keep_all=False, post_process=True, device="cpu")
        _MODELS["net"] = InceptionResnetV1(pretrained="vggface2").eval()
    return _MODELS


def embed(image_path):
    """The face in the picture as a unit vector, or None if no face is there."""
    import numpy as np
    from PIL import Image, ImageOps
    m = models()
    img = ImageOps.exif_transpose(Image.open(image_path).convert("RGB"))
    face, prob = m["mtcnn"](img, return_prob=True)
    if face is None or (prob is not None and float(prob) < 0.85):
        return None
    import torch
    with torch.no_grad():
        e = m["net"](face.unsqueeze(0))[0].numpy()
    return e / (np.linalg.norm(e) + 1e-9)


def enrol(shots=5):
    import numpy as np
    DIR.mkdir(exist_ok=True)
    embs = []
    for i in range(shots):
        p = DIR / f"shot-{i:02d}.jpg"
        if not snap(p, warm=1.2 if i == 0 else 0.6):
            continue
        e = embed(p)
        if e is not None:
            embs.append(e)
        time.sleep(0.6)
    if len(embs) < 3:
        return {"ok": False, "error": f"only {len(embs)} clear shot(s) of a face; face the camera in decent light and try again"}
    mean = np.mean(embs, axis=0); mean /= np.linalg.norm(mean)
    # how alike the shots are: a sanity figure for the doctor
    spread = float(min(np.dot(e, mean) for e in embs))
    np.save(PRINT, mean)
    return {"ok": True, "shots": len(embs), "consistency": round(spread, 3)}


def verify(image=None):
    import numpy as np
    if not PRINT.exists():
        return {"ok": False, "error": "no face print yet (face.py enrol)"}
    p = Path(image) if image else DIR / "check.jpg"
    if not image and not snap(p):
        return {"ok": False, "error": "camera capture failed"}
    e = embed(p)
    if e is None:
        return {"ok": False, "sim": 0.0, "error": "no face in view"}
    th = float(settings().get("face_id_threshold", 0.70))
    sim = float(np.dot(e, np.load(PRINT)))
    return {"ok": sim >= th, "sim": round(sim, 3), "threshold": th}


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "check":
        print(json.dumps({"print": PRINT.exists(), "threshold": settings().get("face_id_threshold", 0.70), "shots": len(list(DIR.glob("shot-*.jpg"))) if DIR.exists() else 0}))
    elif a[0] == "enrol":
        n = int(a[a.index("--shots") + 1]) if "--shots" in a else 5
        print(json.dumps(enrol(n)))
    elif a[0] == "verify":
        print(json.dumps(verify(a[1] if len(a) > 1 else None)))
    elif a[0] == "embed":
        e = embed(a[1]); print(json.dumps({"face": e is not None}))
    else:
        print(__doc__)
