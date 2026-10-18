#!/usr/bin/env bash
# ReelForge one-click setup.
#
#   ./install.sh
#
# One command. Walk away. Come back to a working AI video studio.
# Installs: Python venv, all dependencies, CLIP vision model (offline
# footage gate), Piper neural voices (English + Urdu, offline), starter
# music library, default config. Then runs `reelforge doctor`.
#
# After it finishes:
#   source .venv/bin/activate
#   reelforge serve   # → open http://127.0.0.1:8000 for the Studio dashboard
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n\033[1;33m⚒️  %s\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$1"; }
fail() { printf '\033[1;31m✗ %s\033[0m\n' "$1"; exit 1; }

say "Checking prerequisites"
command -v python3 >/dev/null || fail "python3 not found — install Python 3.10+ first."
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python3 -c 'import sys; assert sys.version_info >= (3,10)' \
  || fail "Python 3.10+ required (found $PYV)."
command -v ffmpeg >/dev/null || fail "ffmpeg not found — install it first (apt: sudo apt install ffmpeg | mac: brew install ffmpeg)."
ok "python3 $PYV + ffmpeg present"

say "Creating virtual environment"
[ -d .venv ] || python3 -m venv .venv
ok "venv ready"

say "Installing ReelForge + all features (this is the long step — one time only)"
.venv/bin/pip -q install --upgrade pip
.venv/bin/pip -q install -e ".[ai,voice,vision,web,mcp,trends,bluesky,threads,youtube,x,schedule,captions]"
ok "dependencies installed"

say "Downloading CLIP vision model (offline footage gate, ~600MB, one time)"
.venv/bin/python -c "from reelforge.vision_local import ensure_model; ensure_model(); print('clip ok')"
ok "vision model ready"

say "Downloading Piper neural voices (English + Urdu, offline, one time)"
mkdir -p voices
dl_voice() { # $1 = filename
  [ -f "voices/$1" ] || curl -sL -o "voices/$1" "https://huggingface.co/rhasspy/piper-voices/resolve/main/$2"
  [ -f "voices/$1" ] || fail "could not download $1"
}
dl_voice en_US-amy-medium.onnx        "en/en_US/amy/medium/en_US-amy-medium.onnx"
dl_voice en_US-amy-medium.onnx.json   "en/en_US/amy/medium/en_US-amy-medium.onnx.json"
dl_voice ur_PK-aegis_female-medium.onnx      "ur/ur_PK/aegis_female/medium/ur_PK-aegis_female-medium.onnx"
dl_voice ur_PK-aegis_female-medium.onnx.json "ur/ur_PK/aegis_female/medium/ur_PK-aegis_female-medium.onnx.json"
ok "voices ready (English + Urdu)"

say "Setting up config + starter music"
.venv/bin/python -m reelforge.cli init >/dev/null 2>&1 || true
.venv/bin/python -c "from reelforge.music import ensure_library; ensure_library(); print('music ok')"
ok "config + music ready"

say "Running health check"
.venv/bin/python -m reelforge.cli doctor || true

printf '\n\033[1;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
printf '\033[1;32m🎉 ReelForge is ready.\033[0m\n\n'
printf '  source .venv/bin/activate\n'
printf '  reelforge serve   →  open http://127.0.0.1:8000\n\n'
printf 'Make your first video from the Studio dashboard, then hit the\n'
printf '🚀 Publish tab to post it to 8 platforms in one click.\n'
printf '\033[1;32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
