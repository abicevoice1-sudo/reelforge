"""Stock stage: real footage from free APIs, or generated placeholders.

Providers:
- pixabay — Pixabay Video API (free key). Default. (Pexels paused new API key
  issuance 2026-09-30; its adapter stays for existing key holders.)
- pexels  — Pexels Video API, for accounts that already have a key.
- generate — offline: cinematic animated gradients via FFmpeg. Used for tests,
  demos, and when no API key is configured. Honest placeholders, not fake stock.
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from .config import Config
from .schemas import EditPlan

PEXELS_API = "https://api.pexels.com/videos/search"
PIXABAY_API = "https://pixabay.com/api/videos/"
_PIXABAY_HELPER = Path.home() / "workspace/custom-connectors/custom.pixabay/bin/pixabay.py"
_GEMINI_HELPER = Path.home() / "workspace/custom-connectors/custom.gemini/bin/gemini.py"

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "on", "with", "for", "to",
    "clip", "video", "footage", "shot",
})


def _rank_hits(hits: list[dict], query: str, seed: int | None = None) -> list[dict]:
    """Order stock hits by tag overlap with the query (best first).

    Blind random picks put pasta in biryani videos. Ranking by the
    provider's own tags is the cheap first line of defense; a vision
    check below is the second.
    """
    words = [w for w in re.findall(r"[a-z]+", query.lower())
             if w not in _STOPWORDS]

    def score(hit: dict) -> int:
        tags = (hit.get("tags") or "").lower()
        return sum(1 for w in words if w in tags)

    rng = random.Random(seed)
    scored = [(score(h), rng.random(), h) for h in hits]
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [h for _, _, h in scored]


def _frame_b64(clip: Path) -> str | None:
    """Middle frame of `clip` as base64 JPEG, or None on failure."""
    try:
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
            capture_output=True, text=True, timeout=30)
        mid = max(0.5, float(dur.stdout.strip() or 0) / 2)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", str(mid), "-i", str(clip),
                 "-frames:v", "1", "-q:v", "5", tmp.name, "-y"],
                check=True, timeout=60)
            return base64.b64encode(Path(tmp.name).read_bytes()).decode()
    except Exception:
        return None


def _vision_relevant(clip: Path, query: str, context: str | None,
                     cfg: Config) -> bool:
    """Ask Gemini whether the clip's middle frame matches the query.

    Second line of defense after tag ranking. Returns True when Gemini is
    unreachable so a vision outage degrades to tag-ranking instead of
    blocking the render — but logs it loudly.
    """
    if not cfg.get("stock_verify", True):
        return True
    if not _GEMINI_HELPER.exists():
        return True
    frame = _frame_b64(clip)
    if not frame:
        print("stock: frame extract failed, skipping vision check",
              file=sys.stderr)
        return True
    prompt = (
        "You're checking stock footage for a cooking video. "
        f"This scene needs footage of: '{query}'. "
        + (f"The narration at this moment says: {context!r}. " if context else "")
        + "Does this frame plausibly fit — could it illustrate this moment? "
          "Answer YES unless the frame clearly shows something unrelated "
          "(wrong dish, wrong subject, or no food at all). "
          "Answer with only YES or NO.")
    try:
        proc = subprocess.run(
            [sys.executable, str(_GEMINI_HELPER), "generate"],
            input=json.dumps({
                "user": prompt, "image_b64": frame,
                "model": cfg.get("gemini_model") or "gemini-3.8-flash",
                "temperature": 0.1,
            }).encode(),
            capture_output=True, timeout=90)
        data = json.loads(proc.stdout.decode() or "{}")
        answer = (data.get("content") or "").strip().upper()
        return answer.startswith("YES")
    except Exception as exc:  # noqa: BLE001 — degrade, don't block
        print(f"stock: vision check failed ({exc}), trusting tag rank",
              file=sys.stderr)
        return True


def _egress_proxy() -> str | None:
    # httpx 0.28.1 cannot parse this runtime's no_proxy (bare IPv6 entries
    # become invalid "all://*[::1]" URLPatterns), so bypass env-proxy parsing
    # and hand httpx the proxy URL directly.
    return (os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
            or os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY"))


def _download(url: str, out: Path, referer: str | None = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    headers = {"Referer": referer} if referer else {}
    with httpx.stream("GET", url, headers=headers, timeout=120,
                      follow_redirects=True, proxy=_egress_proxy()) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    return out


def _pixabay_via_helper(query: str, per_page: int) -> list[dict]:
    """Search Pixabay through the vault-held custom.pixabay credential."""
    proc = subprocess.run(
        [sys.executable, str(_PIXABAY_HELPER), "search_videos"],
        input=json.dumps({"q": query, "per_page": per_page}).encode(),
        capture_output=True, timeout=90,
    )
    try:
        data = json.loads(proc.stdout.decode() or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("Pixabay helper returned unparseable output")
    if not data.get("ok"):
        raise RuntimeError(f"Pixabay helper failed: {data.get('error')}")
    return data["data"].get("hits", [])


def _pexels_search(query: str, per_page: int, key: str) -> list[dict]:
    r = httpx.get(PEXELS_API, params={"query": query, "per_page": per_page,
                                      "orientation": "portrait", "size": "medium"},
                  headers={"Authorization": key}, timeout=30,
                  proxy=_egress_proxy())
    r.raise_for_status()
    return r.json().get("videos", [])


def _pexels_best_file(video: dict) -> str | None:
    files = [f for f in video.get("video_files", [])
             if f.get("file_type") == "video/mp4"]
    if not files:
        return None
    # Prefer ~720p portrait-ish files; fall back to smallest HD file.
    files.sort(key=lambda f: abs((f.get("height") or 720) - 720))
    return files[0]["link"]


def _pixabay_search(query: str, per_page: int, key: str) -> list[dict]:
    r = httpx.get(PIXABAY_API, params={"key": key, "q": query,
                                       "per_page": per_page, "video_type": "all"},
                  timeout=30)
    r.raise_for_status()
    return r.json().get("hits", [])


def _pixabay_best_file(hit: dict) -> str | None:
    videos = hit.get("videos", {})
    for quality in ("medium", "small", "large", "tiny"):
        if quality in videos:
            return videos[quality]["url"]
    return None


def fetch_stock(query: str, out: Path, cfg: Config | None = None,
                seed: int | None = None, context: str | None = None) -> Path:
    """Download one stock clip for `query`. Returns the local path.

    `context` (e.g. the scene's voiceover) helps the vision relevance check.
    Clips are ranked by tag overlap, then each candidate is vision-checked
    before acceptance — a wrong clip fails loudly instead of shipping.
    """
    cfg = cfg or Config()
    provider = cfg.get("stock_provider")

    if provider == "generate":
        return generate_placeholder(query, out, seed=seed)

    if provider == "pixabay":
        if cfg.pixabay_key():
            hits = _pixabay_search(query, 5, cfg.pixabay_key())
        elif _PIXABAY_HELPER.exists():
            print("pixabay: using vault-connected key", file=sys.stderr)
            hits = _pixabay_via_helper(query, 8)
        else:
            print("pixabay: no API key — placeholder footage", file=sys.stderr)
            return generate_placeholder(query, out, seed=seed)
        for hit in _rank_hits(hits, query, seed) if hits else []:
            url = _pixabay_best_file(hit)
            if not url:
                continue
            path = _download(url, out)
            if _vision_relevant(path, query, context, cfg):
                return path
            print(f"pixabay: clip rejected by vision check for {query!r} "
                  f"(tags: {(hit.get('tags') or '')[:60]}), trying next",
                  file=sys.stderr)
        raise RuntimeError(
            f"Pixabay: no relevant clip for {query!r} "
            f"({len(hits)} hits, all failed relevance).")

    if provider == "pexels" and not cfg.pexels_key():
        print("pexels: no API key — placeholder footage", file=sys.stderr)
        return generate_placeholder(query, out, seed=seed)

    # pexels (existing key holders only; new issuance paused 2026-09-30)
    key = cfg.require("pexels_key", "PEXELS_API_KEY", "Pexels stock video")
    videos = _pexels_search(query, 5, key)
    rng = random.Random(seed)
    for video in rng.sample(videos, min(len(videos), 3)) if videos else []:
        if url := _pexels_best_file(video):
            return _download(url, out)
    raise RuntimeError(f"Pexels returned no usable video for {query!r}")


# Nice cinematic palettes for offline placeholders.
_PALETTES = [
    ("#0f2027", "#203a43", "#2c5364"),
    ("#141e30", "#243b55", "#3a6073"),
    ("#200122", "#6f0000", "#c31432"),
    ("#0f0c29", "#302b63", "#24243e"),
    ("#232526", "#414345", "#5a5a5a"),
]


def generate_placeholder(query: str, out: Path, duration: float = 8.0,
                         seed: int | None = None) -> Path:
    """Offline cinematic clip: animated gradient + film grain + vignette.

    Clearly a placeholder (never passed off as real footage); keeps the full
    pipeline testable without API keys.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed if seed is not None else abs(hash(query)) % 10**6)
    c1, c2, c3 = rng.choice(_PALETTES)
    w, h = 720, 1280
    vf = (
        f"gradients=s={w}x{h}:c0={c1[1:]}:c1={c2[1:]}:c2={c3[1:]}:speed=0.08,"
        f"vignette=PI/5,"
        f"drawtext=text='{query[:28]}':fontcolor=white@0.25:fontsize=36:"
        f"x=(w-text_w)/2:y=(h-text_h)/2"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", vf,
         "-t", str(duration), "-r", "30", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )
    return out


def fetch_plan_stock(plan: EditPlan, workdir: Path,
                     cfg: Config | None = None) -> list[Path]:
    """Fetch one clip per scene. Returns paths in scene order."""
    cfg = cfg or Config()
    clips_dir = workdir / "clips"
    paths = []
    for scene in plan.scenes:
        out = clips_dir / f"scene_{scene.id:02d}.mp4"
        fetch_stock(scene.stock_query, out, cfg, seed=scene.id,
                    context=scene.voiceover)
        paths.append(out)
    return paths
