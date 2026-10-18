"""Tests for manual video posts: probe/validate/stage/publish_video."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from shortsmash import pipeline

DEMO = Path(__file__).resolve().parent.parent / "demo" / "coffee-v1.mp4"

needs_demo = pytest.mark.skipif(not DEMO.exists(), reason="demo video missing")


@needs_demo
def test_probe_video():
    info = pipeline.probe_video(DEMO)
    assert info["width"] == 1080
    assert info["height"] == 1920
    assert info["duration"] > 40
    assert info["vertical"] is True


def test_probe_missing():
    with pytest.raises(FileNotFoundError):
        pipeline.probe_video(Path("/nonexistent/x.mp4"))


def test_probe_bad_suffix(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported"):
        pipeline.probe_video(f)


@needs_demo
def test_validate_video_warnings():
    # 49s vertical video: no warnings for shorts platforms
    info = pipeline.validate_video(DEMO, ["youtube", "tiktok"])
    assert info["ok"] is True
    assert info["warnings"] == []
    # unknown platform: no crash, no warnings
    info = pipeline.validate_video(DEMO, ["myspace"])
    assert info["warnings"] == []


@needs_demo
def test_validate_landscape_warning(tmp_path):
    pytest.importorskip("ffmpeg")  # noqa - just ensure ffmpeg exists
    import subprocess

    land = tmp_path / "land.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "color=c=blue:s=1920x1080:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(land)],
                   check=True)
    info = pipeline.validate_video(land, ["youtube"])
    assert any("landscape" in w for w in info["warnings"])


@needs_demo
def test_stage_upload(tmp_path, monkeypatch):
    from shortsmash import config

    monkeypatch.setattr(config, "UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "HOME", tmp_path)
    dest = pipeline.stage_upload(DEMO)
    assert dest.exists()
    assert dest.parent == tmp_path / "uploads"
    assert dest.suffix == ".mp4"


def test_publish_video_unknown_platform(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"fake")
    with patch.object(pipeline, "probe_video", return_value={}):
        with pytest.raises(ValueError, match="Unknown platforms"):
            pipeline.publish_video(f, "t", "d", [], ["myspace"])


def test_publish_video_calls_adapters(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"fake")
    calls = []

    def fake_adapter(platform, video, title, desc, tags, cfg,
                     dry_run=False, **kw):
        calls.append((platform, str(video), title))
        return {"platform": platform, "dry_run": dry_run}

    with patch.object(pipeline, "probe_video", return_value={}), \
         patch.object(pipeline, "publish_adapter", side_effect=fake_adapter):
        res = pipeline.publish_video(f, "My Title", "desc", ["#a"],
                                     ["youtube", "tiktok"], dry_run=True)
    assert set(res) == {"youtube", "tiktok"}
    assert calls[0][1] == str(f)
    assert calls[0][2] == "My Title"
    assert res["youtube"]["dry_run"] is True


def test_parse_when_tomorrow():
    from shortsmash.schedule import parse_when

    dt = parse_when("tomorrow 9am", "America/New_York")
    assert dt.hour == 9
    assert (dt.date() - parse_when("today 9am", "America/New_York").date()).days == 1
