"""Edit stage: the FFmpeg render pipeline.

Per scene: stock clip is reframed to the target aspect ratio, trimmed to the scene
length (+ transition overlap), and chained with xfade transitions. Voiceovers
concatenate gaplessly; the music bed is ducked under speech; karaoke captions
are burned in; hook + CTA text overlays finish the viral look.

Output: H.264 + AAC, yuv420p, faststart — accepted everywhere as-is.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .captions import Word
from .config import Config
from .music import prepare_music
from .schemas import EditPlan
from .voice import probe_duration

# Top 5 most common video aspect ratios in the world.
ASPECT_RATIOS = {
    "9:16": {"label": "9:16 Vertical", "desc": "TikTok, Reels, Shorts", "w": 1080, "h": 1920},
    "16:9": {"label": "16:9 Widescreen", "desc": "YouTube, TV", "w": 1920, "h": 1080},
    "1:1": {"label": "1:1 Square", "desc": "Instagram feed", "w": 1080, "h": 1080},
    "4:5": {"label": "4:5 Portrait", "desc": "Instagram portrait", "w": 1080, "h": 1350},
    "21:9": {"label": "21:9 Ultrawide", "desc": "Cinematic", "w": 2560, "h": 1080},
}

FPS = 30

_XFADE = {"cut": ("fade", 0.04), "fade": ("fade", 0.5),
          "slide": ("slideleft", 0.5), "zoom": ("fade", 0.04)}

def _esc_filter_path(p: Path) -> str:
    # ass/subtitles filters split on ':' — escape it.
    return str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render(plan: EditPlan, clips: list[Path], voiceovers: list[Path],
           captions_ass: Path, words: list[Word], workdir: Path,
           music_track: Path | None = None,
           cfg: Config | None = None) -> Path:
    """Render the final MP4 at the configured aspect ratio. Returns the output path."""
    cfg = cfg or Config()
    n = len(plan.scenes)
    assert len(clips) == n and len(voiceovers) == n

    durs = [probe_duration(a) for a in voiceovers]
    total = sum(durs)

    # Transition between scene i and i+1 comes from scene i's `transition`.
    xfades = [_XFADE.get(plan.scenes[i].transition, _XFADE["cut"]) for i in range(n - 1)]

    cmd: list[str] = ["ffmpeg", "-y", "-v", "error"]
    for i in range(n):
        cmd += ["-i", str(clips[i]), "-i", str(voiceovers[i])]
    if music_track:
        music_proc = workdir / "music_ducked.m4a"
        prepare_music(music_track, total, words, music_proc, cfg)
        cmd += ["-i", str(music_proc)]
        music_idx = 2 * n
    else:
        music_idx = -1

    fc: list[str] = []

    # --- per-scene video prep: trim (+xfade overlap), reframe to target ratio ---
    # Cinematic treatment (config `cinematic`, default on): a slow Ken Burns
    # push-in on every clip plus a subtle film grade. This is the cheapest
    # way to make stock footage feel directed instead of slideshow-flat.
    cinematic = cfg.get("cinematic", True)
    W = cfg.get("width", 1080)
    H = cfg.get("height", 1920)
    for i, scene in enumerate(plan.scenes):
        vi = 2 * i
        d = durs[i] + (xfades[i][1] if i < n - 1 else 0.0)
        zoom = scene.transition == "zoom"
        sw, sh = (int(W * 1.15), int(H * 1.15)) if zoom else (W, H)
        prep = (f"[{vi}:v]trim=0:{d:.2f},setpts=PTS-STARTPTS,"
                f"scale={sw}:{sh}:force_original_aspect_ratio=increase,")
        if cinematic and not zoom:
            # Gentle 6% push-in across the clip, anchored center.
            frames = max(1, int(d * FPS))
            prep += (f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':"
                     f"y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},")
        else:
            prep += f"crop={W}:{H},"
        if cinematic:
            prep += "eq=contrast=1.06:saturation=1.12:brightness=0.01,"
        prep += f"fps={FPS}[v{i}]"
        fc.append(prep)
        fc.append(f"[{2 * i + 1}:a]atrim=0:{durs[i]:.2f},asetpts=PTS-STARTPTS[a{i}]")

    # --- xfade chain (video) ---
    seg_lens = [durs[i] + (xfades[i][1] if i < n - 1 else 0.0) for i in range(n)]
    if n == 1:
        last_v = "v0"
    else:
        cur, acc = "v0", seg_lens[0]
        for k in range(n - 1):
            name, fd = xfades[k]
            offset = acc - fd
            out = f"x{k}"
            fc.append(f"[{cur}][v{k + 1}]xfade=transition={name}:duration={fd:.2f}:"
                      f"offset={offset:.2f}[{out}]")
            cur = out
            acc = acc + seg_lens[k + 1] - fd
        last_v = cur

    # --- voiceover concat, music mix ---
    fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[voice]")
    if music_idx >= 0:
        fc.append(f"[voice][{music_idx}:a]amix=inputs=2:duration=first:"
                  f"dropout_transition=0:normalize=0[aout]")
    else:
        fc.append("[voice]anull[aout]")

    # --- captions + hook/CTA overlays (all via libass; see captions.py) ---
    vchain = f"[{last_v}]ass={_esc_filter_path(captions_ass)}[vout]"
    fc.append(vchain)

    out = workdir / "final.mp4"
    cmd += ["-filter_complex", ";".join(fc),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-maxrate", "16M", "-bufsize", "32M",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-movflags", "+faststart", "-shortest", str(out)]
    subprocess.run(cmd, check=True)
    if not out.exists():
        raise RuntimeError("FFmpeg render failed — no output file produced.")
    _assert_audible(out)
    return out


def _assert_audible(path: Path, floor_db: float = -45.0) -> None:
    """Refuse to ship a silent video. A render with no (or dead) audio is a
    failed render, not a finished one."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-map", "0:a",
         "-af", "volumedetect", "-f", "null", "/dev/null"],
        capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", proc.stderr)
    if not m:
        raise RuntimeError(
            "Rendered video has no audio stream — refusing to ship it silent.")
    level = float(m.group(1))
    if level < floor_db:
        raise RuntimeError(
            f"Rendered audio is effectively silent (mean {level} dB) — "
            "refusing to ship it.")


def render_quiet_check() -> None:
    """Fail fast if ffmpeg/ffprobe or libass are missing."""
    for bin_ in ("ffmpeg", "ffprobe"):
        subprocess.run([bin_, "-version"], capture_output=True, check=True)
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-h", "filter=ass"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("This FFmpeg build lacks libass — captions can't burn in. "
                           "Install a full FFmpeg build (e.g. apt install ffmpeg).")
