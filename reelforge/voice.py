"""Voice stage: free, high-quality narration via Edge-TTS.

Edge-TTS is free, needs no API key, and its neural voices are the closest free
option to studio quality. Output is MP3 per scene, plus a concatenated full
track. Optional Piper support for fully-offline synthesis (set voice to a
piper model path with the `piper:` prefix).
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from .config import Config
from .schemas import EditPlan

SAMPLE_VOICES = {
    "en": ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"],
    "ur": ["ur-PK-AsadNeural", "ur-IN-GulNeural"],
    "ur-roman": ["ur-PK-AsadNeural", "ur-IN-GulNeural"],
    "hi": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"],
    "hi-roman": ["hi-IN-SwaraNeural", "hi-IN-MadhurNeural"],
    "ar": ["ar-SA-ZariyahNeural", "ar-EG-SalmaNeural"],
    "es": ["es-ES-ElviraNeural", "es-MX-DaliaNeural"],
    "fr": ["fr-FR-DeniseNeural", "fr-CA-SylvieNeural"],
    "de": ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
    "pt": ["pt-BR-FranciscaNeural", "pt-PT-RaquelNeural"],
    "zh": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"],
}

DUB_LANGUAGES = {"ur": "Urdu", "ur-roman": "Urdu (Roman)",
                 "hi": "Hindi", "hi-roman": "Hindi (Roman)",
                 "ar": "Arabic", "es": "Spanish",
                 "fr": "French", "de": "German", "pt": "Portuguese",
                 "zh": "Chinese"}

# Roman dubs: native-script voice, Latin-script captions. The base language
# drives translation and voice; captions get transliterated.
ROMAN_BASE = {"ur-roman": "ur", "hi-roman": "hi"}

# Offline Piper voices shipped in voices/ (repo root). Used automatically when
# Edge-TTS is unreachable, keyed by language — so a Urdu dub never falls back
# to the robotic gTTS voice while a native neural model sits on disk.
PIPER_VOICES = {
    "en": "en_US-amy-medium.onnx",
    "ur": "ur_PK-aegis_female-medium.onnx",
    "hi": "hi_IN-priyamvada-medium.onnx",
    "zh": "zh_CN-huayan-medium.onnx",
}


def _resolve_piper_model(voice: str, cfg: "Config") -> str:
    """Pick the best local Piper model for this voice's language."""
    voices_dir = Path(__file__).resolve().parent.parent / "voices"
    lang = voice.split("-")[0].lower() if "-" in voice else "en"
    candidate = PIPER_VOICES.get(lang)
    if candidate:
        p = voices_dir / candidate
        if p.exists():
            return str(p)
    configured = cfg.get("piper_voice") or ""
    if configured and Path(configured).expanduser().exists():
        return configured
    return ""


async def _edge_tts(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out))


def synthesize_scene(text: str, out: Path, cfg: Config | None = None) -> Path:
    """Synthesize one narration file. Returns the path written.

    Chain: Edge-TTS (best quality, needs network) → Piper (offline neural,
    needs a local .onnx voice) → gTTS (last resort, robotic). The chain
    exists because a silent or robot-voiced video is worse than a slightly
    slower render — but gTTS is never the first choice.
    """
    cfg = cfg or Config()
    voice = cfg.get("voice")
    out.parent.mkdir(parents=True, exist_ok=True)

    if voice.startswith("piper:"):
        model = voice.split("piper:", 1)[1]
        _piper_tts(text, out, model)
        return out

    async def _bounded():
        # Edge-TTS has no internal timeout; never let one scene hang the job.
        await asyncio.wait_for(_edge_tts(text, out, voice,
                                         cfg.get("voice_rate", "+0%")),
                               timeout=25)
    try:
        asyncio.run(_bounded())
    except ImportError as exc:
        raise RuntimeError(
            "edge-tts is not installed. Run: pip install 'reelforge[voice]'."
        ) from exc
    except Exception:
        # Edge-TTS unreachable (restricted networks, etc.) → best local
        # Piper neural voice for this language, else gTTS fallback.
        piper_model = _resolve_piper_model(voice, cfg)
        if piper_model:
            _piper_tts(text, out, piper_model)
        else:
            _gtts_fallback(text, out, voice)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"No TTS engine produced audio for: {text[:60]!r}")
    return out


def _gtts_fallback(text: str, out: Path, voice: str) -> None:
    """Google Translate TTS fallback — free, no key, works almost everywhere."""
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RuntimeError(
            "Edge-TTS failed and gtts is not installed. "
            "Run: pip install gtts (or check your network)."
        ) from exc
    lang = voice.split("-")[0] if "-" in voice else "en"
    gTTS(text=text, lang=lang if lang in ("en", "ur", "hi", "ar", "es", "fr") else "en",
         slow=False).save(str(out))


def _piper_tts(text: str, out: Path, model: str) -> None:
    """Offline synthesis via a local Piper model.

    Uses the piper-tts Python package (``python -m piper``); falls back to a
    `piper` binary on PATH if the module is missing.
    """
    import sys as _sys

    wav = out.with_suffix(".wav")
    try:
        import piper  # noqa: F401 — proves the module is installed
        cmd = [_sys.executable, "-m", "piper"]
    except ImportError:
        cmd = ["piper"]
    proc = subprocess.run(
        cmd + ["--model", model, "--output_file", str(wav)],
        input=text.encode(), capture_output=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper failed: {proc.stderr.decode()[:300]}")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
         "-codec:a", "libmp3lame", "-q:a", "4", str(out)],
        check=True,
    )
    wav.unlink(missing_ok=True)


def synthesize_plan(plan: EditPlan, workdir: Path,
                    cfg: Config | None = None) -> list[Path]:
    """Voice every scene in order. Returns per-scene audio paths."""
    cfg = cfg or Config()
    audio_dir = workdir / "audio"
    paths = []
    for scene in plan.scenes:
        out = audio_dir / f"scene_{scene.id:02d}.mp3"
        synthesize_scene(scene.voiceover, out, cfg)
        paths.append(out)
    return paths


def concat_audio(parts: list[Path], out: Path) -> Path:
    """Concatenate scene MP3s into one track (re-encoded, gapless-ish)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.parent / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-codec:a", "libmp3lame", "-q:a", "3", str(out)],
        check=True,
    )
    lst.unlink(missing_ok=True)
    return out


def probe_duration(path: Path) -> float:
    """Media duration in seconds via ffprobe."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(proc.stdout.strip())
