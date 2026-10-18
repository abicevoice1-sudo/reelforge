#!/usr/bin/env bash
# ReelForge one-click setup. Works on Linux, macOS, and Windows (Git Bash).
#
#   ./install.sh
#
# One command. Walk away. Come back to a working AI video studio.
# Installs: Python venv, all dependencies, CLIP vision model (offline
# footage gate), Piper neural voices (English + Urdu, offline), starter
# music library, default config. Then runs `reelforge doctor`.
#
# After it finishes:
#   Linux/macOS:  source .venv/bin/activate
#   Windows:      source .venv/Scripts/activate
#   reelforge serve   # → open http://127.0.0.1:8000 for the Studio dashboard
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n\033[1;33m\xe2\x9a\x92\xef\xb8\x8f  %s\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m\xe2\x9c\x93 %s\033[0m\n' "$1"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$1"; }
fail() { printf '\033[1;31m\xe2\x9c\x97 %s\033[0m\n' "$1"; exit 1; }

# ---- platform detection ----
OS="unix"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) OS="windows" ;;
esac
if [ "$OS" = "windows" ]; then
  VBIN=".venv/Scripts"
  ACTIVATE="source .venv/Scripts/activate"
else
  VBIN=".venv/bin"
  ACTIVATE="source .venv/bin/activate"
fi

say "Checking prerequisites"
# python3 on unix, python on Windows Git Bash
PYBIN=python3
if ! command -v python3 >/dev/null 2>&1; then
  command -v python >/dev/null 2>&1 && PYBIN=python
fi
command -v "$PYBIN" >/dev/null || fail "Python not found — install Python 3.11–3.13 from https://www.python.org/downloads/ (tick 'Add to PATH')."
PYV=$($PYBIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
$PYBIN -c 'import sys; assert sys.version_info >= (3,10)' \
  || fail "Python 3.10+ required (found $PYV)."
PY_MAJOR=$($PYBIN -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYBIN -c 'import sys; print(sys.version_info.minor)')
# torch (vision extra) has no wheels for Python 3.14+ yet — skip it there.
SKIP_VISION=0
if [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 14 ]; }; then
  SKIP_VISION=1
  warn "Python $PYV detected — torch has no wheels for 3.14+ yet, skipping offline vision gate."
  warn "For the full feature set, use Python 3.11–3.13. Everything else installs normally."
fi
command -v ffmpeg >/dev/null || fail "ffmpeg not found — install it first (Windows: winget install ffmpeg | mac: brew install ffmpeg | apt: sudo apt install ffmpeg)."
ok "python3 $PYV + ffmpeg present"

say "Creating virtual environment"
if [ ! -d .venv ]; then
  $PYBIN -m venv .venv || fail "could not create venv — on Debian/Ubuntu: sudo apt install python3-venv"
fi
[ -x "$VBIN/python" ] || [ -x "$VBIN/python.exe" ] || fail "venv python not found at $VBIN"
ok "venv ready"

say "Installing ReelForge + all features (this is the long step — one time only)"
"$VBIN/python" -m pip -q install --upgrade pip
EXTRAS="ai,voice,web,mcp,trends,bluesky,threads,youtube,x,schedule,captions"
if [ "$SKIP_VISION" -eq 0 ]; then
  EXTRAS="$EXTRAS,vision"
fi
if ! "$VBIN/python" -m pip install -e ".[$EXTRAS]"; then
  warn "Full install failed — retrying without the vision extra (torch)."
  "$VBIN/python" -m pip install -e ".[ai,voice,web,mcp,trends,bluesky,threads,youtube,x,schedule,captions]" \
    || fail "pip install failed. Check the error above."
  SKIP_VISION=1
fi
ok "dependencies installed"

if [ "$SKIP_VISION" -eq 0 ]; then
  say "Downloading CLIP vision model (offline footage gate, ~600MB, one time)"
  "$VBIN/python" -c "from reelforge.vision_local import ensure_model; ensure_model(); print('clip ok')" \
    || warn "vision model download failed — footage gate will use Gemini only."
  ok "vision model ready"
else
  warn "Skipping CLIP vision model (needs torch). Footage checks will use Gemini vision when configured."
fi

say "Downloading Piper neural voices (English + Urdu + Hindi, offline, one time)"
mkdir -p voices
dl_voice() { # $1 = filename, $2 = hf path
  if [ ! -f "voices/$1" ]; then
    if command -v curl >/dev/null; then
      curl -sL -o "voices/$1" "https://huggingface.co/rhasspy/piper-voices/resolve/main/$2" || true
    else
      "$VBIN/python" -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/rhasspy/piper-voices/resolve/main/$2', 'voices/$1')" || true
    fi
  fi
  [ -f "voices/$1" ] || warn "could not download $1 — voice will fall back."
}
dl_voice en_US-amy-medium.onnx               "en/en_US/amy/medium/en_US-amy-medium.onnx"
dl_voice en_US-amy-medium.onnx.json          "en/en_US/amy/medium/en_US-amy-medium.onnx.json"
dl_voice ur_PK-aegis_female-medium.onnx      "ur/ur_PK/aegis_female/medium/ur_PK-aegis_female-medium.onnx"
dl_voice ur_PK-aegis_female-medium.onnx.json "ur/ur_PK/aegis_female/medium/ur_PK-aegis_female-medium.onnx.json"
dl_voice hi_IN-priyamvada-medium.onnx        "hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium.onnx"
dl_voice hi_IN-priyamvada-medium.onnx.json   "hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium.onnx.json"
ok "voices ready (English + Urdu + Hindi)"

say "Installing Urdu caption font (Noto Nastaliq Urdu)"
if [ "$OS" = "windows" ]; then
  FONTDIR="$LOCALAPPDATA/Microsoft/Windows/Fonts"
  mkdir -p "$FONTDIR" 2>/dev/null || true
  cp fonts/NotoNastaliqUrdu.ttf "$FONTDIR/" 2>/dev/null || warn "copy the font manually: fonts/NotoNastaliqUrdu.ttf → Settings > Fonts"
else
  mkdir -p ~/.fonts
  cp fonts/NotoNastaliqUrdu.ttf ~/.fonts/ 2>/dev/null || true
  fc-cache -f ~/.fonts >/dev/null 2>&1 || true
fi
ok "caption font ready"

say "Setting up config + starter music"
"$VBIN/python" -m reelforge.cli init >/dev/null 2>&1 || true
"$VBIN/python" -c "from reelforge.music import ensure_library; ensure_library(); print('music ok')" || true
ok "config + music ready"

say "Running health check"
"$VBIN/python" -m reelforge.cli doctor || true

printf '\n\033[1;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
printf '\033[1;32m🎉 ReelForge is ready.\033[0m\n\n'
printf '  %s\n' "$ACTIVATE"
printf '  reelforge serve   →  open http://127.0.0.1:8000\n\n'
printf 'Make your first video from the Studio dashboard, then hit the\n'
printf '🚀 Publish tab to post it to 8 platforms in one click.\n'
printf '\033[1;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
