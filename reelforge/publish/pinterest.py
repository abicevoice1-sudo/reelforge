"""Pinterest — official video Pins.

Setup:
  1. developers.pinterest.com → app → OAuth with boards:write, pins:write.
  2. Env: PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID.

Flow: POST /v5/pins with the video file (multipart).
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from ..config import Config

_PROXY = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False) -> dict:
    cfg = cfg or Config()
    desc = f"{description} {' '.join(hashtags)}"[:800].strip()
    if dry_run:
        return {"platform": "pinterest", "dry_run": True, "title": title,
                "bytes": video.stat().st_size}

    token = cfg.require("pinterest_token", "PINTEREST_ACCESS_TOKEN",
                        "Pinterest posting")
    board = cfg.require("pinterest_board", "PINTEREST_BOARD_ID",
                        "Pinterest posting")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(proxy=_PROXY or None, timeout=180) as c:
        with open(video, "rb") as f:
            r = c.post("https://api.pinterest.com/v5/pins",
                       headers=headers,
                       data={"board_id": board, "title": title[:100],
                             "description": desc},
                       files={"video": (video.name, f, "video/mp4")})
        r.raise_for_status()
        pin = r.json()
    return {"platform": "pinterest", "pin_id": pin.get("id")}
