"""Agnes AI video generation provider (free tier).

Agnes AI (Singapore) offers genuinely free text-to-video via an
OpenAI-compatible API — no credit card, no GPU needed. This wires it into
ReelForge as a visual provider: each scene's cinematic shot list becomes
an AI-generated clip instead of stock footage.

Setup:
  1. Sign up free at https://platform.agnes-ai.com and create an API key.
  2. Save it via the Secure Vault (credentials.request_api_access,
     provider "agnes") — never paste it in chat or a file.
  3. config: visual_provider: agnes

API shape (verified against Agnes docs 2026):
  POST https://apihub.agnes-ai.com/v1/videos
    {model, mode: "text", prompt, size, aspect_ratio, seconds, n}
  -> {video_id, ...}
  GET https://apihub.agnes-ai.com/agnesapi?video_id=..&model_name=..
  -> {status: completed|failed|..., metadata: {url: mp4}}

Rate limit on free tier: ~16 req/min. Generations are async; we poll.
The API key lives in the Secure Vault as custom.agnes and is injected
as a surrogate — it never appears in code, logs, or files.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request  # noqa: E402

from .config import Config

BASE = "https://apihub.agnes-ai.com"
HOSTS = ["apihub.agnes-ai.com"]
MODEL = "agnes-video-2.5-flash"
_POLL_EVERY = 3
_TIMEOUT = 600


class AgnesError(RuntimeError):
    pass


def _authed(url: str, data: dict | None = None) -> urllib.request.Request:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    add_surrogate_to_request(req, "custom.agnes", allowed_hosts=HOSTS)
    return req


def _call(url: str, data: dict | None = None) -> dict:
    try:
        with urllib.request.urlopen(_authed(url, data), timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise AgnesError(f"Agnes API {e.code}: {detail}") from e


def generate(prompt: str, out: Path, cfg: Config,
             duration: float = 4.0, aspect: str = "9:16") -> Path:
    """Generate one AI video clip for a scene prompt. Returns the mp4 path."""
    seconds = str(min(12, max(4, int(round(duration)))))
    create = _call(f"{BASE}/v1/videos", {
        "model": cfg.get("agnes_model", MODEL),
        "mode": "text",
        # Cinematic framing helps the model; keep the scene's own words first.
        "prompt": f"Cinematic vertical video, no on-screen text, no watermark: {prompt}",
        "size": cfg.get("agnes_size", "720P"),
        "aspect_ratio": aspect,
        "seconds": seconds,
        "n": 1,
    })
    video_id = create.get("video_id") or create.get("id") or create.get("task_id")
    if not video_id:
        raise AgnesError(f"No video_id in Agnes response: {str(create)[:200]}")
    model = cfg.get("agnes_model", MODEL)
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        time.sleep(_POLL_EVERY)
        st = _call(f"{BASE}/agnesapi?video_id={video_id}&model_name={model}")
        status = str(st.get("status", "")).lower()
        if status == "completed":
            url = ((st.get("metadata") or {}).get("url")
                   or st.get("url") or st.get("video_url"))
            if not url:
                raise AgnesError(f"Completed but no URL: {str(st)[:200]}")
            _download(url, out)
            return out
        if status in ("failed", "error"):
            raise AgnesError(f"Agnes generation failed: {str(st)[:200]}")
    raise AgnesError(f"Agnes generation timed out after {_TIMEOUT}s")


def _download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ReelForge/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    if out.stat().st_size == 0:
        raise AgnesError("Downloaded empty video file")
