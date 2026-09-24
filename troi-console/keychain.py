"""The agent's secrets, in the macOS login Keychain only (never a file). One account, one prefix:
account "troi-of-silo-one", services "troi-of-silo-one.<name>". Names: pin, telegram, telegram-chat, elevenlabs,
openai, gemini, agora-appid, agora-cert. Onboarding and Settings write them; the tools read them here.

  keychain.py list               which are set (never the values)
  keychain.py set <name>         prompts for the value (hidden)
"""
import getpass
import subprocess
import sys

ACCOUNT = "troi-of-silo-one"
NAMES = {"pin": "the PIN for protected settings", "telegram": "the Telegram bot token", "telegram-chat": "your Telegram chat id",
         "elevenlabs": "the ElevenLabs API key", "openai": "the OpenAI key (pictures)", "gemini": "the Gemini key (pictures)",
         "agora-appid": "the Agora app id (calls)", "agora-cert": "the Agora certificate (calls)"}


def service(name: str) -> str:
    return f"{ACCOUNT}.{name}"


def get(name: str) -> str:
    try:
        r = subprocess.run(["security", "find-generic-password", "-a", ACCOUNT, "-s", service(name), "-w"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def has(name: str) -> bool:
    try:
        return subprocess.run(["security", "find-generic-password", "-a", ACCOUNT, "-s", service(name)], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


def put(name: str, value: str):
    """Keep one secret (only the names above). -T lets the voice engine read the ElevenLabs key without a prompt."""
    if name not in NAMES or not value or "\n" in value:
        return False, "not a secret the agent keeps"
    extra = ["-T", "/usr/bin/security"]
    r = subprocess.run(["security", "add-generic-password", "-U", "-a", ACCOUNT, "-s", service(name), *extra, "-w", value], capture_output=True, text=True, timeout=10)
    return r.returncode == 0, (r.stderr.strip()[:200] if r.returncode else "")


def status() -> dict:
    return {n: has(n) for n in NAMES}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["list"]:
        for n, d in NAMES.items(): print(f"{'✓' if has(n) else '·'} {n:14} {d}")
    elif a[:1] == ["set"] and len(a) > 1 and a[1] in NAMES:
        ok, err = put(a[1], getpass.getpass(f"{NAMES[a[1]]}: ").strip()); print("kept" if ok else "not kept: " + err)
    else:
        print(__doc__)
