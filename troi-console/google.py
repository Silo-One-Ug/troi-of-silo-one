#!/usr/bin/env python3
"""google.py: the owner's Google account for the agent (Calendar, Gmail, Drive, Docs, Sheets, Tasks, Contacts), through
the Google Workspace MCP server (workspace-mcp, run with uvx) as one of the brain's tool servers: `google.sh mcp`.
Standard library only.

  google.py status                      what is set up: the OAuth client, the sign-in and its account, the runner
  google.py setup <client_secret.json>  keep the OAuth client Google gave you (data/google/client_secret.json, 0600)
  google.py enable [project]            turn the Google APIs on in the Cloud project (gcloud services enable …)
  google.py signin <email>              sign that account in once, in the browser; the token stays in data/google/
  google.py env                         the environment the MCP server runs with

The way in, once: a Google Cloud project with an OAuth client (a web application with the redirect URI
http://localhost:8788/oauth2callback, or a desktop app), the APIs turned on, and one sign-in in the browser. The
refresh token then lives in data/google/credentials/<email>.json, never in the record and never backed up. An app
left "In testing" on Google's side signs out after seven days; "In production" (no verification needed for your own
account, past a warning screen) does not.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as P  # noqa: E402

HERE = Path(__file__).resolve().parent
DIR = P.DATA / "google"
SECRET = DIR / "client_secret.json"
CREDS = DIR / "credentials"
PORT = 8788
APIS = ["calendar-json.googleapis.com", "gmail.googleapis.com", "drive.googleapis.com", "docs.googleapis.com",
        "sheets.googleapis.com", "tasks.googleapis.com", "people.googleapis.com"]
TOOLS = ["calendar", "gmail", "drive", "docs", "sheets", "tasks", "contacts"]
UVX = shutil.which("uvx") or str(Path.home() / ".local" / "bin" / "uvx")


def accounts():
    """The accounts signed in: one credential file per address."""
    return sorted(p.stem for p in CREDS.glob("*.json") if "@" in p.stem) if CREDS.exists() else []   # the server's own state files are not accounts


def env(email=""):
    e = {"GOOGLE_CLIENT_SECRET_PATH": str(SECRET), "WORKSPACE_MCP_CREDENTIALS_DIR": str(CREDS), "WORKSPACE_MCP_PORT": str(PORT),
         "GOOGLE_OAUTH_REDIRECT_URI": f"http://localhost:{PORT}/oauth2callback", "OAUTHLIB_INSECURE_TRANSPORT": "1", "MCP_SINGLE_USER_MODE": "1"}
    acc = email or (accounts()[0] if accounts() else "")
    if acc:
        e["USER_GOOGLE_EMAIL"] = acc
    return e


def status(line=False):
    ok_client = SECRET.exists(); acc = accounts(); ok_run = Path(UVX).exists()
    if line:
        if not ok_run: print("no uvx to run the Google tools (uv is missing)"); return 1
        if not ok_client: print("no Google OAuth client yet (google.py setup <client_secret.json>)"); return 1
        if not acc: print("Google client kept, no account signed in yet (google.py signin <email>)"); return 2
        print(f"Google signed in as {', '.join(acc)}"); return 0
    kind = ""
    if ok_client:
        try:
            d = json.loads(SECRET.read_text()); kind = "web application" if "web" in d else "desktop app" if "installed" in d else "unknown"
        except Exception:
            kind = "unreadable"
    print(f"runner:   {'uvx at ' + UVX if ok_run else 'uvx missing (install uv)'}")
    print(f"client:   {'kept, a ' + kind + ' (' + str(SECRET) + ')' if ok_client else 'none yet: google.py setup <client_secret.json>'}")
    print(f"account:  {', '.join(acc) if acc else 'not signed in: google.py signin <email>'}")
    print(f"tools:    {' '.join(TOOLS)}   (the brain sees them as mcp__google__*; names that delete are blocked by the guard)")
    print(f"callback: http://localhost:{PORT}/oauth2callback   tokens: {CREDS}")
    return 0


def setup(path):
    src = Path(os.path.expanduser(path))
    try:
        d = json.loads(src.read_text())
    except Exception as e:
        print(f"not a client secret file: {e}"); return 1
    body = d.get("web") or d.get("installed")
    if not body or not body.get("client_id"):
        print("that JSON has no OAuth client in it (expected a 'web' or 'installed' block with a client_id)"); return 1
    DIR.mkdir(parents=True, exist_ok=True); CREDS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, SECRET); os.chmod(SECRET, 0o600); os.chmod(DIR, 0o700)
    kind = "web application" if "web" in d else "desktop app"
    uris = body.get("redirect_uris") or []
    print(f"kept the OAuth client ({kind}) as {SECRET}")
    if "web" in d and f"http://localhost:{PORT}/oauth2callback" not in uris:
        print(f"  ! its redirect URIs do not include http://localhost:{PORT}/oauth2callback: add it in Google Cloud › Credentials, or the sign-in will fail")
    print(f"next: google.py enable [project]   then   google.py signin <your@gmail.com>")
    return 0


def enable(project=""):
    gcloud = shutil.which("gcloud")
    if not gcloud:
        print("gcloud is not installed: turn the APIs on in Google Cloud › APIs & Services › Library instead:"); print("  " + "\n  ".join(APIS)); return 1
    if not project:
        project = subprocess.run([gcloud, "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()
    if not project:
        print("no project: google.py enable <project-id>"); return 1
    print(f"turning on {len(APIS)} APIs in {project} (a minute)…")
    r = subprocess.run([gcloud, "services", "enable", *APIS, "--project", project], capture_output=True, text=True, timeout=600)
    print((r.stdout or r.stderr).strip()[-600:] or "done")
    return r.returncode


class _Mcp:
    """The smallest MCP client: the stdio server, JSON-RPC lines in and out."""
    def __init__(self, email):
        self.p = subprocess.Popen([str(HERE / "google.sh"), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                  env={**os.environ, **env(email)})
        self.n = 0

    def call(self, method, params=None, wait=True):
        self.n += 1; msg = {"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}
        self.p.stdin.write(json.dumps(msg) + "\n"); self.p.stdin.flush()
        if not wait:
            return None
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("the Google tool server went away")
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("id") == self.n:
                return d

    def notify(self, method, params=None):
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}) + "\n"); self.p.stdin.flush()

    def close(self):
        try:
            self.p.terminate()
        except Exception:
            pass


def signin(email):
    if not SECRET.exists():
        print("no OAuth client yet: google.py setup <client_secret.json>"); return 1
    if not email or "@" not in email:
        print("google.py signin <your@gmail.com>"); return 1
    CREDS.mkdir(parents=True, exist_ok=True)
    before = set(accounts())
    m = _Mcp(email)
    try:
        m.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "troi", "version": "1"}})
        m.notify("notifications/initialized")
        r = m.call("tools/call", {"name": "start_google_auth", "arguments": {"service_name": "Google Calendar", "user_google_email": email}})
        text = " ".join(c.get("text", "") for c in ((r.get("result") or {}).get("content") or []) if isinstance(c, dict))
        url = next((w for w in text.split() if w.startswith("https://accounts.google.com/")), "")
        print(text.strip()[:900] if not url else f"the sign-in page is open in the browser; if it is not, open this:\n\n{url}\n")
        print("waiting for the sign-in (up to five minutes)…")
        t0 = time.time()
        while time.time() - t0 < 300:
            time.sleep(2)
            new = set(accounts()) - before
            if new or (email in accounts() and CREDS.joinpath(email + ".json").stat().st_mtime > t0):
                print(f"signed in as {', '.join(sorted(new) or [email])}; the brain has the Google tools from its next session (or start Troi again)")
                return 0
        print("no sign-in arrived; run it again and finish the consent screen"); return 1
    finally:
        m.close()


def main(a):
    c = a[0] if a else "status"
    if c == "status":
        return status(line="--line" in a)
    if c == "setup" and len(a) > 1:
        return setup(a[1])
    if c == "enable":
        return enable(a[1] if len(a) > 1 else "")
    if c == "signin":
        return signin(a[1] if len(a) > 1 else "")
    if c == "env":
        for k, v in env().items():
            print(f"{k}={v}")
        return 0
    print(__doc__.strip()); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
