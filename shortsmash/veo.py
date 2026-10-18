"""Google Veo 3.1 video generation provider (paid, bring-your-own-key).

Veo is Google's state-of-the-art text-to-video model — the same engine
behind Google Flow (Flow itself has no public API; this *is* the API
path to the same models). Native audio, 4/6/8-second clips, 9:16.

Setup:
  1. Create a Gemini API key at https://aistudio.google.com/app/apikey
     in a Google Cloud project WITH billing enabled (Veo is paid-only,
     no free tier — a project without billing returns auth-looking
     errors). Pricing is per-second of generated video.
  2. Export GEMINI_API_KEY, or save it via the Secure Vault
     (provider "gemini") — never paste it in chat or a file.
  3. config: visual_provider: veo

API shape (Gemini API v1beta):
  POST /v1beta/models/{model}:predictLongRunning
    {"instances": [{"prompt": ...}],
     "parameters": {"aspectRatio": "9:16", "sampleCount": 1}}
  -> {"name": "operations/..."} ; poll GET /v1beta/{operation}
  until done=true ->
  {"response": {"generateVideoResponse":
    {"generatedSamples": [{"video": {"uri": ...}}]}}}

Models: veo-3.1-generate-preview (best quality, 4K),
        veo-3.1-fast-generate-preview (faster/cheaper),
        veo-3.1-lite-generate-preview (1080p, cheapest).
Config key: veo_model (default veo-3.1-fast-generate-preview).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

try:
    # Muse VM: inject the Secure Vault credential as a surrogate header.
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import add_surrogate_to_request
except ImportError:
    # CI / user machines: fall back to the GEMINI_API_KEY env var.
    add_surrogate_to_request = None  # type: ignore[assignment]

from .config import Config

BASE = "https://generativelanguage.googleapis.com/v1beta"
HOSTS = ["generativelanguage.googleapis.com"]
DEFAULT_MODEL = "veo-3.1-fast-generate-preview"
_POLL_EVERY = 10
_TIMEOUT = 900


class VeoError(RuntimeError):
    pass


def _key(cfg: Config) -> str:
    return cfg.secret("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")


def _request(url: str, data: dict | None, cfg: Config) -> urllib.request.Request:
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    if add_surrogate_to_request is not None:
        add_surrogate_to_request(req, "custom.gemini", allowed_hosts=HOSTS)
    else:
        key = _key(cfg)
        if not key:
            raise VeoError(
                "visual_provider=veo needs GEMINI_API_KEY "
                "(aistudio.google.com, billing-enabled project).")
        req.add_header("x-goog-api-key", key)
    return req


def _call(url: str, cfg: Config, data: dict | None = None) -> dict:
    try:
        with urllib.request.urlopen(_request(url, data, cfg), timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise VeoError(f"Veo API {e.code}: {detail}") from e


def _download(url: str, out: Path, cfg: Config) -> None:
    # The sample URI needs the same credential to download.
    if add_surrogate_to_request is None:
        key = _key(cfg)  # submit already raised if this is empty
        url += ("&" if "?" in url else "?") + f"key={key}"
        req = urllib.request.Request(url)
    else:
        req = _request(url, None, cfg)  # attaches the surrogate header
    with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def generate(prompt: str, out: Path, cfg: Config,
             duration: float = 4.0, aspect: str = "9:16") -> Path:
    """Generate one AI video clip with Veo 3.1. Returns the mp4 path."""
    model = cfg.get("veo_model", DEFAULT_MODEL)
    # Veo renders 4/6/8s clips and picks the length itself; the scene's
    # duration is honored downstream when the clip is cut to the timeline.
    op = _call(f"{BASE}/models/{model}:predictLongRunning", cfg, {
        "instances": [{"prompt": (
            f"Cinematic vertical video, no on-screen text, no watermark: {prompt}"
        )}],
        "parameters": {"aspectRatio": aspect, "sampleCount": 1},
    })
    name = op.get("name", "")
    if not name:
        raise VeoError(f"Veo submit returned no operation: {op}")
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        time.sleep(_POLL_EVERY)
        status = _call(f"{BASE}/{name}", cfg)
        if status.get("done"):
            try:
                uri = (status["response"]["generateVideoResponse"]
                       ["generatedSamples"][0]["video"]["uri"])
            except (KeyError, IndexError, TypeError) as e:
                raise VeoError(f"Veo done but no video URI: {status}") from e
            _download(uri, out, cfg)
            if not out.exists() or out.stat().st_size == 0:
                raise VeoError("Veo download produced an empty file")
            return out
        if status.get("error"):
            raise VeoError(f"Veo generation failed: {status['error']}")
    raise VeoError("Veo generation timed out after 15 minutes")
