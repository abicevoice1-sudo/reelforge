"""Music stage: royalty-free bed track with smart ducking.

Source priority:
1. `music_file` in config — explicit track.
2. `~/.reelforge/music/` — drop royalty-free MP3s here; one is picked by mood
   keyword in the filename (e.g. `upbeat-summer.mp3`), else at random.
3. `music_url` in config — downloaded once and cached.

Ducking: the track is dipped under every speech segment (from caption word
timings) via an FFmpeg `volume` expression, so narration always sits on top.
"""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

import httpx

from .captions import Word
from .config import HOME, Config


def pick_track(mood: str, cfg: Config | None = None) -> Path | None:
    cfg = cfg or Config()
    if cfg.get("music_file"):
        p = Path(cfg.get("music_file")).expanduser()
        return p if p.exists() else None
    lib = HOME / "music"
    if not lib.exists():
        return None
    tracks = sorted(lib.glob("*.mp3")) + sorted(lib.glob("*.wav")) \
        + sorted(lib.glob("*.m4a"))
    if not tracks:
        return None
    mood_hits = [t for t in tracks if mood.lower() in t.stem.lower()]
    return random.choice(mood_hits or tracks)


def fetch_url(url: str, cache: Path) -> Path:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return cache
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with open(cache, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    return cache


def speech_segments(words: list[Word], pad: float = 0.15,
                    merge_gap: float = 0.4) -> list[tuple[float, float]]:
    """Merge word timings into (start, end) speech segments."""
    segs: list[tuple[float, float]] = []
    for w in words:
        s, e = max(0.0, w.start - pad), w.end + pad
        if segs and s - segs[-1][1] <= merge_gap:
            segs[-1] = (segs[-1][0], e)
        else:
            segs.append((s, e))
    return segs


def duck_expression(words: list[Word], bed: float, ducked: float) -> str:
    """FFmpeg volume expression: `ducked` level during speech, `bed` otherwise."""
    conds = "+".join(f"between(t,{s:.2f},{e:.2f})" for s, e in speech_segments(words))
    if not conds:
        return str(bed)
    return f"if({conds},{ducked:.3f},{bed:.3f})"


def prepare_music(track: Path, duration: float, words: list[Word], out: Path,
                  cfg: Config | None = None) -> Path:
    """Loop/trim track to `duration`, apply ducking. Returns processed track."""
    cfg = cfg or Config()
    out.parent.mkdir(parents=True, exist_ok=True)
    bed = float(cfg.get("music_volume"))
    expr = duck_expression(words, bed, bed * 0.35) if cfg.get("music_duck") else str(bed)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(track),
         "-t", str(duration),
         "-af", f"volume={expr}:eval=frame,afade=t=in:st=0:d=1,afade=t=out:st={max(0, duration - 2):.2f}:d=2",
         "-codec:a", "aac", "-b:a", "128k", str(out)],
        check=True,
    )
    return out
