"""TikTok Content Posting API — official video uploads.

Setup (docs/setup-tiktok.md):
  1. developers.tiktok.com → create app → add "Content Posting API" product.
  2. Request the video.upload + video.publish scopes (app review needed for
     production; sandbox works immediately for your own account).
  3. OAuth: authorize → exchange code for access_token.
  4. Set TIKTOK_ACCESS_TOKEN (refresh with TIKTOK_REFRESH_TOKEN when expired).

Flow: FILE_UPLOAD init → PUT chunks → publish with title/privacy.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ..config import Config

API = "https://open.tiktokapis.com/v2"
CHUNK = 8 * 1024 * 1024


def _headers(cfg: Config) -> dict[str, str]:
    token = cfg.require("token", "TIKTOK_ACCESS_TOKEN",
                        "TikTok uploads (Content Posting API OAuth)")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False,
            privacy: str = "PUBLIC") -> dict:
    cfg = cfg or Config()
    caption = f"{title} {' '.join(hashtags)}"[:2200]
    size = video.stat().st_size
    if dry_run:
        return {"platform": "tiktok", "dry_run": True, "caption": caption,
                "bytes": size, "privacy": privacy}

    headers = _headers(cfg)
    # 1. init
    init = httpx.post(f"{API}/post/publish/video/init/", headers=headers, json={
        "post_info": {"title": caption, "privacy_level": privacy},
        "source_info": {"source": "FILE_UPLOAD",
                        "video_size": size, "chunk_size": CHUNK,
                        "total_chunk_count": (size + CHUNK - 1) // CHUNK},
    }, timeout=30)
    init.raise_for_status()
    data = init.json()["data"]

    # 2. upload chunks
    with open(video, "rb") as f:
        for i in range((size + CHUNK - 1) // CHUNK):
            chunk = f.read(CHUNK)
            put = httpx.put(data["upload_url"], content=chunk,
                            headers={"Content-Range":
                                     f"bytes {i * CHUNK}-{i * CHUNK + len(chunk) - 1}/{size}",
                                     "Content-Length": str(len(chunk)),
                                     "Content-Type": "video/mp4"},
                            timeout=120)
            put.raise_for_status()

    # 3. FILE_UPLOAD auto-publishes once chunks are uploaded — poll status.
    pub_id = data["publish_id"]
    done = httpx.post(f"{API}/post/publish/status/fetch/", headers=headers,
                      json={"publish_id": pub_id}, timeout=30)
    done.raise_for_status()
    return {"platform": "tiktok", "publish_id": pub_id,
            "status": done.json()["data"].get("status")}
