from pathlib import Path

import pytest

from reelforge.captions import RLM, Word, _is_rtl, build_ass, distribute_words
from reelforge.music import duck_expression, speech_segments
from reelforge.schemas import Scene


def test_distribute_words_even():
    scene = Scene(id=1, voiceover="one two three four", on_screen_text="x",
                  stock_query="y", duration=4.0)
    words = distribute_words(scene, 4.0, 10.0)
    assert len(words) == 4
    assert words[0].start == 10.0 and words[-1].end == 14.0


def test_build_ass_karaoke(tmp_path: Path):
    words = [Word("hello", 0.0, 0.5), Word("world", 0.5, 1.0)]
    out = tmp_path / "c.ass"
    build_ass(words, out, style="karaoke")
    text = out.read_text()
    assert "\\kf" in text  # karaoke timing tags
    assert "hello" in text and "world" in text
    assert "PlayResX: 1080" in text
    assert RLM not in text  # English stays left-to-right


def test_build_ass_rtl_urdu(tmp_path: Path):
    """Urdu captions must carry a right-to-left mark so libass lays them
    out RTL (first spoken word at the right), not LTR like English."""
    words = [Word("نویں", 0.0, 0.5), Word("صدی", 0.5, 1.0)]
    out = tmp_path / "u.ass"
    build_ass(words, out, style="karaoke")
    text = out.read_text()
    assert _is_rtl("نویں صدی")
    assert not _is_rtl("hello world")
    # RLM is the very first content char of the dialogue text,
    # before any karaoke override blocks (a {\fn} font override for
    # Nastaliq may precede it).
    for line in text.splitlines():
        if line.startswith("Dialogue:"):
            payload = line.split(",", 9)[9]
            assert RLM in payload[:40], payload[:40]
            if "نویں" in payload:  # RTL: Nastaliq, not Arial fallback
                assert payload.startswith("{\\fnNoto Nastaliq Urdu\\fs")


def test_build_ass_rtl_no_kf_sweep(tmp_path: Path):
    """RTL karaoke must NOT use \\kf: libass applies kf in visual order,
    which highlights the wrong words for RTL. Instead each word gets its
    own timed event with the current word highlighted."""
    words = [Word("نویں", 0.0, 0.5), Word("صدی", 0.5, 1.0)]
    out = tmp_path / "u.ass"
    build_ass(words, out, style="karaoke")
    text = out.read_text()
    assert "\\kf" not in text
    dialogues = [l for l in text.splitlines() if l.startswith("Dialogue:")]
    assert len(dialogues) == 2
    # First event (0.0-0.5) highlights the first word, second event the second.
    assert "{\\c&H000019FF&}نویں{\\c&H00FFFFFF&}" in dialogues[0]
    assert "{\\c&H000019FF&}صدی{\\c&H00FFFFFF&}" in dialogues[1]
    assert "0:00:00.00,0:00:00.50" in dialogues[0]
    assert "0:00:00.50,0:00:01.00" in dialogues[1]


def test_build_ass_ltr_keeps_kf(tmp_path: Path):
    """English karaoke still uses the \\kf sweep (it works fine LTR)."""
    words = [Word("hello", 0.0, 0.5), Word("world", 0.5, 1.0)]
    out = tmp_path / "e.ass"
    build_ass(words, out, style="karaoke")
    text = out.read_text()
    assert "\\kf" in text
    assert RLM not in text


def test_build_ass_rtl_overlay(tmp_path: Path):
    out = tmp_path / "o.ass"
    build_ass([Word("test", 0.0, 1.0)], out,
              overlays=[{"start": 0.0, "end": 1.0, "text": "تم عادی ہو",
                         "kind": "hook"}])
    text = out.read_text()
    hook = [l for l in text.splitlines() if ",Hook," in l][0]
    payload = hook.split(",", 9)[9]
    assert RLM in payload[:40]
    assert payload.startswith("{\\fnNoto Nastaliq Urdu\\fs")


def test_speech_segments_merge():
    words = [Word("a", 0.0, 0.3), Word("b", 0.4, 0.7), Word("c", 5.0, 5.3)]
    segs = speech_segments(words)
    assert len(segs) == 2  # first two merge (gap 0.1 < 0.4)


def test_duck_expression_shape():
    words = [Word("a", 1.0, 2.0)]
    expr = duck_expression(words, 0.12, 0.04)
    assert "between(t\\,0.85\\,2.15)" in expr
    assert expr.startswith("if(")


def test_duck_expression_valid_ffmpeg():
    """The ducking expression must parse in a real ffmpeg filtergraph.

    Regression test: unescaped commas once made every musically-backed
    render fail at the prepare_music stage.
    """
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    words = [Word("a", 1.0, 2.0), Word("b", 3.0, 3.5)]
    expr = duck_expression(words, 0.12, 0.04)
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         "anullsrc=r=44100:cl=stereo:d=5",
         "-af", f"volume={expr}:eval=frame", "-t", "5",
         "-codec:a", "aac", "-f", "null", "-"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"ffmpeg rejected duck expression: {proc.stderr[:300]}"


def test_local_vision_rejects_wrong_clip():
    """Local CLIP gate: accepts matching footage, rejects confusers.

    Uses real frames captured from actual renders (see /tmp/v3check).
    Skipped when torch/transformers are unavailable.
    """
    import shutil

    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from pathlib import Path as P
    from reelforge import vision_local

    good = P("/tmp/v3check/f2.jpg")   # steaming biryani pot
    bad = P("/tmp/v3check/f22.jpg")   # burger patty
    if not (good.exists() and bad.exists()):
        pytest.skip("calibration frames not present")
    assert vision_local.relevant(good, "steaming biryani pot")[0] is True
    assert vision_local.relevant(bad, "charcoal embers cooking fire")[0] is False


def test_trend_scoring_and_dedupe():
    """Trend ranking: higher engagement wins, duplicates collapse."""
    from reelforge.trends import Trend, NICHE_QUERIES
    assert "food" in NICHE_QUERIES and "ai" in NICHE_QUERIES
    ts = [
        Trend(title="Viral Biryani Recipe", source="Google News", score=50.0),
        Trend(title="viral biryani recipe", source="Google News", score=90.0),
        Trend(title="New Gym Study", source="Google News", score=10.0),
    ]
    seen = {}
    for t in sorted(ts, key=lambda t: -t.score):
        key = t.title.lower()[:60]
        if key not in seen:
            seen[key] = t
    assert len(seen) == 2
    assert seen["viral biryani recipe"].score == 90.0


def test_openai_provider_routing():
    """llm.provider honors a pinned 'openai' provider and _openai posts
    to the configured base_url (OpenRouter/DeepSeek/Ollama all work)."""
    from unittest.mock import patch
    from reelforge import llm
    from reelforge.config import Config
    cfg = Config(overrides={"llm_provider": "openai",
                            "openai_base_url": "http://localhost:11434/v1",
                            "openai_model": "llama3"})
    assert llm.provider(cfg) == "openai"

    captured = {}
    class FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["model"] = json["model"]
        return FakeResp()
    with patch("httpx.post", fake_post):
        out = llm._openai("sys", "hi", cfg, 0.5, False)
    assert out == "hello"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["model"] == "llama3"


def test_visual_provider_routing():
    """visual.fetch uses stock by default, custom when configured."""
    from reelforge import visual
    from reelforge.config import Config
    cfg = Config()
    assert cfg.get("visual_provider", "stock") == "stock"
    # custom without a command must fail loudly, not silently
    cfg = Config(overrides={"visual_provider": "custom"})
    import pytest as _pt
    with _pt.raises(RuntimeError, match="visual_command"):
        visual.fetch("test", __import__("pathlib").Path("/tmp/x.mp4"), cfg)


def test_new_publishers_dry_run():
    """Threads + Bluesky adapters support dry_run without credentials."""
    from pathlib import Path
    from reelforge.publish import publish, ADAPTERS
    from reelforge.config import Config
    assert "threads" in ADAPTERS and "bluesky" in ADAPTERS
    v = Path("/tmp/fake.mp4")
    v.write_bytes(b"x" * 100)
    for p in ("threads", "bluesky"):
        r = publish(p, v, "T", "d", ["#t"], Config(), dry_run=True)
        assert r["platform"] == p and r["dry_run"] is True


def test_web_api_endpoints():
    """Studio web UI: index, projects, stats, trends all respond."""
    from fastapi.testclient import TestClient
    from reelforge.web import app
    c = TestClient(app)
    assert c.get("/").status_code == 200
    assert c.get("/api/projects").status_code == 200
    stats = c.get("/api/stats").json()
    assert stats["platforms"] and len(stats["platforms"]) >= 6
    assert c.post("/api/trends", json={"niche": "ai", "limit": 2}).status_code == 200


def test_linkedin_pinterest_dry_run():
    """LinkedIn + Pinterest adapters dry_run without credentials."""
    from pathlib import Path
    from reelforge.publish import publish, ADAPTERS
    from reelforge.config import Config
    assert len(ADAPTERS) == 10
    v = Path("/tmp/fake.mp4")
    for p in ("linkedin", "pinterest", "facebook", "facebook_page"):
        r = publish(p, v, "T", "d", ["#t"], Config(), dry_run=True)
        assert r["platform"] == p and r["dry_run"] is True


def test_dub_language_map():
    """Dubbing supports 50 language options with native neural voices."""
    from reelforge.voice import DUB_LANGUAGES, SAMPLE_VOICES
    assert len(DUB_LANGUAGES) == 50
    for lang in DUB_LANGUAGES:
        assert SAMPLE_VOICES[lang], f"no voices for {lang}"


def test_analytics_youtube_id():
    """YouTube video ID extraction from Shorts URLs."""
    from reelforge.analytics import _youtube_id
    assert _youtube_id("https://www.youtube.com/shorts/abc123") == "abc123"
    assert _youtube_id("https://youtu.be/xyz789?t=5") == "xyz789"
    assert _youtube_id("https://example.com") is None
