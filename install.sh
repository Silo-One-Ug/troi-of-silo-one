#!/bin/bash
# Troi of Silo One: install on this Mac. Run it once after cloning (and again any time: it only adds what is missing).
#   git clone https://github.com/Silo-One-Ug/troi-of-silo-one && cd troi-of-silo-one && ./install.sh
# Then double-click "Troi" on the Desktop: the welcome takes you through the rest (your name, your keys, your vault).
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="$(cd "$(dirname "$0")" && pwd)"; C="$ROOT/troi-console"; source "$C/paths.sh"
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
die()  { printf "  \033[31m✗\033[0m %s\n" "$1"; exit 1; }
echo "TROI OF SILO ONE · install"
[ "$(uname)" = "Darwin" ] || die "macOS only (the globe, the camera, the cursor and the Keychain are Mac pieces)."

echo "1. the tools it stands on"
command -v brew >/dev/null || die "Homebrew is missing: https://brew.sh (paste its one-line installer, then run me again)."
for b in git uv ffmpeg imagesnap cliclick node gh espeak-ng; do command -v "${b%-ng}" >/dev/null 2>&1 || command -v "$b" >/dev/null 2>&1 && ok "$b" || { warn "installing $b"; brew install "$b" >/dev/null 2>&1 && ok "$b" || warn "$b did not install (brew install $b)"; }; done
command -v claude >/dev/null && ok "Claude Code $(claude --version 2>/dev/null | head -1)" || die "Claude Code is missing: https://claude.com/claude-code (install it and sign in, then run me again)."
[ -d "/Applications/Google Chrome.app" ] && ok "Google Chrome" || warn "Google Chrome is not installed: the hands board and the agent's browser need it"

echo "2. the voice line, the globe, face ID"
( cd "$ROOT/backtalk" && uv sync -q --inexact 2>/dev/null ) && ok "voice line environment" || die "the voice line environment did not build (cd backtalk && uv sync)"
uv pip install -q --python "$ROOT/backtalk/.venv/bin/python" resemblyzer agora-python-server-sdk agora-token-builder webrtcvad numpy 2>/dev/null && ok "voice ID, calls, voice activity" || warn "voice ID / calls extras did not install"
[ -x "$C/.venv-ring/bin/python" ] || uv venv -q "$C/.venv-ring" >/dev/null 2>&1
uv pip install -q --python "$C/.venv-ring/bin/python" pyobjc-framework-Cocoa pyobjc-framework-WebKit pyobjc-framework-Quartz pyobjc-framework-ApplicationServices 2>/dev/null && ok "the globe and the cursor guard" || warn "the globe environment did not install"
if [ ! -x "$C/.venv-face/bin/python" ]; then
  uv venv -q --python 3.12 "$C/.venv-face" >/dev/null 2>&1 && uv pip install -q --python "$C/.venv-face/bin/python" facenet-pytorch pillow numpy 2>/dev/null && ok "face ID environment" || warn "face ID did not install (optional)"
else ok "face ID environment"; fi

echo "3. the console and the agent's browser"
( cd "$C" && npm install --no-audit --no-fund --silent >/dev/null 2>&1 ) && ok "browser bridge" || warn "browser bridge (npm install in troi-console) did not install"
( cd "$ROOT/console" && npm install --no-audit --no-fund --silent >/dev/null 2>&1 && npm run build >"$LOGS/console-build.log" 2>&1 ) && ok "the console (built)" || die "the console did not build (see $LOGS/console-build.log)"

echo "4. this Mac"
chmod +x "$ROOT"/*.sh "$C"/*.sh "$C"/*.py 2>/dev/null
/usr/bin/python3 "$C/setup.py" render | sed 's/^/ /'
"$C/patch-board.sh" >/dev/null 2>&1 && ok "board tools in place" || warn "the board tools did not copy"
/usr/bin/python3 "$C/setup.py" services install | sed 's/^/ /'
/usr/bin/python3 "$C/setup.py" shortcut | sed 's/^/ /'
mkdir -p "$HOME/.local/bin"; printf '#!/bin/bash\nexec "%s/start.sh" "$@"\n' "$ROOT" > "$HOME/.local/bin/troi"; chmod +x "$HOME/.local/bin/troi"; ok "terminal command: troi"

echo "5. the larger speech model (1.5 GB, resumable, in the background)"
[ -f "$MODELS/whisper-medium.en-mlx/.done" ] && ok "already here" || { nohup "$C/get-model.sh" >"$LOGS/model.log" 2>&1 & ok "downloading into data/models (log: data/logs/model.log); the small model works meanwhile"; }

cat <<TXT

Done. Double-click "Troi" on the Desktop (or type  troi  in a terminal): the welcome takes it from there.
Once, in System Settings > Privacy & Security, give Terminal: Accessibility, Input Monitoring (the talk key)
and Screen Recording (the welcome checks these), and allow the Camera and Microphone when macOS asks.
Everything the agent keeps lives in $DATA (one SQLite record, one blob folder); secrets live in the Keychain.
TXT
