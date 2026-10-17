"""Official-API publishers. No scraping, no unofficial endpoints, no automation
that impersonates human engagement — uploads only, through each platform's
blessed API. Every adapter supports dry_run for safe testing.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config

ADAPTERS = ("youtube", "tiktok", "instagram", "x", "threads", "bluesky")


def publish(platform: str, video: Path, title: str, description: str,
            hashtags: list[str], cfg: Config | None = None,
            dry_run: bool = False, **kwargs) -> dict:
    cfg = cfg or Config()
    if platform == "youtube":
        from .youtube import publish as fn
    elif platform == "tiktok":
        from .tiktok import publish as fn
    elif platform == "instagram":
        from .instagram import publish as fn
    elif platform == "x":
        from .x import publish as fn
    elif platform == "threads":
        from .threads import publish as fn
    elif platform == "bluesky":
        from .bluesky import publish as fn
    else:
        raise ValueError(f"Unknown platform {platform!r}. Choose from {ADAPTERS}.")
    return fn(video, title, description, hashtags, cfg, dry_run=dry_run, **kwargs)
