"""Pydantic contracts: the edit plan is the single source of truth.

Gemini produces an EditPlan; every downstream stage (voice, stock, captions,
render, publish metadata) consumes it. Strict validation here means a bad LLM
output fails fast with a clear error instead of a broken video.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Scene(BaseModel):
    """One beat of the video."""

    id: int = Field(ge=1)
    voiceover: str = Field(min_length=1, max_length=500,
                           description="Spoken narration for this scene.")
    on_screen_text: str = Field(default="",
                                description="Short punchy caption text (<=8 words).")
    stock_query: str = Field(min_length=1,
                             description="Search terms for stock footage.")
    duration: float = Field(gt=1.0, le=30.0,
                           description="Target scene length in seconds.")
    transition: str = Field(default="cut",
                            description="cut | fade | zoom | slide")
    mood: str = Field(default="neutral",
                      description="Guides music + pacing: energetic, calm, dramatic, funny.")

    @field_validator("transition")
    @classmethod
    def _transition_known(cls, v: str) -> str:
        allowed = {"cut", "fade", "zoom", "slide"}
        if v not in allowed:
            raise ValueError(f"transition must be one of {sorted(allowed)}")
        return v


class EditPlan(BaseModel):
    """Full blueprint for one short."""

    title: str = Field(min_length=1, max_length=100)
    hook: str = Field(min_length=1, max_length=140,
                      description="First 3 seconds — must stop the scroll.")
    description: str = Field(default="", max_length=2000,
                             description="Platform description / caption.")
    hashtags: list[str] = Field(default_factory=list, max_length=15)
    scenes: list[Scene] = Field(min_length=1, max_length=12)
    music_mood: str = Field(default="upbeat")
    cta: str = Field(default="",
                     description="Call to action shown on the end card.")

    @field_validator("hashtags")
    @classmethod
    def _hashtags_clean(cls, v: list[str]) -> list[str]:
        return [h if h.startswith("#") else f"#{h}" for h in v]

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    def validate_runtime(self, max_duration: float = 180) -> None:
        if self.total_duration > max_duration:
            raise ValueError(
                f"Plan is {self.total_duration:.1f}s, over the {max_duration}s cap. "
                "Ask for a shorter video or fewer scenes."
            )


class AgentJob(BaseModel):
    """Structured job produced by the agent layer from natural language."""

    action: str = Field(description="create | publish | schedule | engage | status")
    topic: str = Field(default="")
    duration: int = Field(default=30, ge=5, le=180)
    platforms: list[str] = Field(default_factory=lambda: ["youtube", "tiktok", "instagram"])
    schedule_at: str | None = Field(default=None,
                                    description="ISO-8601 datetime, or None for ASAP.")
    project_slug: str | None = None
    note: str = Field(default="")
