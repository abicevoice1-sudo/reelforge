"""Engagement assistant: drafts replies to real comments. You approve each one.

Hard rules (non-negotiable, by design):
- NOTHING posts without your explicit per-reply approval. No auto-replies.
- No likes, follows, or shares automation of any kind — that's fake engagement,
  it violates every platform's ToS, and it gets accounts banned.
- Drafts are clearly labeled AI-suggested; you can edit before approving.

Flow: `shortsmash engage --platform youtube` → pulls recent comments on your
latest videos → Gemini drafts a warm, on-brand reply per comment → you tap
[a]pprove / [e]dit / [s]kip → approved replies post via the official API.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from . import llm as llm_mod
from .config import Config

DRAFT_PROMPT = """You manage comments for a short-form video creator. Draft ONE reply.

RULES:
- Warm, human, specific to the comment. Never generic ("Thanks for watching!").
- <= 280 characters. No hashtags. No emojis unless the comment used them.
- If it's a question you can't answer, say so honestly and invite discussion.
- If it's spam/hate, reply exactly: SKIP
- Output ONLY the reply text (or SKIP).

Video title: {title}
Comment from @{author}: {text}
Reply:"""


@dataclass
class Comment:
    platform: str
    id: str
    author: str
    text: str
    video_title: str
    reply_to: dict  # platform-specific locator for posting the reply


def draft_reply(comment: Comment, cfg: Config | None = None) -> str:
    cfg = cfg or Config()
    if llm_mod.provider(cfg) == "template":
        return f"Thanks {comment.author} — appreciate you watching! (offline draft)"
    return llm_mod.chat_text(
        None,
        DRAFT_PROMPT.format(title=comment.video_title, author=comment.author,
                            text=comment.text),
        cfg).strip().strip('"')


# ---------------- fetchers (official APIs, read-only) ----------------

def fetch_youtube_comments(cfg: Config, max_videos: int = 3,
                           per_video: int = 10) -> list[Comment]:
    from .publish.youtube import _service
    yt = _service(cfg)
    out: list[Comment] = []
    vids = yt.search().list(part="id,snippet", forMine=True, type="video",
                            order="date", maxResults=max_videos).execute()
    for item in vids.get("items", []):
        vid, title = item["id"]["videoId"], item["snippet"]["title"]
        threads = yt.commentThreads().list(
            part="snippet", videoId=vid, maxResults=per_video,
            order="time", textFormat="plainText").execute()
        for th in threads.get("items", []):
            top = th["snippet"]["topLevelComment"]["snippet"]
            out.append(Comment("youtube", th["id"],
                               top.get("authorDisplayName", "?"),
                               top.get("textDisplay", "")[:500], title,
                               {"video_id": vid}))
    return out


def fetch_tiktok_comments(cfg: Config) -> list[Comment]:
    token = cfg.require("token", "TIKTOK_ACCESS_TOKEN", "reading TikTok comments")
    headers = {"Authorization": f"Bearer {token}"}
    # list videos, then comments per video (Content Posting / Display API)
    vids = httpx.post("https://open.tiktokapis.com/v2/video/list/",
                      headers=headers, json={"max_count": 5}, timeout=30).json()
    out: list[Comment] = []
    for v in vids.get("data", {}).get("videos", []):
        cs = httpx.post("https://open.tiktokapis.com/v2/video/comment/list/",
                        headers=headers,
                        json={"video_id": v["id"], "count": 10}, timeout=30).json()
        for c in cs.get("data", {}).get("comments", []):
            out.append(Comment("tiktok", c["id"], c.get("comment_user", {}).get("nickname", "?"),
                               c.get("text", "")[:500], v.get("title", ""),
                               {"video_id": v["id"]}))
    return out


def fetch_instagram_comments(cfg: Config) -> list[Comment]:
    from .publish.instagram import _call
    ig_id = cfg.require("ig_user", "IG_USER_ID", "reading IG comments")
    media = _call(cfg, "GET", f"/{ig_id}/media",
                  params={"fields": "id,caption,timestamp", "limit": 5})
    out: list[Comment] = []
    for m in media.get("data", []):
        cs = _call(cfg, "GET", f"/{m['id']}/comments",
                   params={"fields": "id,username,text", "limit": 10})
        for c in cs.get("data", []):
            out.append(Comment("instagram", c["id"], c.get("username", "?"),
                               c.get("text", "")[:500],
                               (m.get("caption") or "")[:80], {"media_id": m["id"]}))
    return out


def fetch_x_mentions(cfg: Config) -> list[Comment]:
    import tweepy
    client = tweepy.Client(
        consumer_key=cfg.secret("X_API_KEY"), consumer_secret=cfg.secret("X_API_SECRET"),
        access_token=cfg.secret("X_ACCESS_TOKEN"),
        access_token_secret=cfg.secret("X_ACCESS_SECRET"))
    me = client.get_me().data
    mentions = client.get_users_mentions(me.id, max_results=10,
                                         tweet_fields=["created_at"],
                                         expansions=["author_id"])
    users = {u.id: u.username for u in (mentions.includes.get("users", []) if mentions.includes else [])}
    return [Comment("x", str(t.id), users.get(t.author_id, "?"), t.text[:500],
                    "", {"tweet_id": str(t.id)})
            for t in (mentions.data or [])]


FETCHERS = {"youtube": fetch_youtube_comments, "tiktok": fetch_tiktok_comments,
            "instagram": fetch_instagram_comments, "x": fetch_x_mentions}


# ---------------- posters (only called after human approval) ----------------

def post_reply(comment: Comment, text: str, cfg: Config) -> dict:
    if comment.platform == "youtube":
        from .publish.youtube import _service
        yt = _service(cfg)
        r = yt.comments().insert(part="snippet", body={
            "snippet": {"parentId": comment.id,
                        "textOriginal": text}}).execute()
        return {"id": r["id"]}
    if comment.platform == "tiktok":
        token = cfg.require("token", "TIKTOK_ACCESS_TOKEN", "replying on TikTok")
        r = httpx.post("https://open.tiktokapis.com/v2/video/comment/reply/",
                       headers={"Authorization": f"Bearer {token}"},
                       json={"video_id": comment.reply_to["video_id"],
                             "comment_id": comment.id, "text": text}, timeout=30)
        r.raise_for_status()
        return r.json()
    if comment.platform == "instagram":
        from .publish.instagram import _call
        r = _call(cfg, "POST", f"/{comment.reply_to['media_id']}/replies",
                  data={"message": text})
        return r
    if comment.platform == "x":
        import tweepy
        client = tweepy.Client(
            consumer_key=cfg.secret("X_API_KEY"),
            consumer_secret=cfg.secret("X_API_SECRET"),
            access_token=cfg.secret("X_ACCESS_TOKEN"),
            access_token_secret=cfg.secret("X_ACCESS_SECRET"))
        t = client.create_tweet(text=text[:280],
                                in_reply_to_tweet_id=int(comment.reply_to["tweet_id"]))
        return {"id": t.data["id"]}
    raise ValueError(f"no poster for {comment.platform}")
