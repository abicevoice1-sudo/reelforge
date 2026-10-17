"""Plain-text script format for reasoning LLMs.

nvidia/nemotron-3.5-lightning-30b-a3b — the only chat model provisioned on
Syed's NVIDIA key — falls into an unending reasoning loop when asked for
strict JSON (verified 2026-10-16: 170s of streaming, 4655 reasoning chars,
0 content chars, no finish). It answers the same task reliably when asked
for plain text in a fixed layout, which this module parses into an EditPlan.
"""

from __future__ import annotations

import re

from .schemas import EditPlan, Scene

SYSTEM_PROMPT = """You write scripts for 30-second vertical food videos. Reply in plain text using exactly this format, no markdown, no extra commentary:

TITLE: <catchy title under 60 chars>
HOOK: <the first 3 seconds, a bold claim under 12 words>
SCENES:
1. [7s] SAY: <voiceover: one or two short spoken sentences> | TEXT: <3-6 punchy on-screen words> | SHOW: <2-4 visual search terms>
2. [7s] SAY: <...> | TEXT: <...> | SHOW: <...>
CTA: <one subscribe/follow line>
HASHTAGS: <#tag1 #tag2 #tag3 #tag4 #tag5>

Rules: 4 scenes, short spoken sentences, one idea per scene."""


def _field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", text, re.M | re.I)
    return m.group(1).strip() if m else ""


def parse_plan(text: str, topic: str, duration: int = 30) -> EditPlan:
    """Parse the plain-text script format into a validated EditPlan."""
    title = _field(text, "TITLE") or f"{topic.title()} — explained in {duration}s"
    hook = _field(text, "HOOK") or f"Stop scrolling. This is about {topic}."
    cta = _field(text, "CTA") or "Follow for daily shorts"
    tags = _field(text, "HASHTAGS")
    hashtags = re.findall(r"#\w+", tags) or ["#shorts", "#reels"]

    scene_re = re.compile(
        r"^\s*\d+\.\s*\[(?P<dur>[\d.]+)s?\]\s*"
        r"SAY:\s*(?P<say>[^|]+?)\s*\|\s*"
        r"TEXT:\s*(?P<txt>[^|]+?)\s*\|\s*"
        r"SHOW:\s*(?P<show>.+?)\s*$",
        re.M | re.I,
    )
    scenes = []
    for i, m in enumerate(scene_re.finditer(text)):
        scenes.append(Scene(
            id=i + 1,
            voiceover=m.group("say").strip(),
            on_screen_text=m.group("txt").strip()[:60],
            stock_query=m.group("show").strip()[:80],
            duration=float(m.group("dur")),
            transition="zoom" if i % 2 == 0 else "cut",
            mood="energetic",
        ))
    if len(scenes) < 2:
        raise ValueError(f"Could not parse scenes from model output: {text[:200]!r}")

    # Fit the requested total duration.
    total = sum(s.duration for s in scenes)
    if total > 0:
        scale = duration / total
        for s in scenes:
            s.duration = round(s.duration * scale, 1)

    plan = EditPlan(
        title=title[:100],
        hook=hook[:140],
        description=f"{title} {hook}"[:300],
        hashtags=hashtags[:10],
        music_mood="upbeat",
        cta=cta[:140],
        scenes=scenes,
    )
    plan.validate_runtime(duration)
    return plan
