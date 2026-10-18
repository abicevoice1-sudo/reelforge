"""Tests for the Agnes AI video provider routing."""
from pathlib import Path
from unittest.mock import patch

from shortsmash.config import Config


def test_agnes_provider_routing(tmp_path: Path):
    """visual_provider=agnes routes to agnes.generate, not stock."""
    from shortsmash import visual
    out = tmp_path / "scene.mp4"
    cfg = Config(overrides={"visual_provider": "agnes"})
    with patch("shortsmash.agnes.generate", return_value=out) as m:
        result = visual.fetch("cinematic espresso macro", out, cfg, duration=4.0)
    assert result == out
    m.assert_called_once()
    # Prompt and duration pass through; aspect defaults to vertical.
    assert m.call_args[0][0] == "cinematic espresso macro"
    assert m.call_args[1]["duration"] == 4.0


def test_stock_still_default(tmp_path: Path):
    """Default provider is still stock (no regression)."""
    from shortsmash import visual
    cfg = Config(overrides={})
    assert cfg.get("visual_provider", "stock") == "stock"
    with patch("shortsmash.stock.fetch_stock") as m:
        visual.fetch("coffee", tmp_path / "x.mp4", cfg)
    m.assert_called_once()
