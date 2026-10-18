"""Trend harvesting: find what the world is talking about, free, no API keys.

Sources (all keyless and verified working):
  - Google News RSS — fresh articles per niche query
  - Hacker News official API — tech/AI front-page stories

Each trend gets a score from source authority and recency, so
`shortsmash batch` can turn today's conversations into today's videos.

Note: Reddit's public JSON API now requires OAuth (403 without it) and
Google Trends' trending endpoint is deprecated — both are deliberately
not used here.
"""
from __future__ import annotations

import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

# Niche -> Google News search queries. Broad enough to return volume,
# specific enough to stay on-topic.
NICHE_QUERIES: dict[str, list[str]] = {
    "food": ["indian food", "street food", "viral recipe"],
    "fitness": ["fitness", "workout routine", "weight loss"],
    "tech": ["technology", "gadgets"],
    "ai": ["artificial intelligence", "AI"],
    "finance": ["personal finance", "investing", "stock market"],
    "travel": ["travel destinations", "budget travel"],
    "motivation": ["self improvement", "success habits"],
    "health": ["health tips", "nutrition"],
    "general": ["viral", "trending"],
}

_PROXY = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")


@dataclass
class Trend:
    title: str
    source: str
    url: str = ""
    score: float = 0.0
    published: str = ""
    extra: dict = field(default_factory=dict)


def _client() -> httpx.Client:
    return httpx.Client(
        proxy=_PROXY or None,
        timeout=20,
        headers={"User-Agent": "ShortSmash/1.0 (trend research)"},
    )


def _gnews_trends(queries: list[str]) -> list[Trend]:
    trends: list[Trend] = []
    now = datetime.now(timezone.utc)
    with _client() as c:
        for q in queries:
            try:
                url = ("https://news.google.com/rss/search?q="
                       + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en")
                r = c.get(url)
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.text)
                for item in root.findall(".//item")[:12]:
                    title = (item.findtext("title") or "").strip()
                    # Google News titles append " - Source"; strip it.
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0].strip()
                    if len(title) < 25:
                        continue
                    pub = item.findtext("pubDate") or ""
                    try:
                        dt = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z"
                                               ).replace(tzinfo=timezone.utc)
                        age_h = max((now - dt).total_seconds() / 3600, 1)
                    except Exception:
                        age_h = 12
                    # Fresher = hotter. News decays fast.
                    score = 100 / (age_h ** 0.8)
                    trends.append(Trend(
                        title=title,
                        source="Google News",
                        url=item.findtext("link") or "",
                        score=round(score, 1),
                        published=pub,
                    ))
            except Exception:
                continue
    return trends


def _hn_trends() -> list[Trend]:
    trends: list[Trend] = []
    try:
        with _client() as c:
            ids = c.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:25]
            for i in ids:
                try:
                    d = c.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json").json()
                    if not d or d.get("type") != "story" or not d.get("title"):
                        continue
                    age_h = max((time.time() - d.get("time", time.time())) / 3600, 1)
                    pts = d.get("score", 0) + d.get("descendants", 0) * 2
                    score = pts / (age_h ** 0.9)
                    trends.append(Trend(
                        title=d["title"],
                        source="Hacker News",
                        url=d.get("url", f"https://news.ycombinator.com/item?id={i}"),
                        score=round(float(score), 1),
                    ))
                except Exception:
                    continue
    except Exception:
        pass
    return trends


def harvest(niche: str = "general", limit: int = 10) -> list[Trend]:
    """Return the top `limit` trending topics for a niche, ranked by score."""
    niche = niche.lower()
    queries = NICHE_QUERIES.get(niche, NICHE_QUERIES["general"])
    trends = _gnews_trends(queries)
    if niche in ("tech", "ai"):
        trends.extend(_hn_trends())
    # Dedupe near-identical titles, keep highest score.
    seen: dict[str, Trend] = {}
    for t in sorted(trends, key=lambda t: -t.score):
        key = t.title.lower()[:60]
        if key not in seen:
            seen[key] = t
    return list(seen.values())[:limit]


def to_video_prompt(trend: Trend, niche: str) -> str:
    """Turn a trend into a video topic prompt."""
    return f"{trend.title} ({niche} trend)"
