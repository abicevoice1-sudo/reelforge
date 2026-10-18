"""Bluesky — official video posts via the AT Protocol.

Setup:
  1. bsky.app → Settings → App passwords → create one.
  2. Env: BSKY_HANDLE (you.bsky.social), BSKY_APP_PASSWORD.

Flow: createSession → uploadBlob(video) → post with video embed.
No third-party SDK needed — raw ATProto HTTP.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from ..config import Config

_PROXY = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
PDS = "https://bsky.social"


def _client() -> httpx.Client:
    return httpx.Client(proxy=_PROXY or None, timeout=120)


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False) -> dict:
    cfg = cfg or Config()
    text = f"{title} {' '.join(hashtags)}"[:300]
    if dry_run:
        return {"platform": "bluesky", "dry_run": True, "text": text,
                "bytes": video.stat().st_size}

    handle = cfg.require("bsky_handle", "BSKY_HANDLE", "Bluesky posting")
    password = cfg.require("bsky_password", "BSKY_APP_PASSWORD", "Bluesky posting")

    with _client() as c:
        r = c.post(f"{PDS}/xrpc/com.atproto.server.createSession",
                   json={"identifier": handle, "password": password})
        r.raise_for_status()
        sess = r.json()
        auth = {"Authorization": f"Bearer {sess['accessJwt']}"}

        blob = c.post(f"{PDS}/xrpc/com.atproto.repo.uploadBlob",
                      content=video.read_bytes(),
                      headers={**auth, "Content-Type": "video/mp4"})
        blob.raise_for_status()
        blob_ref = blob.json()["blob"]

        post = {
            "repo": sess["did"], "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc).isoformat(),
                "embed": {"$type": "app.bsky.embed.video",
                          "video": blob_ref},
            },
        }
        r = c.post(f"{PDS}/xrpc/com.atproto.repo.createRecord",
                   json=post, headers=auth)
        r.raise_for_status()
        uri = r.json()["uri"]
    return {"platform": "bluesky", "uri": uri,
            "url": f"https://bsky.app/profile/{handle}/post/{uri.split('/')[-1]}"}
