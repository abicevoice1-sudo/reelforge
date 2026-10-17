"""Agent layer: one prompt → planned job → your confirmation → execution.

"make a 30s reel about hyderabadi biryani and post it Friday at 6pm"
becomes an AgentJob {action, topic, duration, platforms, schedule_at}.
Gemini parses; a regex fallback handles the common shapes offline.

The agent NEVER publishes without you confirming the plan first, and it
never touches engagement automation — that surface doesn't exist in this
codebase by design.
"""

from __future__ import annotations

import re

from . import llm as llm_mod
from .config import Config
from .schemas import AgentJob
from .schedule import parse_when

AGENT_PROMPT = """Parse the user's request into JSON. Output ONLY JSON.

Fields:
- action: "create" (make/render a video), "publish" (publish an existing project),
  "schedule" (create now, publish later), "engage" (draft comment replies),
  "status" (show queue/projects)
- topic: the video subject ("" if not a video request)
- duration: seconds (default 30; parse "30s", "1 minute", etc.)
- platforms: subset of ["youtube","tiktok","instagram","x"] (default all four;
  parse "just youtube", "tiktok and reels", etc.)
- schedule_at: ISO-8601 datetime if they name a time ("Friday 6pm", "tomorrow 9am"),
  else null. Assume {tz}.
- project_slug: if they reference an existing project ("publish my biryani video")
- note: anything else worth remembering

User request: {request}"""


def _regex_parse(request: str, cfg: Config) -> AgentJob:
    r = request.lower()
    action = "create"
    if any(w in r for w in ("publish my", "post my", "upload my")):
        action = "publish"
    elif re.search(r"\b(post|publish|schedule|drop)\b.*\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|am|pm|\d{1,2}:\d{2})\b", r):
        action = "schedule"
    elif any(w in r for w in ("comment", "replies", "reply to")):
        action = "engage"
    elif any(w in r for w in ("status", "queue", "what's scheduled")):
        action = "status"

    m = re.search(r"(\d+)\s*(?:s|sec|second)", r)
    duration = int(m.group(1)) if m else (
        int(re.search(r"(\d+)\s*(?:m|min|minute)", r).group(1)) * 60
        if re.search(r"(\d+)\s*(?:m|min|minute)", r) else 30)
    duration = max(5, min(180, duration))

    # NOTE: the generic word "reel"/"short" means a short video, not Instagram —
    # only explicit platform names select platforms.
    tokens = set(re.findall(r"[a-z0-9]+", r))
    platforms = []
    if tokens & {"youtube", "yt"}:
        platforms.append("youtube")
    if "tiktok" in tokens:
        platforms.append("tiktok")
    if tokens & {"instagram", "ig"}:
        platforms.append("instagram")
    if tokens & {"x", "twitter"}:
        platforms.append("x")
    if not platforms and action in ("create", "publish", "schedule"):
        platforms = ["youtube", "tiktok", "instagram", "x"]

    schedule_at = None
    tm = re.search(r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow)"
                   r"(?:\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?", r)
    if tm and action in ("create", "schedule"):
        try:
            schedule_at = parse_when(tm.group(0), cfg.get("timezone")).isoformat()
        except ValueError:
            pass

    # topic: text after "about" up to "and post/schedule/for"
    topic = ""
    mt = re.search(r"about\s+(.+?)(?:\s+and\s+(?:post|publish|schedule|drop)|\s*$)", r)
    if mt:
        topic = mt.group(1).strip()
    return AgentJob(action=action, topic=topic, duration=duration,
                    platforms=platforms, schedule_at=schedule_at)


def parse_request(request: str, cfg: Config | None = None) -> AgentJob:
    cfg = cfg or Config()
    if llm_mod.provider(cfg) == "template":
        return _regex_parse(request, cfg)
    job = AgentJob.model_validate(llm_mod.chat_json(
        None, AGENT_PROMPT.format(request=request, tz=cfg.get("timezone")), cfg,
        temperature=0.3))
    if job.schedule_at and "T" not in job.schedule_at:
        # model gave a bare phrase — resolve it properly
        try:
            job.schedule_at = parse_when(job.schedule_at,
                                         cfg.get("timezone")).isoformat()
        except ValueError:
            job.schedule_at = None
    return job


def describe(job: AgentJob) -> str:
    when = f"scheduled for {job.schedule_at}" if job.schedule_at else "right away"
    plats = ", ".join(job.platforms) or "—"
    if job.action == "engage":
        return "Draft replies to recent comments (you approve each one)."
    if job.action == "status":
        return "Show the publish queue and recent projects."
    if job.action == "publish":
        return (f"Publish project '{job.project_slug or job.topic}' to {plats}, "
                f"{when}.")
    return (f"Create a {job.duration}s video about '{job.topic}', "
            f"publish to {plats}, {when}.")
