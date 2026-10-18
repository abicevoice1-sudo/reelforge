"""Free-tier API limit tracking. Knows every API ReelForge uses, its free
limits, and today's usage — so auto-generation never burns quota blind."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

# Free-tier limits. `per_video` = API calls consumed to make one video.
# Sources: provider docs / observed behavior; conservative where uncertain.
APIS = {
    "pixabay": {
        "label": "Pixabay",
        "group": "generation",
        "required": False,
        "daily_limit": 100,  # generous; effectively per-minute throttled
        "per_video": 3,
        "get_key": "https://pixabay.com/api/docs/",
        "why": "Real stock footage. Without it: gradient placeholders.",
    },
    "gemini": {
        "label": "Gemini",
        "group": "generation",
        "required": False,
        "daily_limit": 20,  # free tier
        "per_video": 2,  # script + footage verification
        "get_key": "https://aistudio.google.com/app/apikey",
        "why": "AI scripts + footage quality checks. Without it: template scripts.",
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "group": "generation",
        "required": False,
        "daily_limit": 40,
        "per_video": 2,
        "get_key": "https://build.nvidia.com/settings/api-keys",
        "why": "Backup AI script writer when Gemini quota runs out.",
    },
    "agnes": {
        "label": "Agnes AI",
        "group": "generation",
        "required": False,
        "daily_limit": 50,  # queue-based; conservative
        "per_video": 1,
        "get_key": "https://platform.agnes-ai.com",
        "why": "AI-generated video clips instead of stock.",
    },
    "youtube": {
        "label": "YouTube",
        "group": "publishing",
        "required": False,
        "daily_limit": 6,  # uploads/day per channel (platform cap)
        "per_video": 1,
        "get_key": "docs/setup-youtube.md",
        "why": "Post Shorts via official API (OAuth client JSON).",
    },
    "tiktok": {
        "label": "TikTok",
        "group": "publishing",
        "required": False,
        "daily_limit": 10,
        "per_video": 1,
        "get_key": "docs/setup-tiktok.md",
        "why": "Post via official Content Posting API.",
    },
    "instagram": {
        "label": "Instagram",
        "group": "publishing",
        "required": False,
        "daily_limit": 25,  # Reels/day (platform guidance)
        "per_video": 1,
        "get_key": "docs/setup-instagram.md",
        "why": "Post Reels via Graph API.",
    },
    "x": {
        "label": "X (Twitter)",
        "group": "publishing",
        "required": False,
        "daily_limit": 17,  # ~500/mo free tier ≈ 17/day
        "per_video": 1,
        "get_key": "docs/setup-x.md",
        "why": "Post videos via API v2.",
    },
    "threads": {
        "label": "Threads",
        "group": "publishing",
        "required": False,
        "daily_limit": 20,
        "per_video": 1,
        "get_key": "Meta developer dashboard",
        "why": "Post via Threads API (needs public video URL).",
    },
    "bluesky": {
        "label": "Bluesky",
        "group": "publishing",
        "required": False,
        "daily_limit": 50,
        "per_video": 1,
        "get_key": "bsky.app → Settings → App passwords",
        "why": "Post via official AT Protocol API.",
    },
    "linkedin": {
        "label": "LinkedIn",
        "group": "publishing",
        "required": False,
        "daily_limit": 10,
        "per_video": 1,
        "get_key": "LinkedIn developer portal",
        "why": "Post videos via official API.",
    },
    "pinterest": {
        "label": "Pinterest",
        "group": "publishing",
        "required": False,
        "daily_limit": 20,
        "per_video": 1,
        "get_key": "Pinterest developer portal",
        "why": "Create video pins via official API.",
    },
    "facebook": {
        "label": "Facebook (Profile)",
        "group": "publishing",
        "required": False,
        "daily_limit": 10,
        "per_video": 1,
        "get_key": "Meta developer dashboard → your app → Graph API Explorer",
        "why": "Post videos to your personal timeline via Graph API.",
    },
    "facebook_page": {
        "label": "Facebook Page",
        "group": "publishing",
        "required": False,
        "daily_limit": 25,
        "per_video": 1,
        "get_key": "Meta developer dashboard → your app → Page access token",
        "why": "Post videos to your Page — the reliable Facebook path.",
    },
}


def _db() -> sqlite3.Connection:
    p = Path.home() / ".reelforge" / "usage.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE IF NOT EXISTS usage (api TEXT, day TEXT, calls INT, PRIMARY KEY (api, day))")
    return con


def record(api: str, calls: int = 1) -> None:
    con = _db()
    today = date.today().isoformat()
    con.execute(
        "INSERT INTO usage (api, day, calls) VALUES (?,?,?) "
        "ON CONFLICT (api, day) DO UPDATE SET calls = calls + ?",
        (api, today, calls, calls),
    )
    con.commit()
    con.close()


def today_usage() -> dict[str, int]:
    con = _db()
    rows = con.execute(
        "SELECT api, calls FROM usage WHERE day = ?", (date.today().isoformat(),)
    ).fetchall()
    con.close()
    return {api: calls for api, calls in rows}


def status() -> list[dict]:
    """Per-API limit status for the dashboard."""
    used = today_usage()
    out = []
    for key, info in APIS.items():
        limit = info["daily_limit"]
        u = used.get(key, 0)
        out.append({
            "key": key, "label": info["label"], "group": info["group"],
            "required": info["required"], "used": u, "limit": limit,
            "remaining": max(0, limit - u),
            "pct": min(100, int(100 * u / limit)) if limit else 0,
            "why": info["why"], "get_key": info["get_key"],
        })
    return out


def videos_possible_today() -> int:
    """How many full videos can still be generated with today's quota."""
    used = today_usage()
    caps = []
    for key, info in APIS.items():
        if info["group"] != "generation":
            continue
        limit = info["daily_limit"]
        per = info["per_video"]
        remaining_calls = max(0, limit - used.get(key, 0))
        caps.append(remaining_calls // per)
    # Generation needs footage OR ai visuals; script needs gemini OR nvidia.
    # Conservative: the tightest single API caps output.
    return min(caps) if caps else 0
