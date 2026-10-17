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
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            return llm.chat_text(
                f"You translate short video narrations into {lang_name}. "
                "Keep it punchy, conversational, same length as the original. "
                "Return ONLY the translation, no quotes or explanations.",
                text, cfg, temperature=0.3)
        except Exception as e:  # noqa: BLE001 — LLM APIs are flaky; retry
            last_err = e
            print(f"translate: attempt {attempt + 1}/3 failed ({e}); retrying…")
            import time
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Translation failed after 3 attempts: {last_err}")


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

    # Scenes are independent: translate + synthesize in parallel.
    # Sequential was 9 × ~45s; parallel is ~1 minute total.
    def _dub_scene(scene):
        translated = translate(scene.voiceover, lang, cfg)
        out = workdir / "audio" / f"scene_{scene.id:02d}.mp3"
        voice.synthesize_scene(translated, out, dub_cfg)
        return scene.model_copy(update={"voiceover": translated}), out

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as ex:
        # map preserves scene order
        dubbed = list(ex.map(_dub_scene, plan.scenes))
    new_scenes = [s for s, _ in dubbed]
    audio_paths = [p for _, p in dubbed]
    dub_plan = plan.model_copy(update={"scenes": new_scenes,
                                       "title": f"{plan.title} ({voice.DUB_LANGUAGES[lang]})"})
    (workdir / "plan.json").write_text(dub_plan.model_dump_json(indent=2))
    final = _finish_project(dub_plan, workdir, audio_paths, dub_cfg)
    print(f"Dubbed video ready: {final}")
    return final
