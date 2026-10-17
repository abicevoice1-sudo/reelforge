"""Pipeline orchestration: the full prompt → finished MP4 run.

create_project(topic, duration):
  script (Gemini/template) → voice (Edge-TTS) → stock (Pexels/Pixabay/generated)
  → captions (whisper/fallback) → render (FFmpeg 1080x1920)
Each stage's artifacts land in ~/.reelforge/projects/<slug>/ so any stage can
be re-run or inspected. plan.json is the contract between stages.

publish_project(slug, platforms): uploads final.mp4 via official APIs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import captions as captions_mod
from . import edit, music, script, stock, voice
from .captions import Word
from .config import PROJECTS_DIR, Config, ensure_home
from .publish import publish as publish_adapter
from .schemas import EditPlan

console = Console()


def slugify(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] or "video"
    return f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"


def project_dir(slug: str) -> Path:
    return PROJECTS_DIR / slug


def list_projects() -> list[dict]:
    ensure_home()
    out = []
    for d in sorted(PROJECTS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        plan = d / "plan.json"
        final = d / "final.mp4"
        out.append({"slug": d.name,
                    "has_plan": plan.exists(), "has_video": final.exists(),
                    "size": final.stat().st_size if final.exists() else 0})
    return out


def load_plan(slug: str) -> EditPlan:
    plan_file = project_dir(slug) / "plan.json"
    return EditPlan.model_validate(json.loads(plan_file.read_text()))


def create_project(topic: str, duration: int = 30,
                   cfg: Config | None = None) -> Path:
    """Run the full creation pipeline. Returns the project directory."""
    cfg = cfg or Config()
    ensure_home()
    edit.render_quiet_check()

    slug = slugify(topic)
    workdir = project_dir(slug)
    workdir.mkdir(parents=True)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console) as prog:
        t = prog.add_task("Writing script…", total=None)
        plan = script.generate_plan(topic, duration, cfg)
        (workdir / "plan.json").write_text(plan.model_dump_json(indent=2))
        prog.update(t, description=f"Script ready: {plan.title[:50]}")

        t = prog.add_task("Voicing narration…", total=None)
        audio_paths = voice.synthesize_plan(plan, workdir, cfg)
        voice.concat_audio(audio_paths, workdir / "voiceover.mp3")

        t = prog.add_task("Fetching footage…", total=None)
        clips = stock.fetch_plan_stock(plan, workdir, cfg)

        t = prog.add_task("Writing captions…", total=None)
        # word timings across the whole timeline
        words: list[Word] = []
        offset = 0.0
        for scene, ap in zip(plan.scenes, audio_paths):
            dur = voice.probe_duration(ap)
            try:
                ws = captions_mod.whisper_words(ap, offset)
                if not ws:
                    raise RuntimeError("empty")
            except Exception:
                ws = captions_mod.distribute_words(scene, dur, offset)
            words.extend(ws)
            offset += dur
        captions_ass = captions_mod.build_ass(
            words, workdir / "captions.ass", style=cfg.get("caption_style"),
            fontsize=cfg.get("caption_fontsize"),
            width=cfg.get("width"), height=cfg.get("height"),
            overlays=captions_mod.plan_overlays(plan, offset))

        t = prog.add_task("Rendering 1080x1920…", total=None)
        track = music.pick_track(plan.music_mood, cfg)
        if not track and (url := cfg.get("music_url")):
            track = music.fetch_url(url, workdir / "music_cache.mp3")
        final = edit.render(plan, clips, audio_paths, captions_ass, words,
                            workdir, music_track=track, cfg=cfg)
        prog.update(t, description="Done")

    (workdir / "meta.json").write_text(json.dumps({
        "topic": topic, "slug": slug, "duration": duration,
        "created_at": datetime.now().isoformat(),
        "final": str(final), "seconds": voice.probe_duration(final),
    }, indent=2))
    console.print(f"[green]✓ Video ready:[/green] {final}")
    return workdir


def publish_project(slug: str, platforms: list[str], cfg: Config | None = None,
                    dry_run: bool = False, **kwargs) -> dict[str, dict]:
    """Upload a finished project via official platform APIs."""
    cfg = cfg or Config()
    workdir = project_dir(slug)
    final = workdir / "final.mp4"
    if not final.exists():
        raise FileNotFoundError(f"No rendered video in {workdir} — run create first.")
    plan = load_plan(slug)
    results = {}
    for platform in platforms:
        console.print(f"Publishing to {platform}…")
        results[platform] = publish_adapter(
            platform, final, plan.title, plan.description, plan.hashtags,
            cfg, dry_run=dry_run, **kwargs)
        console.print(f"[green]✓ {platform}:[/green] "
                      f"{results[platform].get('url', results[platform])}")
    (workdir / "publishes.json").write_text(json.dumps(results, indent=2))
    return results
