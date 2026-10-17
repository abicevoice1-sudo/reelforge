"""Dubbing: re-voice a finished project in another language.

`reelforge dub <slug> --lang ur` →
  1. translates each scene's voiceover via the LLM,
  2. re-synthesizes narration with a native neural voice,
  3. re-renders with the same verified clips, new captions.

The footage doesn't change — only the voice. One project, many audiences.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import voice
from .config import Config
from .pipeline import _finish_project, load_plan, project_dir


def translate(text: str, lang: str, cfg: Config) -> str:
    from . import llm
    lang_name = voice.DUB_LANGUAGES.get(lang, lang)
    return llm.chat_text(
        f"You translate short video narrations into {lang_name}. "
        "Keep it punchy, conversational, same length as the original. "
        "Return ONLY the translation, no quotes or explanations.",
        text, cfg, temperature=0.3)


def dub_project(slug: str, lang: str, cfg: Config | None = None) -> Path:
    cfg = cfg or Config()
    if lang not in voice.DUB_LANGUAGES:
        raise ValueError(f"Unknown language {lang!r}. "
                         f"Choose from: {', '.join(voice.DUB_LANGUAGES)}")
    plan = load_plan(slug)
    src = project_dir(slug)
    if not (src / "clips").exists():
        raise FileNotFoundError(f"No clips in {slug} — nothing to dub.")

    dub_slug = f"{slug}-dub-{lang}"
    workdir = project_dir(dub_slug)
    (workdir / "clips").mkdir(parents=True, exist_ok=True)
    (workdir / "audio").mkdir(parents=True, exist_ok=True)
    for clip in (src / "clips").glob("scene_*.mp4"):
        shutil.copy2(clip, workdir / "clips" / clip.name)

    dub_voice = voice.SAMPLE_VOICES[lang][0]
    dub_cfg = Config(overrides={**cfg._data, "voice": dub_voice})
    new_scenes = []
    audio_paths = []
    for scene in plan.scenes:
        translated = translate(scene.voiceover, lang, cfg)
        out = workdir / "audio" / f"scene_{scene.id:02d}.mp3"
        voice.synthesize_scene(translated, out, dub_cfg)
        audio_paths.append(out)
        new_scenes.append(scene.model_copy(update={"voiceover": translated}))
    dub_plan = plan.model_copy(update={"scenes": new_scenes,
                                       "title": f"{plan.title} ({voice.DUB_LANGUAGES[lang]})"})
    (workdir / "plan.json").write_text(dub_plan.model_dump_json(indent=2))
    final = _finish_project(dub_plan, workdir, audio_paths, dub_cfg)
    print(f"Dubbed video ready: {final}")
    return final
