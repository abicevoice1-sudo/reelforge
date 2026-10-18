"""X API v2 — official video posts.

Setup (docs/setup-x.md):
  1. developer.x.com → project + app → enable OAuth 1.0a (Read+Write).
  2. Env: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.

Video: <= 512MB, <= 140s on free/basic tiers. Chunked upload via v1.1 media
endpoint, then posted with v2 create_tweet.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config


def publish(video: Path, title: str, description: str, hashtags: list[str],
            cfg: Config | None = None, dry_run: bool = False) -> dict:
    cfg = cfg or Config()
    text = f"{title} {' '.join(hashtags)}"[:280]
    if dry_run:
        return {"platform": "x", "dry_run": True, "text": text,
                "bytes": video.stat().st_size}

    try:
        import tweepy
    except ImportError as exc:
        raise RuntimeError("pip install 'shortsmash[x]' first.") from exc

    auth = tweepy.OAuth1UserHandler(
        cfg.require("k", "X_API_KEY", "X posting"),
        cfg.require("s", "X_API_SECRET", "X posting"),
        cfg.require("t", "X_ACCESS_TOKEN", "X posting"),
        cfg.require("ts", "X_ACCESS_SECRET", "X posting"))
    api = tweepy.API(auth)  # v1.1 for chunked media upload
    client = tweepy.Client(
        consumer_key=cfg.secret("X_API_KEY"), consumer_secret=cfg.secret("X_API_SECRET"),
        access_token=cfg.secret("X_ACCESS_TOKEN"),
        access_token_secret=cfg.secret("X_ACCESS_SECRET"))

    media = api.media_upload(str(video), chunked=True,
                             media_category="tweet_video")
    api.create_media_metadata(media.media_id, alt_text=title[:1000])
    tweet = client.create_tweet(text=text, media_ids=[media.media_id])
    tid = tweet.data["id"]
    me = client.get_me().data.username
    return {"platform": "x", "tweet_id": tid,
            "url": f"https://x.com/{me}/status/{tid}"}
