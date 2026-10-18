"""Kling AI video generation provider (paid, bring-your-own-key).

Kling (kling.ai) is one of the top-tier text-to-video models — strong
motion quality, native 9:16, 5s/10s clips. Paid per generation.

Setup:
  1. Sign up at https://kling.ai and open kling.ai/dev/api-key.
     Click "Create a new API Key" — copy the Access Key AND the Secret
     Key (the secret shows only once).
  2. Export KLING_ACCESS_KEY and KLING_SECRET_KEY, or save them via
     the Secure Vault — never paste them in chat or a file.
  3. config: visual_provider: kling

API shape (api.klingai.com):
  auth: JWT HS256, claims {iss: accessKey, exp: now+1800, nbf: now-5},
        signed with the secret key, sent as `Authorization: Bearer <jwt>`.
  POST /v1/videos/text2video
    {"model_name": "kling-v2-1", "prompt": ..., "duration": "5",
     "aspect_ratio": "9:16", "cfg_scale": 0.5}
  -> {"data": {"task_id": ...}}
  GET /v1/videos/text2video/{task_id}  (poll until task_status=succeed)
  -> {"data": {"task_status": ..., "task_result": {"videos": [{"url": ...}]}}}

Config keys: kling_model (default kling-v2-1),
             kling_duration (5 or 10, default 5).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request
from pathlib import Path

from .config import Config

BASE = "https://api.klingai.com"
DEFAULT_MODEL = "kling-v2-1"
_POLL_EVERY = 10
_TIMEOUT = 900


class KlingError(RuntimeError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _jwt(access_key: str, secret_key: str) -> str:
    """Build Kling's HS256 auth token with the stdlib (no new dependency)."""
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "iss": access_key, "exp": now + 1800, "nbf": now - 5,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def _creds(cfg: Config) -> tuple[str, str]:
    ak = cfg.secret("KLING_ACCESS_KEY") or os.environ.get("KLING_ACCESS_KEY", "")
    sk = cfg.secret("KLING_SECRET_KEY") or os.environ.get("KLING_SECRET_KEY", "")
    if not ak or not sk:
        raise KlingError(
            "visual_provider=kling needs KLING_ACCESS_KEY and "
            "KLING_SECRET_KEY (kling.ai/dev/api-key).")
    return ak, sk


def _call(method: str, path: str, cfg: Config,
          data: dict | None = None) -> dict:
    ak, sk = _creds(cfg)
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {_jwt(ak, sk)}"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise KlingError(f"Kling API {e.code}: {detail}") from e


def _download(url: str, out: Path) -> None:
    with urllib.request.urlopen(url, timeout=300) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def generate(prompt: str, out: Path, cfg: Config,
             duration: float = 4.0, aspect: str = "9:16") -> Path:
    """Generate one AI video clip with Kling. Returns the mp4 path."""
    # Kling renders 5s or 10s clips; snap the scene duration to nearest.
    seconds = "10" if duration >= 7.5 else "5"
    seconds = cfg.get("kling_duration", seconds)
    model = cfg.get("kling_model", DEFAULT_MODEL)
    submit = _call("POST", "/v1/videos/text2video", cfg, {
        "model_name": model,
        "prompt": f"Cinematic vertical video, no on-screen text, no watermark: {prompt}",
        "duration": str(seconds),
        "aspect_ratio": aspect,
        "cfg_scale": 0.5,
    })
    try:
        task_id = submit["data"]["task_id"]
    except (KeyError, TypeError) as e:
        raise KlingError(f"Kling submit returned no task_id: {submit}") from e
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        time.sleep(_POLL_EVERY)
        status = _call("GET", f"/v1/videos/text2video/{task_id}", cfg)
        data = status.get("data") or {}
        state = str(data.get("task_status") or data.get("status") or "").lower()
        if state in ("succeed", "success", "completed", "done"):
            try:
                url = data["task_result"]["videos"][0]["url"]
            except (KeyError, IndexError, TypeError) as e:
                raise KlingError(f"Kling done but no video URL: {status}") from e
            _download(url, out)
            if not out.exists() or out.stat().st_size == 0:
                raise KlingError("Kling download produced an empty file")
            return out
        if state in ("failed", "fail", "error", "cancelled"):
            raise KlingError(f"Kling generation failed: {data}")
    raise KlingError("Kling generation timed out after 15 minutes")
