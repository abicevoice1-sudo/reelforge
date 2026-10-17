"""LinkedIn — official video posts.

Setup:
  1. developer.linkedin.com → app → Products: "Share on LinkedIn".
  2. OAuth 2.0 with w_member_social scope → access token.
  3. Env: LINKEDIN_ACCESS_TOKEN.

Flow: register upload → PUT binary → create ugcPost.
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
    text = f"{title}\n\n{description} {' '.join(hashtags)}"[:3000].strip()
    if dry_run:
        return {"platform": "linkedin", "dry_run": True,
                "bytes": video.stat().st_size}

    token = cfg.require("linkedin_token", "LINKEDIN_ACCESS_TOKEN",
                        "LinkedIn posting")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(proxy=_PROXY or None, timeout=120) as c:
        me = c.get("https://api.linkedin.com/v2/userinfo",
                   headers=headers).json()["sub"]
        # 1. register the upload
        reg = c.post("https://api.linkedin.com/v2/videos?action=initializeUpload",
                     headers={**headers, "Content-Type": "application/json"},
                     json={"initializeUploadRequest": {
                         "owner": f"urn:li:person:{me}",
                         "fileSizeBytes": video.stat().st_size,
                         "uploadCaptions": False,
                         "uploadThumbnail": False}}).json()
        upload_url = reg["value"]["uploadInstructions"][0]["uploadUrl"]
        video_urn = reg["value"]["video"]
        # 2. upload the binary
        c.put(upload_url, content=video.read_bytes(),
              headers={"Content-Type": "video/mp4"}).raise_for_status()
        # 3. create the post (LinkedIn processes async; check status if needed)
        post = c.post("https://api.linkedin.com/v2/ugcPosts",
                      headers={**headers, "Content-Type": "application/json"},
                      json={"author": f"urn:li:person:{me}",
                            "lifecycleState": "PUBLISHED",
                            "specificContent": {
                                "com.linkedin.ugc.ShareContent": {
                                    "shareCommentary": {"text": text},
                                    "shareMediaCategory": "VIDEO",
                                    "media": [{"status": "READY",
                                               "media": video_urn}]}},
                            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility":
                                           "PUBLIC"}})
        post.raise_for_status()
    return {"platform": "linkedin", "post_id": post.json().get("id")}
