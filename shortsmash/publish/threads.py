"""Threads API — official video posts via graph.threads.net.

Setup:
  1. Create a Meta app with the Threads use case, add a Tester, authorize.
  2. Exchange for a long-lived token.
  3. Env: THREADS_USER_ID, THREADS_ACCESS_TOKEN.

Flow: create a video container, then publish it.
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
    text = f"{title} {' '.join(hashtags)}"[:500]
    if dry_run:
        return {"platform": "threads", "dry_run": True, "text": text,
                "bytes": video.stat().st_size}

    user_id = cfg.require("threads_uid", "THREADS_USER_ID", "Threads posting")
    token = cfg.require("threads_token", "THREADS_ACCESS_TOKEN", "Threads posting")
    # NOTE: Threads ingests from a public URL. Upload the file somewhere
    # public first (S3, R2, your CDN) and pass video_url.
    video_url = cfg.get("public_video_url", "")
    if not video_url:
        raise RuntimeError(
            "Threads needs a public video URL: set public_video_url in config "
            "(upload the mp4 to S3/R2/your CDN first).")

    with httpx.Client(proxy=_PROXY or None, timeout=60) as c:
        r = c.post(f"https://graph.threads.net/v1.0/{user_id}/threads",
                   data={"media_type": "VIDEO", "video_url": video_url,
                         "text": text, "access_token": token})
        r.raise_for_status()
        container = r.json()["id"]
        r = c.post(f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
                   data={"creation_id": container, "access_token": token})
        r.raise_for_status()
    return {"platform": "threads", "container_id": container}
