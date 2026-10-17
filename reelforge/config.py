"""Configuration: layered YAML file + environment variables.

Precedence: explicit arg > env var > ~/.reelforge/config.yaml > defaults.
`reelforge init` writes the YAML; API keys live in the environment (or .env).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

HOME = Path.home() / ".reelforge"
CONFIG_FILE = HOME / "config.yaml"
PROJECTS_DIR = HOME / "projects"
QUEUE_DB = HOME / "queue.db"

DEFAULTS: dict[str, Any] = {
    "timezone": "America/New_York",
    "language": "en",
    # script (llm_provider: auto | nvidia | gemini | template)
    "llm_provider": "auto",
    "nvidia_model": "auto",  # or pin a catalog id; "auto" picks best live model
    "gemini_model": "gemini-3.8-flash",
    # voice
    "voice": "en-US-AriaNeural",  # Edge-TTS voice id
    "voice_rate": "+0%",
    # Offline neural fallback when Edge-TTS is unreachable (used before gTTS).
    # Download: https://huggingface.co/rhasspy/piper-voices (e.g.
    # en/en_US/amy/medium/en_US-amy-medium.onnx)
    "piper_voice": "",
    # look
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "caption_style": "karaoke",  # karaoke | minimal | bold
    "caption_fontsize": 64,
    # music
    "music_volume": 0.12,  # bed level under voiceover
    "music_duck": True,
    # stock (pexels paused new key issuance 2026-09-30; pixabay is the default)
    "stock_provider": "pixabay",  # pixabay | pexels | generate
    "stock_per_scene": 1,
    "stock_verify": True,  # vision-check each clip against its query
    # safety
    "max_duration": 180,
}


def ensure_home() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return HOME


def load_yaml() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return {}


class Config:
    def __init__(self, overrides: dict[str, Any] | None = None):
        file_cfg = load_yaml()
        self._data: dict[str, Any] = {**DEFAULTS, **file_cfg, **(overrides or {})}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    # ---- secrets (env only, never written to disk by us) ----
    @staticmethod
    def secret(name: str) -> str | None:
        return os.environ.get(name) or None

    def gemini_key(self) -> str | None:
        return self.secret("GEMINI_API_KEY") or self.secret("GOOGLE_API_KEY")

    def pexels_key(self) -> str | None:
        return self.secret("PEXELS_API_KEY")

    def pixabay_key(self) -> str | None:
        return self.secret("PIXABAY_API_KEY")

    def require(self, key: str, env_name: str, what_for: str) -> str:
        val = self.secret(env_name) or self.get(key)
        if not val:
            raise RuntimeError(
                f"Missing {env_name}: needed {what_for}. "
                f"Set it in your environment or .env (see .env.example)."
            )
        return val
