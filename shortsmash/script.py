"""Script stage: an LLM writes the script + edit plan as strict JSON.

Provider is routed by shortsmash.llm (NVIDIA NIM preferred — free tier and
already Syed's production LLM — then Gemini, then an offline template).
JSON-mode output validated by pydantic; one repair retry on failure.
"""

from __future__ import annotations

import re

from . import llm as llm_mod
from . import plain_script
from .config import Config
from .schemas import EditPlan, Scene

SYSTEM_PROMPT = """You are ShortSmash's viral-short scriptwriter — the mind behind scroll-stopping
vertical videos (9:16, 15-60s) with the craft of a film trailer and the punch
of the best creators. Think like an AI-film director: every scene is a SHOT,
not a slide.

VOICE (non-negotiable):
- Talk TO the viewer. Second person. Opinions, not lectures.
- Short punchy sentences. One punch per scene. No filler words.
- Rhythm: hook hits hard, middle scenes stack proof fast, payoff lands the CTA.
- Never write like Wikipedia. If a line could be in an encyclopedia, rewrite it
  with attitude. Facts are ammunition, not the script.
- Cinematic verbs: reveal, plunge, sweep, ignite — never "show" or "display".

VISUAL DIRECTION (this is what separates premium from basic):
- Every stock_query must read like a cinematographer's shot list: 2-4 concrete
  terms PLUS a cinematic qualifier — e.g. "espresso pouring macro slow motion",
  not "coffee"; "neon night market shallow depth of field", not "market".
  Qualifiers: macro, slow motion, aerial, shallow depth of field,
  dramatic lighting, golden hour, close-up, tracking shot.
- Use common, searchable footage terms — never proper nouns, landmarks, or
  place names (stock sites don't index "Charminar"; they index
  "indian street food cinematic").
- Vary shot scale across scenes: wide → close → macro → wide. A video that
  never changes shot scale feels flat and cheap.
- mood per scene: energetic, dramatic, intimate, epic, mysterious — and mean
  it in the voiceover too.

STRUCTURE:
- A ruthless hook in the first 3 seconds: a bold claim or open loop, <= 12 words.
- 8-12 scenes for a 30s video (3-4s each). One idea per scene, then CUT.
- A clear payoff or CTA at the end that invites comments.

RULES:
- Output ONLY valid JSON matching the schema below. No markdown, no commentary.
- voiceover: natural spoken English, ~2.4 words/second of the scene duration.
- on_screen_text: <= 8 words, punchy, different from the voiceover (complement, don't repeat).
- stock_query: 2-4 concrete visual search terms (e.g. "busy night market neon").
  Use common, searchable footage terms — never proper nouns, landmarks, or
  place names (stock sites don't index "Charminar" or "Hyderabad"; they do
  index "indian street food").
- transition: one of cut, fade, zoom, slide. Prefer cut/zoom for energy.
- hashtags: 5-10, no spaces, mix of broad and niche.
- The hook must create an open loop or bold claim in under 12 words.

SCHEMA:
{
  "title": "string (<=100 chars)",
  "hook": "string (<=140 chars)",
  "description": "string",
  "hashtags": ["#tag"],
  "music_mood": "upbeat | chill | dramatic | funny",
  "cta": "string",
  "scenes": [
    {"id": 1, "voiceover": "...", "on_screen_text": "...",
     "stock_query": "...", "duration": 5.0, "transition": "cut", "mood": "energetic"}
  ]
}"""


def fallback_plan(topic: str, duration: int = 30) -> EditPlan:
    """Deterministic offline plan — used when no Gemini key is configured."""
    n = max(2, min(6, round(duration / 7)))
    per = duration / n
    scenes = [
        Scene(
            id=i + 1,
            voiceover=f"Here's what nobody tells you about {topic}. "
                      + ("Listen closely — this changes everything. "
                         if i == 0 else
                         "And here's the part most people completely miss. "
                         if i == n - 1 else
                         "But wait, it gets even more interesting. "),
            on_screen_text=(f"The truth about {topic}" if i == 0
                            else f"Secret #{i + 1}" if i < n - 1
                            else "Follow for more"),
            stock_query=f"{topic} cinematic b-roll",
            duration=round(per, 1),
            transition="zoom" if i % 2 == 0 else "cut",
            mood="energetic",
        )
        for i in range(n)
    ]
    return EditPlan(
        title=f"{topic.title()} — explained in {duration}s",
        hook=f"Stop scrolling. This {duration}-second truth about {topic} will surprise you.",
        description=f"Everything you need to know about {topic} in {duration} seconds.",
        hashtags=["#shorts", "#reels", f"#{re.sub(r'[^a-zA-Z0-9]', '', topic.lower()) or 'viral'}"],
        music_mood="upbeat",
        cta="Follow for daily shorts",
        scenes=scenes,
    )


def _generate_plan_nvidia(topic: str, duration: int, cfg: Config) -> EditPlan:
    """Script via NVIDIA's reasoning model using the plain-text format.

    nemotron-3.5-lightning-30b-a3b (the only chat model on this key) never
    converges when asked for strict JSON — it reasons forever. The same
    task as plain text in a fixed layout gets a real answer; plain_script
    parses it into a validated EditPlan.
    """
    user = (f"Topic: {topic}. Make it a {duration}-second video, "
            f"scene lengths adding up to about {duration} seconds.")
    last_err: Exception | None = None
    for _ in range(2):
        try:
            text = llm_mod.chat_text(
                plain_script.SYSTEM_PROMPT, user, cfg, temperature=0.7)
            return plain_script.parse_plan(text, topic, duration)
        except Exception as exc:  # noqa: BLE001 — retry once, then raise
            last_err = exc
    raise RuntimeError(f"NVIDIA script failed twice: {last_err}")


def generate_plan(topic: str, duration: int = 30, cfg: Config | None = None) -> EditPlan:
    """Generate an EditPlan for `topic` via the configured LLM (or template)."""
    cfg = cfg or Config()
    provider = llm_mod.provider(cfg)
    if provider == "template":
        return fallback_plan(topic, duration)
    if provider == "nvidia":
        return _generate_plan_nvidia(topic, duration, cfg)

    prompt = (f"Write a {duration}-second vertical short about: {topic}. "
              f"Total of all scene durations must be close to {duration} seconds.")
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            user = prompt if attempt == 0 else (
                prompt + "\n\nYour previous output failed schema validation with: "
                + str(last_err) + ". Fix it and output ONLY valid JSON.")
            plan = EditPlan.model_validate(llm_mod.chat_json(SYSTEM_PROMPT, user, cfg))
            plan.validate_runtime(cfg.get("max_duration"))
            return plan
        except Exception as exc:  # noqa: BLE001 — retry once with repair prompt
            last_err = exc
    raise RuntimeError(f"LLM produced an invalid plan twice: {last_err}")
