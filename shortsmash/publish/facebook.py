"""Facebook personal profile — official Graph API video publishing.

Setup:
  1. Meta app with `pages_manage_posts` / `publish_video` permissions.
  2. User access token with video upload scope.
     Env: FB_ACCESS_TOKEN.

Flow: upload MP4 via resumable upload to /{user-id}/videos, then publish.
Videos: <= 10GB, 240p minimum.

Note: Meta restricts profile publishing for many app types; if your app
is rejected, use the Facebook Page adapter instead.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from ..config import Config

GRAPH = "https://graph.facebook.com/v21.0"


def _call(cfg: Config, method: str, path: str, **kw) -> dict:
    token = cfg.require("fb_access_token", "FB_ACCESS_TOKEN",
                        "Facebook publishing (user access token)")
    params = kw.pop("params", {})
    params["access_token"] = token
    r = httpx.request(method, f"{GRAPH}{path}", params=params, timeout=120, **kw)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Facebook API error: {data['error']}")
    return data


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False,
            video_url: str | None = None) -> dict:
    cfg = cfg or Config()
    caption = f"{title}\n\n{description}\n\n{' '.join(hashtags)}".strip()[:5000]

    if dry_run:
        return {"platform": "facebook", "dry_run": True, "caption": caption}

    # Resumable upload: init session, upload bytes, publish.
    size = video.stat().st_size
    init = _call(cfg, "POST", "/me/videos", data={
        "upload_phase": "start", "file_size": size})
    session_id = init["video_id"]
    upload_url = init["upload_url"]

    token = cfg.require("fb_access_token", "FB_ACCESS_TOKEN",
                        "Facebook publishing (user access token)")
    with open(video, "rb") as f:
        r = httpx.post(upload_url,
                       headers={"Authorization": f"OAuth {token}",
                                "offset": "0", "file_size": str(size)},
                       content=f.read(), timeout=600)
        r.raise_for_status()

    finish = _call(cfg, "POST", "/me/videos", data={
        "upload_phase": "finish", "video_id": session_id,
        "title": title[:255], "description": caption})
    video_id = finish.get("id", session_id)

    for _ in range(36):  # poll up to ~3 min for processing
        st = _call(cfg, "GET", f"/{video_id}", params={"fields": "status"})
        code = (st.get("status") or {}).get("video_status")
        if code == "ready":
            break
        if code == "error":
            raise RuntimeError(f"Facebook rejected the video: {st}")
        time.sleep(5)

    link = _call(cfg, "GET", f"/{video_id}", params={"fields": "permalink_url"})
    return {"platform": "facebook", "media_id": video_id,
            "url": link.get("permalink_url")}
