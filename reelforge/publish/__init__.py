"""Official-API publishers. No scraping, no unofficial endpoints, no automation
that impersonates human engagement — uploads only, through each platform's
blessed API. Every adapter supports dry_run for safe testing.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config

ADAPTERS = ("youtube", "tiktok", "instagram", "x", "threads", "bluesky",
            "linkedin", "pinterest", "facebook", "facebook_page")

# What each platform needs before it can post. Used by the Studio dashboard
# to show per-platform readiness at a glance. Values are env var names;
# "file:..." means a file must exist under ~/.reelforge/.
PLATFORM_REQUIREMENTS = {
    "youtube": ("file:youtube_client.json",),
    "tiktok": ("TIKTOK_ACCESS_TOKEN",),
    "instagram": ("IG_ACCESS_TOKEN", "IG_USER_ID"),
    "x": ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"),
    "threads": ("THREADS_USER_ID", "THREADS_ACCESS_TOKEN"),
    "bluesky": ("BSKY_HANDLE", "BSKY_APP_PASSWORD"),
    "linkedin": ("LINKEDIN_ACCESS_TOKEN",),
    "pinterest": ("PINTEREST_ACCESS_TOKEN", "PINTEREST_BOARD_ID"),
    "facebook": ("FB_ACCESS_TOKEN",),
    "facebook_page": ("FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN"),
}

PLATFORM_LABELS = {
    "youtube": "YouTube Shorts", "tiktok": "TikTok", "instagram": "Instagram Reels",
    "x": "X (Twitter)", "threads": "Threads", "bluesky": "Bluesky",
    "linkedin": "LinkedIn", "pinterest": "Pinterest",
    "facebook": "Facebook (Profile)", "facebook_page": "Facebook Page",
}


def platform_status(cfg: Config | None = None) -> list[dict]:
    """Per-platform readiness for the Studio dashboard. Never leaks secrets."""
    from ..config import HOME
    from pathlib import Path as _P
    cfg = cfg or Config()
    out = []
    for p in ADAPTERS:
        missing: list[str] = []
        for req in PLATFORM_REQUIREMENTS[p]:
            if req.startswith("file:"):
                if not (HOME / req[5:]).exists():
                    missing.append(req[5:])
            elif not (cfg.secret(req) or cfg.get(req.lower())):
                missing.append(req)
        # YouTube gets a bonus state: client configured, token = one-click away
        state = "ready" if not missing else "needs_setup"
        hint = ""
        if p == "youtube" and state == "ready":
            if not (_P(HOME) / "youtube_token.json").exists():
                state = "needs_auth"
                hint = "Run any publish once — a browser window will ask you to grant access, then it's saved."
        out.append({"platform": p, "label": PLATFORM_LABELS[p],
                    "state": state, "missing": missing, "hint": hint})
    return out


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
    elif platform == "linkedin":
        from .linkedin import publish as fn
    elif platform == "pinterest":
        from .pinterest import publish as fn
    elif platform == "facebook":
        from .facebook import publish as fn
    elif platform == "facebook_page":
        from .facebook_page import publish as fn
    else:
        raise ValueError(f"Unknown platform {platform!r}. Choose from {ADAPTERS}.")
    return fn(video, title, description, hashtags, cfg, dry_run=dry_run, **kwargs)
