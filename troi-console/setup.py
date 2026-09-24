#!/usr/bin/env python3
"""Everything personal, rendered from the repo's templates: the agent's boot file and Claude settings, the three
components' configs, the vault seed, the background services, the Desktop shortcut. Onboarding calls it; so does
install.sh. Safe to run again at any time: it rewrites what it owns and keeps everything else.

  setup.py render                 CLAUDE.md, .mcp.json, .claude/settings.json, the components' configs, Claude's memory pointer
  setup.py vault new [path]       seed a new vault (default: data/vault) from vault-template, git-backed
  setup.py vault use <path>       point the agent at an existing vault
  setup.py services install       render and load the services (pulse, globe, Telegram, nightly backups)
  setup.py services restart [n]   restart one service (or all)
  setup.py services status        which are running
  setup.py services remove        unload them
  setup.py shortcut               the Desktop shortcut that starts everything
  setup.py status                 what is set up (JSON)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P  # noqa: E402

ROOT = P.ROOT
TPL = P.CONSOLE / "templates"
AGENT = "Troi"
LABEL = "com.troi-of-silo-one"
SERVICES = ("pulse", "ring", "telegram", "vault-backup")
LAUNCH = Path.home() / "Library" / "LaunchAgents"

DEFAULTS = {
    "owner": "", "owner_full": "", "address": "", "call": "sir",
    "vault": "", "vault_repo": "", "backup_repo": "", "github_org": "",
    "wake_word": True, "wake_names": ["troi", "troy", "troye", "troie", "troix", "troya"], "barge_in": True,
    "eyes": "off", "voice_id": "off", "voice_id_threshold": 0.78, "face_id_threshold": 0.7, "face_gate": False,
    "brief_time": "08:00", "brief_enabled": True, "report_time": "18:30", "report_enabled": True,
    "living_greeting": True, "guard_settings": True, "cues": True, "duck_music": False, "call_page": "",
    "tts": "kokoro", "elevenlabs_voice": "", "welcomed": False, "board_label": "Chief of Staff",
    "file_roots": [], "projects": {}, "projects_root": str(Path.home() / "Projects"),
    "hand_tuning": {"pinch_close": 0.32, "pinch_open": 0.48, "ext": 1.45, "dwell_ms": 1300, "magnet": 16},
}


def load() -> dict:
    try:
        cur = json.loads(P.CONFIG.read_text())
    except Exception:
        cur = {}
    return {**DEFAULTS, **cur}


def save(cfg: dict):
    P.CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = P.CONFIG.with_suffix(".tmp"); tmp.write_text(json.dumps(cfg, indent=2)); os.replace(tmp, P.CONFIG)


def fields(cfg: dict) -> dict:
    owner = (cfg.get("owner") or "").strip() or "the owner"
    return {"__ROOT__": str(ROOT), "__HOME__": str(Path.home()), "__VAULT__": cfg.get("vault") or str(P.DATA / "vault"),
            "__AGENT__": AGENT, "__agent__": AGENT.lower(), "__OWNER__": owner,
            "__OWNER_FULL__": (cfg.get("owner_full") or "").strip() or owner,
            "__ADDRESS__": (cfg.get("address") or "").strip() or owner, "__CALL__": (cfg.get("call") or "").strip() or "sir"}


def fill(text: str, f: dict) -> str:
    for k, v in f.items():
        text = text.replace(k, v)
    return text


def _merge_json(path: Path, managed: dict, example: Path | None = None):
    try:
        cur = json.loads(path.read_text())
    except Exception:
        try:
            cur = json.loads(example.read_text()) if example and example.exists() else {}
        except Exception:
            cur = {}
    for k, v in managed.items():
        if isinstance(v, dict) and isinstance(cur.get(k), dict):
            cur[k] = {**cur[k], **v}
        else:
            cur[k] = v
    path.write_text(json.dumps(cur, indent=2))


def render() -> list:
    cfg = load(); f = fields(cfg); done = []
    if not cfg.get("vault"):
        cfg["vault"] = f["__VAULT__"]
    default_vault = str(P.DATA / "vault")                          # the vault is always one of the folders it may organise;
    roots = [r for r in cfg.get("file_roots") or [] if r != default_vault or cfg["vault"] == default_vault]   # a vault moved elsewhere leaves no stale root
    cfg["file_roots"] = roots + ([cfg["vault"]] if cfg["vault"] not in roots else [])
    save(cfg)
    # the agent's boot file and Claude Code's settings for this folder
    (ROOT / "CLAUDE.md").write_text(fill((TPL / "CLAUDE.md").read_text(), f)); done.append("CLAUDE.md")
    (ROOT / ".mcp.json").write_text(fill((TPL / "mcp.json").read_text(), f)); done.append(".mcp.json")
    (ROOT / ".claude").mkdir(exist_ok=True)
    st = json.loads(fill((TPL / "settings.json").read_text(), f))
    dirs = st["permissions"].setdefault("additionalDirectories", [])
    dirs += [r for r in cfg.get("file_roots", []) if r not in dirs]      # the folders it may organise, readable without asking
    (ROOT / ".claude" / "settings.json").write_text(json.dumps(st, indent=2)); done.append(".claude/settings.json")
    # the components
    owner = f["__OWNER__"]
    _merge_json(P.BACKTALK / "backtalk.json", {
        "agent_dir": str(ROOT), "name": AGENT, "extra_dirs": sorted(set([f["__VAULT__"], *cfg.get("file_roots", [])])),
        "greeting": f"Hello {f['__ADDRESS__']}." if cfg.get("owner") else f"Hello. I'm {AGENT}. Let's get you set up.",
        "barehands_state_dir": str(P.BAREHANDS / "state"), "thinking_sound": str(P.CONSOLE / "assets" / "thinking-soft.wav"),
        "resume_last_session": True, "elevenlabs": {"key_slot": "troi-of-silo-one.elevenlabs", "enabled": cfg.get("tts") == "elevenlabs" and bool(cfg.get("elevenlabs_voice")), "voice_id": cfg.get("elevenlabs_voice", "")},
    }, P.BACKTALK / "backtalk.json.example")
    b = json.loads((P.BACKTALK / "backtalk.json").read_text())
    b.setdefault("ptt_key", "right_alt"); b.setdefault("mic_mode", "ptt"); b.setdefault("stt_model", "small.en"); b.setdefault("voice", "bm_lewis")
    if b.get("ptt_key") == "home": b["ptt_key"] = "right_alt"
    (P.BACKTALK / "backtalk.json").write_text(json.dumps(b, indent=2)); done.append("backtalk.json")
    _merge_json(P.BAREHANDS / "barehands.json", {"name": cfg.get("board_label") or "Chief of Staff", "port": 8794,
                                                 "orbs": [{"title": "Notes", "path": f["__VAULT__"], "kind": "notes"}, {"title": "Props", "path": "media", "kind": "media"}]},
                P.BAREHANDS / "barehands.json.example"); done.append("barehands.json")
    _merge_json(ROOT / "ai-visualizer" / "ai-visualizer.json", {"name": AGENT.upper(), "face": "board", "port": 8790, "bus_dir": str(P.BACKTALK), "thinking_sound": True},
                ROOT / "ai-visualizer" / "ai-visualizer.json.example"); done.append("ai-visualizer.json")
    # Claude Code's own per-folder memory points at the vault: one memory, never two drifting layers
    mem = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT)) / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "MEMORY.md").write_text(f"There is no separate memory layer here. The single source of truth is the vault, at:\n\n    {f['__VAULT__']}\n\n"
                                   "Read it from there at the start of every session: CLAUDE.md (the boot file, in this folder), then VAULT-INDEX.md at the vault root.\n"
                                   "To remember something, write it to its place in the vault, never here.\n")
    done.append("Claude's memory pointer")
    # Claude Code trusts this folder (its hooks and settings apply)
    cj = Path.home() / ".claude.json"
    try:
        d = json.loads(cj.read_text())
    except Exception:
        d = {}
    proj = d.setdefault("projects", {}).setdefault(str(ROOT), {})
    if not proj.get("hasTrustDialogAccepted"):                      # write the shared file only when something changes
        proj["hasTrustDialogAccepted"] = True
        tmp = cj.with_name(".claude.json.troi-tmp"); tmp.write_text(json.dumps(d, indent=2)); os.replace(tmp, cj)
    done.append("trusted by Claude Code")
    return done


def vault_new(path: str | None = None) -> str:
    cfg = load(); target = Path(path).expanduser() if path else P.DATA / "vault"
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} is not empty: use `setup.py vault use {target}` to keep what is there")
    target.mkdir(parents=True, exist_ok=True)
    cfg["vault"] = str(target); save(cfg); f = fields(cfg)
    src = ROOT / "vault-template"
    for p in src.rglob("*"):
        rel = Path(fill(str(p.relative_to(src)), f)); dst = target / rel
        if p.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(fill(p.read_text(), f))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=target)
    subprocess.run(["git", "add", "-A"], cwd=target)
    subprocess.run(["git", "-c", "user.name=" + AGENT, "-c", "user.email=troi@localhost", "commit", "-q", "-m", "vault created"], cwd=target)
    render()
    return str(target)


def vault_use(path: str) -> str:
    t = Path(path).expanduser()
    if not t.is_dir():
        raise SystemExit(f"no folder at {t}")
    cfg = load(); cfg["vault"] = str(t); save(cfg); render()
    return str(t)


def _launchctl(*a):
    return subprocess.run(["launchctl", *a], capture_output=True, text=True)


def services(action: str, name: str | None = None) -> list:
    out = []; cfg = load(); f = fields(cfg); LAUNCH.mkdir(parents=True, exist_ok=True); uid = os.getuid()
    for s in ([name] if name else SERVICES):
        plist = LAUNCH / f"{LABEL}.{s}.plist"
        if action == "install":
            plist.write_text(fill((TPL / f"{LABEL}.{s}.plist").read_text(), f))
            _launchctl("bootout", f"gui/{uid}/{LABEL}.{s}"); r = _launchctl("bootstrap", f"gui/{uid}", str(plist))
            out.append(f"{s}: {'loaded' if r.returncode == 0 else 'not loaded (' + (r.stderr.strip() or 'error') + ')'}")
        elif action == "restart":
            r = _launchctl("kickstart", "-k", f"gui/{uid}/{LABEL}.{s}"); out.append(f"{s}: {'restarted' if r.returncode == 0 else 'not running'}")
        elif action == "status":
            r = _launchctl("print", f"gui/{uid}/{LABEL}.{s}"); m = re.search(r"\bstate = ([\w ]+)", r.stdout)
            out.append(f"{s}: {m.group(1).strip() if r.returncode == 0 and m else 'not loaded'}")
        elif action == "remove":
            _launchctl("bootout", f"gui/{uid}/{LABEL}.{s}")
            if plist.exists(): plist.unlink()
            out.append(f"{s}: removed")
    return out


def shortcut() -> str:
    p = Path.home() / "Desktop" / f"{AGENT}.command"
    p.write_text(f'#!/bin/bash\nexport PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"\nexec "{ROOT}/start.sh"\n')
    p.chmod(0o755)
    return str(p)


def status() -> dict:
    import keychain as KC
    cfg = load(); uid = os.getuid()
    svc = {s: _launchctl("print", f"gui/{uid}/{LABEL}.{s}").returncode == 0 for s in SERVICES}
    vault = Path(cfg["vault"]).expanduser() if cfg.get("vault") else None
    return {"owner": cfg.get("owner"), "welcomed": cfg.get("welcomed"), "vault": str(vault) if vault else "", "vault_ready": bool(vault and (vault / "VAULT-INDEX.md").exists()),
            "rendered": (ROOT / "CLAUDE.md").exists(), "services": svc, "secrets": KC.status(), "shortcut": (Path.home() / "Desktop" / f"{AGENT}.command").exists(),
            "voice_env": (P.BACKTALK / ".venv" / "bin" / "python").exists(), "face_env": (P.CONSOLE / ".venv-face" / "bin" / "python").exists(),
            "console_built": (ROOT / "console" / ".next" / "BUILD_ID").exists(), "data": str(P.DATA)}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["render"]:
        for x in render(): print("  ✓", x)
    elif a[:2] == ["vault", "new"]:
        print("  ✓ vault seeded at", vault_new(a[2] if len(a) > 2 else None))
    elif a[:2] == ["vault", "use"] and len(a) > 2:
        print("  ✓ vault:", vault_use(a[2]))
    elif a[:1] == ["services"] and len(a) > 1:
        for x in services(a[1], a[2] if len(a) > 2 else None): print("  ·", x)
    elif a[:1] == ["shortcut"]:
        print("  ✓ Desktop shortcut:", shortcut())
    elif a[:1] == ["status"]:
        print(json.dumps(status(), indent=2))
    else:
        print(__doc__)
