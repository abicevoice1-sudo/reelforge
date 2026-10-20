"""Analytics: pull real performance stats back from platforms.

Reads each project's publishes.json receipts, then queries official APIs:
  - YouTube: videos.list → viewCount, likeCount, commentCount

This is the honest kind of analytics — numbers from the platform, not
vanity metrics invented locally.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import PROJECTS_DIR, Config


@dataclass
class VideoStats:
    slug: str
    platform: str
    url: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    title: str = ""


def _youtube_id(url: str) -> str | None:
    # https://www.youtube.com/shorts/{id} or https://youtu.be/{id}
    for marker in ("/shorts/", "youtu.be/", "v="):
        if marker in url:
            return url.split(marker)[-1].split("?")[0].split("&")[0]
    return None


def youtube_stats(video_ids: list[str], cfg: Config) -> dict[str, dict]:
    """Map video ID → {views, likes, comments, title} via YouTube Data API."""
    from creator_publish.publish.youtube import _service
    svc = _service(cfg)
    out: dict[str, dict] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = svc.videos().list(part="statistics,snippet",
                                 id=",".join(batch)).execute()
        for item in resp.get("items", []):
            st = item.get("statistics", {})
            out[item["id"]] = {
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "title": item.get("snippet", {}).get("title", ""),
            }
    return out


def collect(cfg: Config | None = None) -> list[VideoStats]:
    """Gather stats for every published video across all projects."""
    cfg = cfg or Config()
    results: list[VideoStats] = []
    yt_ids: dict[str, VideoStats] = {}
    for proj in Path(PROJECTS_DIR).iterdir():
        receipts = proj / "publishes.json"
        if not receipts.exists():
            continue
        try:
            data = json.loads(receipts.read_text())
        except Exception:
            continue
        for platform, r in data.items():
            if not isinstance(r, dict) or r.get("dry_run"):
                continue
            url = r.get("url", "")
            if platform == "youtube" and url:
                vid = _youtube_id(url)
                if vid:
                    vs = VideoStats(slug=proj.name, platform=platform, url=url)
                    yt_ids[vid] = vs
                    results.append(vs)
            elif url:
                results.append(VideoStats(slug=proj.name, platform=platform,
                                          url=url))
    if yt_ids:
        try:
            stats = youtube_stats(list(yt_ids), cfg)
            for vid, data in stats.items():
                vs = yt_ids[vid]
                vs.views, vs.likes = data["views"], data["likes"]
                vs.comments, vs.title = data["comments"], data["title"]
        except Exception as e:  # noqa: BLE001
            print(f"analytics: YouTube stats unavailable ({e})")
    return results
