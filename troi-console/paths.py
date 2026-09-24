"""Where everything lives. The repo is the agent's home (its CLAUDE.md, .mcp.json and .claude/ sit at the root);
everything the agent writes goes under data/ (TROI_DATA overrides it): one SQLite record, one blob folder for every
binary, logs, a throwaway cache, the voice and face prints, the agent's browser profile and the downloaded models.
Nothing else on the Mac is written to, apart from the vault the owner chose and macOS's own integration points."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "troi-console"
DATA = Path(os.environ.get("TROI_DATA") or ROOT / "data")
DB = DATA / "troi.db"
CONFIG = DATA / "console.json"            # the owner's settings (written by onboarding and the Modes page)
BLOBS = DATA / "blobs"                    # every binary: blobs/<kind>/…, indexed in the blobs table of troi.db
LOGS = DATA / "logs"
CACHE = DATA / "cache"                    # safe to delete at any time
PRINTS = DATA / "prints"                  # prints/voice/owner.npy, prints/face/owner.npy (+ enrolment shots)
BROWSER = DATA / "browser"                # the agent's own Chrome profile
MODELS = DATA / "models"                  # whisper, and HF_HOME / TORCH_HOME for kokoro and the face model
TRASH = DATA / "trash"
LIVE = CACHE / "live.jpg"                 # the camera's newest frame while eyes are on (never kept)
BACKTALK = ROOT / "backtalk"
BAREHANDS = ROOT / "barehands"
KINDS = ("looks", "screens", "research", "imagined", "telegram", "meetings", "reports", "reviews", "board", "uploads")


def blob_dir(kind: str) -> Path:
    d = BLOBS / kind; d.mkdir(parents=True, exist_ok=True); return d


def ensure():
    for d in (DATA, BLOBS, LOGS, CACHE, PRINTS / "voice", PRINTS / "face", BROWSER, MODELS, TRASH):
        d.mkdir(parents=True, exist_ok=True)
    for d in ("misc", "models", "research"):                 # the hands board's airlock: it shows only files inside it
        (BAREHANDS / "media" / d).mkdir(parents=True, exist_ok=True)
    (BAREHANDS / "state").mkdir(parents=True, exist_ok=True)  # where the voice line and the hooks tell the board what the agent is doing


ensure()
