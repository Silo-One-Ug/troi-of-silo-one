#!/usr/bin/env python3
"""The file hands, deeper (Silo One, 2026-09-27): what Finder does beyond moving. Everything stays inside the folders the agent
may touch (file_roots in the console's settings); nothing is ever overwritten, and nothing here removes anything: a duplicate
found is reported, and its removal is a Trash request through fs.sh, the owner's to approve.

  files.py zip <path> [dest.zip]           an archive beside it (ditto -c -k --keepParent); a name that exists gets " 2"
  files.py unzip <archive> [folder]        unpacked into a new folder beside it (ditto -x -k), never over an existing one
  files.py size <folder> [--top 12]        the folder's size and its largest children
  files.py dupes <folder> [--min 100k]     duplicate files (size, then a hash), in groups, with what they take; read-only
  files.py recent <folder> [--days 7]      files changed in the last N days, newest first
  files.py tag <path> <tag> [<tag>…]       Finder tags added to a file or folder (the ones it has are kept)
  files.py tags <path>                     the Finder tags on it
  files.py plan <folder> [--by-month]      a plan to organise it, by kind (or by month): what would move where; nothing moves

Stdlib and the Mac's own tools (ditto, du, xattr). Actions are logged to data/logs/fs.log like fs.sh's.
TROI_FILE_ROOTS (a colon-separated list) stands in for the settings' roots in a test.
"""
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

KINDS = [
    ("Screenshots", lambda n, e: n.lower().startswith(("screenshot", "screen shot", "capture d")) and e in {".png", ".jpg", ".jpeg"}),
    ("Images", lambda n, e: e in {".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif", ".webp", ".svg", ".tif", ".tiff", ".bmp", ".raw", ".dng"}),
    ("Video", lambda n, e: e in {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}),
    ("Audio", lambda n, e: e in {".mp3", ".m4a", ".wav", ".aiff", ".aif", ".flac", ".ogg", ".opus"}),
    ("Documents", lambda n, e: e in {".pdf", ".doc", ".docx", ".pages", ".txt", ".md", ".rtf", ".odt", ".epub"}),
    ("Spreadsheets", lambda n, e: e in {".xls", ".xlsx", ".csv", ".numbers", ".ods", ".tsv"}),
    ("Slides", lambda n, e: e in {".ppt", ".pptx", ".key", ".odp"}),
    ("Installers", lambda n, e: e in {".dmg", ".pkg", ".mpkg"}),
    ("Archives", lambda n, e: e in {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}),
    ("Code", lambda n, e: e in {".py", ".js", ".ts", ".tsx", ".sh", ".json", ".yaml", ".yml", ".toml", ".rs", ".go", ".java", ".c", ".h", ".swift", ".sql", ".html", ".css"}),
]


# ---- the roots, the log, the safe names
def roots():
    env = os.environ.get("TROI_FILE_ROOTS")
    if env:
        return [Path(p).expanduser().resolve() for p in env.split(":") if p]
    try:
        cfg = json.loads(P.CONFIG.read_text())
        rs = cfg.get("file_roots") or []
    except Exception:
        rs = []
    out = []
    for r in rs:
        try:
            out.append(Path(str(r)).expanduser().resolve())
        except Exception:
            pass
    return out


def inside(p):
    p = Path(p).expanduser().resolve()
    return any(p == r or r in p.parents for r in roots())


def must_be_inside(p):
    if not inside(p):
        print(f"outside the folders I may touch: {p}  (file_roots in the console's settings)"); sys.exit(2)
    return Path(p).expanduser().resolve()


def log(line):
    try:
        P.LOGS.mkdir(parents=True, exist_ok=True)
        with open(P.LOGS / "fs.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass


def free_name(p):
    """A path that does not exist yet: the name, or the name with ' 2', ' 3'… before the suffix. Nothing is ever overwritten."""
    p = Path(p)
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    if suf.lower() == ".zip" or p.is_dir() or not suf:
        pass
    for n in range(2, 1000):
        q = p.with_name(f"{stem} {n}{suf}")
        if not q.exists():
            return q
    raise SystemExit("no free name")


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def size_arg(s, default):
    s = str(s or "").strip().lower()
    if not s:
        return default
    mult = {"k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}
    if s[-1] in mult:
        return int(float(s[:-1]) * mult[s[-1]])
    return int(float(s))


# ---- the actions
def cmd_zip(a):
    if not a:
        print("usage: files.py zip <path> [dest.zip]"); return 2
    src = must_be_inside(a[0])
    if not src.exists():
        print(f"no such file or folder: {a[0]}"); return 2
    dest = Path(a[1]).expanduser().resolve() if len(a) > 1 else src.with_name(src.name + ".zip")
    if not inside(dest.parent):
        print(f"the archive would land outside the folders I may touch: {dest}"); return 2
    dest = free_name(dest)
    r = subprocess.run(["ditto", "-c", "-k", "--keepParent", "--sequesterRsrc", str(src), str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        print("ditto refused: " + (r.stderr.strip() or "unknown")[:200]); return 1
    log(f"zip {src} -> {dest}")
    print(f"zipped: {dest}  ({human(dest.stat().st_size)})"); return 0


def cmd_unzip(a):
    if not a:
        print("usage: files.py unzip <archive> [folder]"); return 2
    src = must_be_inside(a[0])
    if not src.is_file():
        print(f"no such archive: {a[0]}"); return 2
    dest = Path(a[1]).expanduser().resolve() if len(a) > 1 else src.with_name(src.stem)
    if not inside(dest.parent if not dest.exists() else dest):
        print(f"it would unpack outside the folders I may touch: {dest}"); return 2
    dest = free_name(dest)
    dest.mkdir(parents=True, exist_ok=False)
    r = subprocess.run(["ditto", "-x", "-k", str(src), str(dest)], capture_output=True, text=True)
    if r.returncode != 0:
        print("ditto refused: " + (r.stderr.strip() or "unknown")[:200]); return 1
    n = sum(1 for _ in dest.rglob("*"))
    log(f"unzip {src} -> {dest}")
    print(f"unpacked into: {dest}  ({n} item{'s' if n != 1 else ''})"); return 0


def walk_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if not d.startswith(".") and not d.endswith(".app")]
        for fn in fns:
            if fn.startswith("."):
                continue
            p = Path(dp) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            if not p.is_file():
                continue
            yield p, st


def cmd_size(a):
    top = 12
    if "--top" in a:
        i = a.index("--top"); top = int(a[i + 1]); del a[i:i + 2]
    if not a:
        print("usage: files.py size <folder> [--top 12]"); return 2
    root = must_be_inside(a[0])
    if not root.is_dir():
        print(f"not a folder: {a[0]}"); return 2
    total = 0; rows = []
    for child in sorted(root.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            s = sum(st.st_size for _, st in walk_files(child))
        else:
            try:
                s = child.stat().st_size
            except OSError:
                s = 0
        total += s; rows.append((s, child))
    rows.sort(key=lambda r: -r[0])
    print(f"{root}: {human(total)} in {len(rows)} item{'s' if len(rows) != 1 else ''}")
    for s, c in rows[:top]:
        print(f"  {human(s):>10}  {c.name}{'/' if c.is_dir() else ''}")
    if len(rows) > top:
        print(f"  … and {len(rows) - top} more, {human(sum(s for s, _ in rows[top:]))} together")
    return 0


def cmd_dupes(a):
    mn = 100 * 1024
    if "--min" in a:
        i = a.index("--min"); mn = size_arg(a[i + 1], mn); del a[i:i + 2]
    if not a:
        print("usage: files.py dupes <folder> [--min 100k]"); return 2
    root = must_be_inside(a[0])
    if not root.is_dir():
        print(f"not a folder: {a[0]}"); return 2
    by_size = {}
    for p, st in walk_files(root):
        if st.st_size >= mn:
            by_size.setdefault(st.st_size, []).append(p)
    groups = []
    for size, ps in by_size.items():
        if len(ps) < 2:
            continue
        by_hash = {}
        for p in ps:
            try:
                h = hashlib.sha1()
                with open(p, "rb") as f:
                    while True:
                        b = f.read(1 << 20)
                        if not b:
                            break
                        h.update(b)
                by_hash.setdefault(h.hexdigest(), []).append(p)
            except OSError:
                continue
        for hs, same in by_hash.items():
            if len(same) > 1:
                groups.append((size, sorted(same, key=lambda p: p.stat().st_mtime)))
    if not groups:
        print(f"no duplicates over {human(mn)} in {root}"); return 0
    groups.sort(key=lambda g: -g[0] * (len(g[1]) - 1))
    waste = sum(s * (len(ps) - 1) for s, ps in groups)
    print(f"{len(groups)} group{'s' if len(groups) != 1 else ''} of duplicates in {root}, {human(waste)} taken by the copies (nothing removed: a Trash request is the owner's to approve)")
    for s, ps in groups[:40]:
        print(f"  {human(s):>10}  x{len(ps)}")
        for p in ps:
            print(f"              {p.relative_to(root)}  ({datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d})")
    if len(groups) > 40:
        print(f"  … and {len(groups) - 40} more groups")
    return 0


def cmd_recent(a):
    days = 7
    if "--days" in a:
        i = a.index("--days"); days = float(a[i + 1]); del a[i:i + 2]
    if not a:
        print("usage: files.py recent <folder> [--days 7]"); return 2
    root = must_be_inside(a[0])
    if not root.is_dir():
        print(f"not a folder: {a[0]}"); return 2
    since = time.time() - days * 86400
    rows = sorted(((st.st_mtime, st.st_size, p) for p, st in walk_files(root) if st.st_mtime >= since), reverse=True)
    if not rows:
        print(f"nothing changed in {root} in the last {days:g} day{'s' if days != 1 else ''}"); return 0
    print(f"{len(rows)} file{'s' if len(rows) != 1 else ''} changed in {root} in the last {days:g} day{'s' if days != 1 else ''}:")
    for mt, s, p in rows[:60]:
        print(f"  {datetime.fromtimestamp(mt):%a %d %b %H:%M}  {human(s):>9}  {p.relative_to(root)}")
    if len(rows) > 60:
        print(f"  … and {len(rows) - 60} more")
    return 0


TAG_ATTR = "com.apple.metadata:_kMDItemUserTags"


def read_tags(p):
    r = subprocess.run(["xattr", "-px", TAG_ATTR, str(p)], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        raw = bytes.fromhex("".join(r.stdout.split()))
        tags = plistlib.loads(raw)
        return [str(t).split("\n")[0] for t in tags] if isinstance(tags, list) else []
    except Exception:
        return []


def cmd_tag(a):
    if len(a) < 2:
        print("usage: files.py tag <path> <tag> [<tag>…]"); return 2
    p = must_be_inside(a[0])
    if not p.exists():
        print(f"no such file or folder: {a[0]}"); return 2
    have = read_tags(p); new = [t for t in a[1:] if t and t not in have]
    tags = have + new
    raw = plistlib.dumps(tags, fmt=plistlib.FMT_BINARY)
    r = subprocess.run(["xattr", "-wx", TAG_ATTR, raw.hex(), str(p)], capture_output=True, text=True)
    if r.returncode != 0:
        print("xattr refused: " + (r.stderr.strip() or "unknown")[:200]); return 1
    log(f"tag {p} + {', '.join(new) or '(nothing new)'}")
    print(f"tags on {p.name}: {', '.join(tags) or 'none'}"); return 0


def cmd_tags(a):
    if not a:
        print("usage: files.py tags <path>"); return 2
    p = must_be_inside(a[0])
    print(", ".join(read_tags(p)) or "no tags"); return 0


def kind_of(p):
    e = p.suffix.lower()
    for name, test in KINDS:
        if test(p.name, e):
            return name
    return "Other"


def cmd_plan(a):
    by_month = "--by-month" in a
    a = [x for x in a if x != "--by-month"]
    if not a:
        print("usage: files.py plan <folder> [--by-month]"); return 2
    root = must_be_inside(a[0])
    if not root.is_dir():
        print(f"not a folder: {a[0]}"); return 2
    files = [c for c in root.iterdir() if c.is_file() and not c.name.startswith(".")]
    if not files:
        print(f"{root} has no loose files to organise"); return 0
    groups = {}
    for f in files:
        key = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m") if by_month else kind_of(f)
        groups.setdefault(key, []).append(f)
    print(f"A plan for {root}: {len(files)} loose file{'s' if len(files) != 1 else ''} into {len(groups)} folder{'s' if len(groups) != 1 else ''}. Nothing has moved; say the word and I move them with fs.sh.")
    for key in sorted(groups, key=lambda k: -len(groups[k])):
        fs = sorted(groups[key], key=lambda f: f.name.lower()); size = sum(f.stat().st_size for f in fs)
        exists = (root / key).is_dir()
        print(f"  {key}/{' (exists)' if exists else ''}  <- {len(fs)} file{'s' if len(fs) != 1 else ''}, {human(size)}: " + ", ".join(f.name for f in fs[:6]) + (f" … and {len(fs) - 6} more" if len(fs) > 6 else ""))
    return 0


def main(argv):
    a = list(argv)
    if not a or a[0] in ("-h", "--help"):
        print(__doc__.strip()); return 0
    fn = {"zip": cmd_zip, "unzip": cmd_unzip, "size": cmd_size, "dupes": cmd_dupes, "recent": cmd_recent, "tag": cmd_tag, "tags": cmd_tags, "plan": cmd_plan}.get(a[0])
    if not fn:
        print("files.py zip|unzip|size|dupes|recent|tag|tags|plan   (--help for the shapes)"); return 2
    return fn(a[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
