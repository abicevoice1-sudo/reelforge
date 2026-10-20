"""Pipeline orchestration: the full prompt → finished MP4 run.

create_project(topic, duration):
  script (Gemini/template) → voice (Edge-TTS) → stock (Pexels/Pixabay/generated)
  → captions (whisper/fallback) → render (FFmpeg 1080x1920)
Each stage's artifacts land in ~/.shortsmash/projects/<slug>/ so any stage can
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
from . import edit, music, script, stock, visual, voice
from .captions import Word
from .config import PROJECTS_DIR, Config, ensure_home
from creator_publish.publish import publish as publish_adapter
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
        prog.update(t, description="Footage ready")

    final = _finish_project(plan, workdir, audio_paths, cfg)

    (workdir / "meta.json").write_text(json.dumps({
        "topic": topic, "slug": slug, "duration": duration,
        "created_at": datetime.now().isoformat(),
        "final": str(final), "seconds": voice.probe_duration(final),
    }, indent=2))
    console.print(f"[green]✓ Video ready:[/green] {final}")
    return workdir


def _finish_project(plan: EditPlan, workdir: Path, audio_paths: list[Path],
                   cfg: Config) -> Path:
    """Captions → music → render. Shared by create and resume."""
    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console) as prog:
        t = prog.add_task("Writing captions…", total=None)
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
            overlays=(captions_mod.plan_overlays(plan, offset)
                      if cfg.get("caption_overlays", False) else None))

        t = prog.add_task("Rendering 1080x1920…", total=None)
        track = music.pick_track(plan.music_mood, cfg)
        if not track:
            # Never ship a silent video: provision the starter library once.
            music.ensure_library(cfg)
            track = music.pick_track(plan.music_mood, cfg)
        clips = sorted((workdir / "clips").glob("scene_*.mp4"))
        final = edit.render(plan, clips, audio_paths, captions_ass, words,
                            workdir, music_track=track, cfg=cfg)
        prog.update(t, description="Done")
    return final


def create_lyrics_project(lyrics: str, title: str = "", duration: int = 30,
                        cfg: Config | None = None) -> Path:
    """Render a karaoke-style lyrics video. Each line gets screen time
    weighted by word count; words highlight in sync across the duration.
    No narration — background music carries the audio."""
    from .schemas import EditPlan, Scene
    cfg = cfg or Config()
    ensure_home()
    edit.render_quiet_check()

    lines = [ln.strip() for ln in lyrics.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("No lyrics provided")
    title = title.strip() or lines[0][:60]
    slug = slugify("lyrics-" + title)
    workdir = project_dir(slug)
    workdir.mkdir(parents=True, exist_ok=True)

    total_words = sum(len(ln.split()) for ln in lines)
    scenes = []
    for i, ln in enumerate(lines[:12], 1):
        share = len(ln.split()) / total_words
        dur = max(2.0, min(30.0, duration * share))
        scenes.append(Scene(id=i, voiceover=ln, on_screen_text=ln,
                            stock_query=f"music concert stage lights {title[:30]}",
                            duration=dur, transition="cut"))
    plan = EditPlan(title=title, hook=lines[0][:140], description="",
                    hashtags=["lyrics", "lyricvideo"],
                    scenes=scenes, music_mood="upbeat", cta="")
    (workdir / "plan.json").write_text(plan.model_dump_json(indent=2))

    with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                  console=console) as prog:
        t = prog.add_task("Fetching footage…", total=None)
        stock.fetch_plan_stock(plan, workdir, cfg)
        prog.update(t, description="Footage ready")

        t = prog.add_task("Writing lyrics captions…", total=None)
        words: list[captions_mod.Word] = []
        offset = 0.0
        for scene in plan.scenes:
            words.extend(captions_mod.distribute_words(scene, scene.duration, offset))
            offset += scene.duration
        captions_ass = captions_mod.build_ass(
            words, workdir / "captions.ass", style="lyrics",
            fontsize=72, width=cfg.get("width"), height=cfg.get("height"))

        t = prog.add_task("Rendering 1080x1920…", total=None)
        track = music.pick_track("upbeat", cfg) or music.ensure_library(cfg)
        track = music.pick_track("upbeat", cfg)
        clips = sorted((workdir / "clips").glob("scene_*.mp4"))
        final = edit.render(plan, clips, [], captions_ass, words,
                            workdir, music_track=track, cfg=cfg)
        prog.update(t, description="Done")

    (workdir / "meta.json").write_text(json.dumps({
        "topic": title, "slug": slug, "duration": duration, "type": "lyrics",
        "created_at": datetime.now().isoformat(),
        "final": str(final), "seconds": voice.probe_duration(final),
    }, indent=2))
    console.print(f"[green]✓ Lyrics video ready:[/green] {final}")
    return workdir


def resume_project(slug: str, cfg: Config | None = None) -> Path:
    """Resume a project that failed partway: only missing stages re-run."""
    cfg = cfg or Config()
    ensure_home()
    edit.render_quiet_check()
    workdir = project_dir(slug)
    if not (workdir / "plan.json").exists():
        raise RuntimeError(f"No plan.json in {workdir} — use `new` instead.")
    plan = EditPlan.model_validate_json((workdir / "plan.json").read_text())
    console.print(f"Resuming [bold]{slug}[/bold] ({len(plan.scenes)} scenes)")

    audio_dir = workdir / "audio"
    audio_paths = []
    for scene in plan.scenes:
        ap = audio_dir / f"scene_{scene.id:02d}.mp3"
        if not (ap.exists() and ap.stat().st_size > 0):
            console.print(f"  Voicing scene {scene.id}…")
            voice.synthesize_scene(scene.voiceover, ap, cfg)
        audio_paths.append(ap)
    voice.concat_audio(audio_paths, workdir / "voiceover.mp3")

    clips_dir = workdir / "clips"
    clips_dir.mkdir(exist_ok=True)
    for scene in plan.scenes:
        cp = clips_dir / f"scene_{scene.id:02d}.mp4"
        if cp.exists() and cp.stat().st_size > 0:
            continue
        console.print(f"  Fetching footage for scene {scene.id}…")
        visual.fetch(scene.stock_query, cp, cfg, seed=scene.id,
                     context=scene.voiceover,
                     duration=scene.duration or 4.0)

    final = _finish_project(plan, workdir, audio_paths, cfg)
    (workdir / "meta.json").write_text(json.dumps({
        "topic": plan.title, "slug": slug, "resumed": True,
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
    results = publish_video(final, plan.title or slug, plan.description or "",
                            plan.hashtags or [], platforms, cfg,
                            dry_run=dry_run, **kwargs)
    (workdir / "publishes.json").write_text(json.dumps(results, indent=2))
    return results


# ---------------------------------------------------------------------------
# Manual video posts — upload your own footage, post now or schedule it.
# ---------------------------------------------------------------------------

# Conservative per-platform limits for pre-flight warnings (not hard blocks).
_PLATFORM_LIMITS = {
    "youtube":   {"max_seconds": 180, "vertical": True,  "label": "YouTube Shorts"},
    "tiktok":    {"max_seconds": 600, "vertical": True,  "label": "TikTok"},
    "instagram": {"max_seconds": 180, "vertical": True,  "label": "Instagram Reels"},
    "facebook":  {"max_seconds": 540, "vertical": True,  "label": "Facebook Reels"},
    "x":         {"max_seconds": 140, "vertical": False, "label": "X"},
    "threads":   {"max_seconds": 300, "vertical": True,  "label": "Threads"},
    "bluesky":   {"max_seconds": 180, "vertical": True,  "label": "Bluesky"},
    "linkedin":  {"max_seconds": 600, "vertical": False, "label": "LinkedIn"},
    "pinterest": {"max_seconds": 300, "vertical": True,  "label": "Pinterest"},
    "snapchat":  {"max_seconds": 180, "vertical": True,  "label": "Snapchat"},
}


def probe_video(path: Path) -> dict:
    """ffprobe a video file. Raises on unreadable/missing files."""
    import subprocess

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Video not found: {p}")
    if p.suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv", ".m4v"}:
        raise ValueError(f"Unsupported video format {p.suffix} — use MP4/MOV/WebM.")
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,avg_frame_rate,codec_name",
         "-show_entries", "format=duration,size",
         "-of", "json", str(p)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(proc.stdout)
    if not info.get("streams"):
        raise ValueError(f"No video stream in {p} — is this a video file?")
    s = info["streams"][0]
    num, den = (s.get("avg_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den or 1)
    return {
        "width": int(s["width"]),
        "height": int(s["height"]),
        "fps": round(fps, 2),
        "codec": s.get("codec_name", "?"),
        "duration": float(info["format"].get("duration", 0)),
        "size_mb": round(float(info["format"].get("size", 0)) / 1e6, 1),
        "vertical": int(s["height"]) >= int(s["width"]),
    }


def validate_video(path: Path, platforms: list[str]) -> dict:
    """Pre-flight check: probe + per-platform warnings. Never raises for
    warnings — only for unreadable files."""
    meta = probe_video(path)
    warnings: list[str] = []
    mins, secs = divmod(int(meta["duration"]), 60)
    dur_str = f"{mins}:{secs:02d}"
    for plat in platforms:
        lim = _PLATFORM_LIMITS.get(plat)
        if not lim:
            continue
        if meta["duration"] > lim["max_seconds"]:
            lmin = lim["max_seconds"] // 60
            warnings.append(
                f"{lim['label']}: video is {dur_str}, over the ~{lmin}m "
                f"limit — it may be rejected or cut.")
        if lim["vertical"] and not meta["vertical"]:
            warnings.append(
                f"{lim['label']}: video is landscape — vertical performs "
                f"far better on this platform.")
    return {"ok": True, "duration_str": dur_str, **meta, "warnings": warnings}


def stage_upload(src: Path, cfg: Config | None = None) -> Path:
    """Copy a user video into ~/.shortsmash/uploads/ with a timestamped name.
    Returns the staged path (safe for the scheduler to reference later)."""
    from .config import UPLOADS_DIR, ensure_home

    ensure_home()
    src = Path(src)
    probe_video(src)  # fail fast on bad files
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    clean = re.sub(r"[^a-z0-9]+", "-", src.stem.lower()).strip("-")[:40] or "video"
    dest = UPLOADS_DIR / f"{stamp}-{clean}{src.suffix.lower()}"
    import shutil

    shutil.copy2(src, dest)
    return dest


def suggest_caption(video: Path, cfg: Config | None = None) -> dict:
    """AI-generate title/description/hashtags from video frames.

    Extracts 3 frames, asks Gemini vision to describe them, returns
    {"title", "description", "hashtags"}. Needs the Gemini connector;
    raises RuntimeError with a clear message when unavailable.
    """
    import base64
    import subprocess
    import sys
    import tempfile
    from pathlib import Path as _Path

    cfg = cfg or Config()
    helper = _Path.home() / "workspace/custom-connectors/custom.gemini/bin/gemini.py"
    if not helper.exists():
        raise RuntimeError(
            "Caption assist needs the Gemini connector "
            "(~/workspace/custom-connectors/custom.gemini) — not set up.")
    meta = probe_video(video)
    descs: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        for i, frac in enumerate((0.15, 0.5, 0.85)):
            t = max(0.5, meta["duration"] * frac)
            out = _Path(td) / f"f{i}.jpg"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(round(t, 1)),
                 "-i", str(video), "-frames:v", "1", "-q:v", "4", str(out)],
                check=True)
            frame_b64 = base64.b64encode(out.read_bytes()).decode()
            proc = subprocess.run(
                [sys.executable, str(helper), "generate"],
                input=json.dumps({
                    "user": "Describe this video frame in one sentence: "
                            "what is happening, objects, setting.",
                    "image_b64": frame_b64,
                    "model": cfg.get("gemini_model") or "gemini-3.8-flash",
                    "temperature": 0.3,
                }).encode(),
                capture_output=True, timeout=90)
            data = json.loads(proc.stdout.decode() or "{}")
            if data.get("ok", True) and data.get("content"):
                descs.append(data["content"].strip())
    if not descs:
        raise RuntimeError("Gemini vision returned nothing — try again later.")
    from . import llm as llm_mod

    prompt = (
        "You are a viral short-form video marketer. A short video shows:\n- "
        + "\n- ".join(descs)
        + "\nReply with EXACTLY three lines:\n"
        "TITLE: <punchy title, max 80 chars, no hashtags>\n"
        "DESC: <2-sentence description with a hook>\n"
        "TAGS: <8-12 hashtags, comma-separated, no spaces inside tags>")
    try:
        text = llm_mod.chat_text(
            "You write viral video titles.", prompt, cfg)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Caption text generation failed: {e}")
    title, desc, tags = "", "", []
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[6:].strip()[:100]
        elif line.upper().startswith("DESC:"):
            desc = line[5:].strip()[:500]
        elif line.upper().startswith("TAGS:"):
            tags = [t.strip() for t in line[5:].replace("#", "").split(",")
                    if t.strip()][:12]
            tags = ["#" + t.replace(" ", "") for t in tags]
    if not title:
        raise RuntimeError("The AI returned an unusable caption — try again.")
    return {"title": title, "description": desc, "hashtags": tags}


def publish_video(video: Path, title: str, description: str,
                  hashtags: list[str], platforms: list[str],
                  cfg: Config | None = None, dry_run: bool = False,
                  **kwargs) -> dict[str, dict]:
    """Publish ANY video file (not just a pipeline project) to platforms."""
    from creator_publish.publish import ADAPTERS

    cfg = cfg or Config()
    video = Path(video)
    probe_video(video)  # fail fast
    bad = [p for p in platforms if p not in ADAPTERS]
    if bad:
        raise ValueError(f"Unknown platforms: {bad}. Choose from {ADAPTERS}.")
    results: dict[str, dict] = {}
    for platform in platforms:
        console.print(f"Publishing to {platform}…")
        results[platform] = publish_adapter(
            platform, video, title, description, hashtags,
            cfg, dry_run=dry_run, **kwargs)
        console.print(f"[green]✓ {platform}:[/green] "
                      f"{results[platform].get('url', results[platform])}")
    return results


