#!/usr/bin/env python3
"""The agent's record: one SQLite file (data/troi.db), stdlib only, WAL mode, safe for several processes at once.
What goes in: the conversation (every line the voice log carries, in order, per session) and the cards drawn in it;
approvals and what became of them; the index of every binary in data/blobs (kind, size, hash, title, credits,
starred); reports and what the routines did; small documents the tools used to keep as JSON files (reminders, the
pulse's state, Telegram's state). Nothing is deleted by the agent: captures past their retention go to the Trash.

  db.py tail [N]         the last N conversation lines
  db.py sessions [--deleted]   sessions with their title (written for them, or the first real line) and size
  db.py title <id> <words>     name a session (the id, or the start of it)
  db.py stats            row counts and sizes
  db.py put <file> <kind> [title]    index a file in data/blobs (moves it there first if it is elsewhere); prints its path
  db.py index            index every file in data/blobs not yet known
  db.py star <id|path>   keep a capture past its retention
  db.py retain [days]    captures (looks, screens, Telegram) older than 14 days and not starred go to the Trash
  db.py doc <name>       print a stored document (reminders, pulse-state, telegram)
"""
import json
import sqlite3
import sys
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
PATH = P.DB
SCHEMA = """
create table if not exists sessions (id text primary key, title text default '', started real, last real);
create table if not exists messages (id integer primary key autoincrement, session text, role text, text text, meta text default '{}', t real, clock text default '');
create index if not exists messages_session on messages(session, id);
create table if not exists approvals (id text primary key, kind text, src text, why text, status text default 'open', decided_by text default '', at real, decided_at real);
create table if not exists blobs (id integer primary key autoincrement, kind text, path text unique, sha256 text default '', size integer default 0, mime text default '', title text default '', meta text default '{}', starred integer default 0, archived integer default 0, t real);
create index if not exists blobs_kind on blobs(kind, t);
create table if not exists docs (name text primary key, body text, t real);
create table if not exists reports (date text primary key, html text default '', pdf text default '', narrative text default '', sent integer default 0, t real);
create table if not exists runs (id integer primary key autoincrement, key text, result text default '', t real);
create table if not exists kv (key text primary key, value text);
"""


def connect():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(PATH), timeout=10, isolation_level=None)
    c.execute("pragma journal_mode=wal"); c.execute("pragma synchronous=normal")
    c.executescript(SCHEMA)
    if "meta" not in [r[1] for r in c.execute("pragma table_info(approvals)")]:      # the request itself, so it survives a restart
        c.execute("alter table approvals add column meta text default '{}'")
    cols = [r[1] for r in c.execute("pragma table_info(sessions)")]
    if "summary" not in cols:                                                         # a title written for it (a small model, the agent or the owner)
        c.execute("alter table sessions add column summary text default ''")
    if "deleted" not in cols:                                                         # when the owner took it off the list; its lines stay
        c.execute("alter table sessions add column deleted real default 0")
    c.row_factory = sqlite3.Row
    return c


def _j(x):
    return json.dumps(x) if not isinstance(x, str) else x


# ---- the conversation
def add_message(session, role, text, meta=None, clock="", t=None):
    t = t or time.time()
    with connect() as c:
        c.execute("insert or ignore into sessions(id, title, started, last) values(?, '', ?, ?)", (session or "", t, t))
        c.execute("update sessions set last=? where id=?", (t, session or ""))
        if role == "you":
            c.execute("update sessions set title=? where id=? and title=''", (text.strip()[:120], session or ""))
        cur = c.execute("insert into messages(session, role, text, meta, t, clock) values(?,?,?,?,?,?)", (session or "", role, text, _j(meta or {}), t, clock))
        return cur.lastrowid


def messages(session=None, limit=200, before=None):
    with connect() as c:
        q = "select id, session, role, text, meta, t, clock from messages"; w, a = [], []
        if session: w.append("session=?"); a.append(session)
        if before: w.append("id<?"); a.append(before)
        if w: q += " where " + " and ".join(w)
        rows = c.execute(q + " order by id desc limit ?", (*a, limit)).fetchall()
    return [dict(r, meta=json.loads(r["meta"] or "{}")) for r in reversed(rows)]


CONTROL = ("clear the session", "clear the context", "compact the session", "compact the context", "stop", "confirm", "usage report", "switch to the deep model",
           "back to the fast model", "go hands free", "push to talk mode", "stop asking for permission", "start asking again")


def _first_line(c, sid):
    """The first thing the owner said that can stand as a title: not a control phrase, not a stage line, a few words at least."""
    for r in c.execute("select text from messages where session=? and role='you' order by id limit 6", (sid,)):
        t = " ".join((r["text"] or "").split())
        if not t or t.startswith("(") or t.lower().rstrip(".!? ") in CONTROL or t.lower().startswith("set effort") or len(t.split()) < 3:
            continue
        return t[:100]
    return ""


def sessions(limit=50, deleted=False):
    """The sessions, newest last-spoken first: id, when, how many lines, and a title (the one written for it, else the
    owner's first real line, else the first line of all). deleted=True lists the ones the owner took off the list."""
    with connect() as c:
        rows = [dict(r) for r in c.execute("select s.id, s.title, s.summary, s.deleted, s.started, s.last, count(m.id) as n from sessions s left join messages m on m.session=s.id "
                                           "where s.id != '' and coalesce(s.deleted, 0) " + (">" if deleted else "=") + " 0 group by s.id order by s.last desc limit ?", (limit,))]
        for s in rows:
            s["first"] = _first_line(c, s["id"]); s["summary"] = s.get("summary") or ""; s["title"] = s["summary"] or s["first"] or s["title"]
        return rows


def session_find(ref):
    """A session by its id or the start of it (as the agent quotes them); None unless it names exactly one."""
    ref = (ref or "").strip()
    if not ref:
        return None
    with connect() as c:
        rows = c.execute("select id from sessions where id=? or id like ?", (ref, ref + "%")).fetchall()
    return rows[0]["id"] if len(rows) == 1 else None


def session_set(sid, **f):
    if not f:
        return False
    with connect() as c:
        return c.execute("update sessions set " + ", ".join(f"{k}=?" for k in f) + " where id=?", (*f.values(), sid)).rowcount > 0


def session_delete(sid):
    """Off the list, its lines kept: the owner's own act, or their approval of the agent's request."""
    return session_set(sid, deleted=time.time())


def session_restore(sid):
    return session_set(sid, deleted=0)


def session_title(sid, text):
    return session_set(sid, summary=" ".join(str(text or "").split())[:120])


def session_text(sid, limit=6000):
    """What was said in a session, owner and agent, for a title: the start and the end when it is long."""
    with connect() as c:
        lines = [f"{'Owner' if r['role'] == 'you' else 'Agent'}: {' '.join((r['text'] or '').split())}"
                 for r in c.execute("select role, text from messages where session=? and role in ('you', 'agent') order by id", (sid,))
                 if (r["text"] or "").strip() and not (r["text"] or "").startswith("(")]
    s = "\n".join(lines)
    return s if len(s) <= limit else s[: limit * 2 // 3] + "\n…\n" + s[-limit // 3:]


def last_id():
    with connect() as c:
        r = c.execute("select max(id) as m from messages").fetchone(); return int(r["m"] or 0)


# ---- approvals
def approval_add(rid, kind, src, why, at=None, meta=None):
    with connect() as c:
        c.execute("insert or replace into approvals(id, kind, src, why, status, at, meta) values(?,?,?,?, 'open', ?, ?)",
                  (rid, kind or "trash", src, why, at or time.time(), _j(meta or {})))


def approvals_open():
    """Requests still waiting for the owner, with what each one would do (the server restores them at start)."""
    with connect() as c:
        return [dict(r) for r in c.execute("select * from approvals where status='open' order by at")]


def approval_expire(rid):
    with connect() as c:
        c.execute("update approvals set status='expired', decided_by='restart', decided_at=? where id=?", (time.time(), rid))


def approval_decide(rid, ok, by="owner"):
    with connect() as c:
        c.execute("update approvals set status=?, decided_by=?, decided_at=? where id=?", ("approved" if ok else "rejected", by, time.time(), rid))


def approvals(limit=100):
    with connect() as c:
        return [dict(r) for r in c.execute("select * from approvals order by at desc limit ?", (limit,))]


# ---- the blob store: every binary lives in data/blobs/<kind>/, this is its index
import hashlib, mimetypes, shutil, subprocess  # noqa: E401,E402
RETAIN_KINDS = ("looks", "screens", "telegram")


def _sha(path, limit=64 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        n = 0
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk); n += len(chunk)
            if n >= limit: break
    return h.hexdigest()


def blob_add(path, kind=None, title="", meta=None, t=None):
    """Index a file under data/blobs (a file elsewhere is moved in first, under its kind). Returns its path."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return None
    try:
        p.relative_to(P.BLOBS.resolve())
    except ValueError:
        dest = P.blob_dir(kind or "uploads") / p.name
        if dest.exists(): dest = dest.with_name(f"{dest.stem}-{int(time.time())}{dest.suffix}")
        shutil.move(str(p), str(dest)); p = dest
    if kind is None:
        rel = p.relative_to(P.BLOBS.resolve()).parts; kind = rel[0] if len(rel) > 1 else "uploads"
    st = p.stat()
    with connect() as c:
        c.execute("insert into blobs(kind, path, sha256, size, mime, title, meta, t) values(?,?,?,?,?,?,?,?) "
                  "on conflict(path) do update set size=excluded.size, sha256=excluded.sha256, title=case when excluded.title != '' then excluded.title else blobs.title end, "
                  "meta=case when excluded.meta != '{}' then excluded.meta else blobs.meta end",
                  (kind, str(p), _sha(p), st.st_size, mimetypes.guess_type(p.name)[0] or "", title or "", _j(meta or {}), t or st.st_mtime))
    return str(p)


def blob_index():
    """Every file in data/blobs that the index does not know yet (any writer, any tool). Returns how many were added."""
    if not P.BLOBS.exists(): return 0
    with connect() as c:
        known = {r["path"] for r in c.execute("select path from blobs")}
    n = 0
    for f in P.BLOBS.rglob("*"):
        if f.is_file() and not f.name.startswith(".") and not f.is_symlink() and str(f.resolve()) not in known and f.suffix.lower() not in (".tmp", ".part", ".log"):
            if blob_add(f): n += 1
    return n


def blobs(kind=None, q="", limit=500, include_archived=False):
    with connect() as c:
        w, a = [], []
        if not include_archived: w.append("archived=0")
        if kind: w.append("kind=?"); a.append(kind)
        if q: w.append("(title like ? or meta like ? or path like ?)"); a += [f"%{q}%"] * 3
        rows = c.execute("select * from blobs" + (" where " + " and ".join(w) if w else "") + " order by t desc limit ?", (*a, limit)).fetchall()
    return [dict(r, meta=json.loads(r["meta"] or "{}")) for r in rows]


def blob_star(ref, on=True):
    with connect() as c:
        col = "id" if str(ref).isdigit() else "path"
        return c.execute(f"update blobs set starred=? where {col}=?", (1 if on else 0, int(ref) if col == "id" else str(Path(ref).expanduser().resolve()))).rowcount


def _to_trash(path):
    """Finder's move to the Trash: recoverable until the owner empties it."""
    r = subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{path}"'], capture_output=True, text=True, timeout=30)
    return r.returncode == 0


def retain(days=14):
    """Captures past their retention go to the Trash; starred ones stay. Returns the lines to log."""
    cut = time.time() - days * 86400; out = []
    with connect() as c:
        rows = c.execute(f"select id, path, kind from blobs where archived=0 and starred=0 and t < ? and kind in ({','.join('?' * len(RETAIN_KINDS))})", (cut, *RETAIN_KINDS)).fetchall()
    for r in rows:
        ok = not Path(r["path"]).exists() or _to_trash(r["path"])
        if ok:
            with connect() as c:
                c.execute("update blobs set archived=1 where id=?", (r["id"],))
            out.append(f"to the Trash: {r['kind']} {Path(r['path']).name}")
    return out


# the old name for research pictures, kept so pictures.py's call lands in the same index
def picture_add(kind, path, **f):
    meta = {k: f[k] for k in ("url", "query", "source", "author", "license", "page") if f.get(k)}
    return blob_add(path, "research" if kind == "research" else kind, title=f.get("title", ""), meta=meta, t=f.get("t"))


def pictures(kind=None, q="", limit=500):
    return blobs(kind, q, limit)


# ---- small documents the tools keep (reminders, the pulse's state, Telegram's state), with the few Path methods they use
class Doc:
    def __init__(self, name):
        self.name = name

    def read_text(self, *a, **k):
        with connect() as c:
            r = c.execute("select body from docs where name=?", (self.name,)).fetchone()
        if r is None: raise FileNotFoundError(f"troi.db:{self.name}")
        return r["body"]

    def write_text(self, body, *a, **k):
        with connect() as c:
            c.execute("insert or replace into docs(name, body, t) values(?,?,?)", (self.name, body, time.time()))
        return len(body)

    def exists(self):
        with connect() as c:
            return c.execute("select 1 from docs where name=?", (self.name,)).fetchone() is not None

    def unlink(self, missing_ok=True):
        with connect() as c:
            c.execute("delete from docs where name=?", (self.name,))

    def __str__(self):
        return f"troi.db:{self.name}"

    def __fspath__(self):
        return str(self)


def doc(name):
    return Doc(name)


def report_add(date, html="", pdf="", narrative="", sent=False):
    with connect() as c:
        c.execute("insert or replace into reports(date, html, pdf, narrative, sent, t) values(?,?,?,?,?,?)", (date, html, pdf, narrative, int(bool(sent)), time.time()))


def run_add(key, result=""):
    with connect() as c:
        c.execute("insert into runs(key, result, t) values(?,?,?)", (key, str(result)[:2000], time.time()))


def kv_get(key, default=None):
    with connect() as c:
        r = c.execute("select value from kv where key=?", (key,)).fetchone(); return json.loads(r["value"]) if r else default


def kv_set(key, value):
    with connect() as c:
        c.execute("insert or replace into kv(key, value) values(?,?)", (key, json.dumps(value)))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["tail"]:
        for m in messages(limit=int(a[1]) if len(a) > 1 else 20):
            print(f"{time.strftime('%m-%d %H:%M', time.localtime(m['t']))}  {m['role']:6}  {m['text'][:110]}")
    elif a[:1] == ["sessions"]:
        for s in sessions(deleted="--deleted" in a):
            print(f"{s['id'][:8]}  {time.strftime('%m-%d %H:%M', time.localtime(s['last'] or 0))}  {s['n']:4}  {s['title'][:80]}")
    elif a[:1] == ["title"] and len(a) > 2:
        sid = session_find(a[1]); print("titled" if sid and session_title(sid, " ".join(a[2:])) else "no such session (db.py sessions lists them)")
    elif a[:1] == ["stats"]:
        with connect() as c:
            for t in ("sessions", "messages", "approvals", "blobs", "reports", "runs", "docs"):
                print(f"{t}: {c.execute(f'select count(*) from {t}').fetchone()[0]}")
            b = c.execute("select count(*), coalesce(sum(size),0) from blobs where archived=0").fetchone()
            print(f"blob store: {b[0]} files, {b[1] / 1048576:.1f} MB · database: {P.DB.stat().st_size / 1048576:.1f} MB")
    elif a[:1] == ["put"] and len(a) >= 3:
        print(blob_add(a[1], a[2], title=" ".join(a[3:])) or "no such file")
    elif a[:1] == ["index"]:
        print(f"indexed {blob_index()} new file(s)")
    elif a[:1] == ["star"] and len(a) > 1:
        print("starred" if blob_star(a[1]) else "no such capture")
    elif a[:1] == ["retain"]:
        for line in retain(int(a[1]) if len(a) > 1 else 14): print(line)
    elif a[:1] == ["doc"] and len(a) > 1:
        try: print(doc(a[1]).read_text())
        except FileNotFoundError: print("{}")
    else:
        print(__doc__)
