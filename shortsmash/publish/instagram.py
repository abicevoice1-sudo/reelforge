"""Instagram Graph API — official Reels publishing.

Setup (docs/setup-instagram.md):
  1. Instagram professional (Business/Creator) account linked to a Facebook Page.
  2. Meta app with instagram_basic + instagram_content_publish permissions.
  3. Long-lived Page access token → IG_USER_ID.
     Env: IG_ACCESS_TOKEN, IG_USER_ID.

Flow: the MP4 must live at a PUBLIC https URL (Meta fetches it server-side).
Pass video_url=..., or set SHORTSMASH_PUBLIC_URL and ShortSmash appends the
project path. Then: create REELS container → poll until FINISHED → publish.

Reels: 3s–15min, 9:16 recommended, <= 1GB.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from ..config import Config

GRAPH = "https://graph.facebook.com/v21.0"


def _call(cfg: Config, method: str, path: str, **kw) -> dict:
    token = cfg.require("token", "IG_ACCESS_TOKEN", "Instagram Graph API publishing")
    params = kw.pop("params", {})
    params["access_token"] = token
    r = httpx.request(method, f"{GRAPH}{path}", params=params, timeout=60, **kw)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Instagram API error: {data['error']}")
    return data


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False,
            video_url: str | None = None,
            share_to_feed: bool = True) -> dict:
    cfg = cfg or Config()
    ig_id = cfg.require("ig_user", "IG_USER_ID", "Instagram publishing (IG user id)")
    video_url = video_url or cfg.get("public_video_url")
    caption = f"{title}\n\n{description}\n\n{' '.join(hashtags)}".strip()[:2200]

    if dry_run:
        return {"platform": "instagram", "dry_run": True, "caption": caption,
                "video_url": video_url or "<set public_video_url or --video-url>"}
    if not video_url:
        raise RuntimeError(
            "Instagram needs the MP4 at a public https URL (Meta downloads it). "
            "Upload final.mp4 somewhere public (e.g. Cloudflare R2, your site) and "
            "pass --video-url, or set public_video_url in config. "
            "See docs/setup-instagram.md.")

    container = _call(cfg, "POST", f"/{ig_id}/media", data={
        "media_type": "REELS", "video_url": video_url, "caption": caption,
        "share_to_feed": str(share_to_feed).lower()})
    container_id = container["id"]

    for _ in range(60):  # poll up to ~5 min for processing
        status = _call(cfg, "GET", f"/{container_id}",
                       params={"fields": "status_code"})
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram rejected the video: {status}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram video processing timed out (>5 min).")

    pub = _call(cfg, "POST", f"/{ig_id}/media_publish",
                data={"creation_id": container_id})
    media_id = pub["id"]
    link = _call(cfg, "GET", f"/{media_id}", params={"fields": "permalink"})
    return {"platform": "instagram", "media_id": media_id,
            "url": link.get("permalink")}
