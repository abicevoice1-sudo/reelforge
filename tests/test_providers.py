"""Tests for the new providers: Veo 3.1, Kling AI (visual), Grok (LLM).

All network calls are mocked — these tests verify routing, auth shapes,
and error messages, never spend a cent.
"""
import base64
import json
from pathlib import Path
from unittest.mock import patch

from shortsmash.config import Config


def test_veo_provider_routing(tmp_path: Path):
    """visual_provider=veo routes to veo.generate, not stock."""
    from shortsmash import visual
    out = tmp_path / "scene.mp4"
    cfg = Config(overrides={"visual_provider": "veo"})
    with patch("shortsmash.veo.generate", return_value=out) as m:
        result = visual.fetch("cinematic espresso macro", out, cfg, duration=4.0)
    assert result == out
    m.assert_called_once()
    assert m.call_args[0][0] == "cinematic espresso macro"


def test_kling_provider_routing(tmp_path: Path):
    """visual_provider=kling routes to kling.generate, not stock."""
    from shortsmash import visual
    out = tmp_path / "scene.mp4"
    cfg = Config(overrides={"visual_provider": "kling"})
    with patch("shortsmash.kling.generate", return_value=out) as m:
        result = visual.fetch("neon city rain", out, cfg, duration=5.0)
    assert result == out
    m.assert_called_once()


def test_veo_missing_key_raises_helpful(monkeypatch):
    """No GEMINI_API_KEY -> clear error telling the user what to do."""
    from shortsmash import veo
    # Exercise the non-VM path (env var), not the Secure Vault surrogate.
    monkeypatch.setattr(veo, "add_surrogate_to_request", None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cfg = Config(overrides={"visual_provider": "veo"})
    try:
        veo._request("https://x", None, cfg)
        raise AssertionError("should have raised")
    except veo.VeoError as e:
        assert "GEMINI_API_KEY" in str(e)


def test_kling_missing_keys_raise_helpful(monkeypatch):
    from shortsmash import kling
    monkeypatch.delenv("KLING_ACCESS_KEY", raising=False)
    monkeypatch.delenv("KLING_SECRET_KEY", raising=False)
    cfg = Config(overrides={"visual_provider": "kling"})
    try:
        kling._creds(cfg)
        raise AssertionError("should have raised")
    except kling.KlingError as e:
        assert "KLING_ACCESS_KEY" in str(e)


def test_kling_jwt_shape():
    """The hand-rolled JWT has 3 parts and the right claims."""
    from shortsmash import kling
    token = kling._jwt("my-access", "my-secret")
    parts = token.split(".")
    assert len(parts) == 3
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    assert payload["iss"] == "my-access"
    assert payload["exp"] - payload["nbf"] == 1805  # 1800 + 5 skew


def test_grok_provider_selected(monkeypatch):
    """XAI_API_KEY present (and nothing higher-priority) -> grok."""
    from shortsmash import llm
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    cfg = Config(overrides={"llm_provider": "auto"})
    with patch.object(llm, "_connector_available", return_value=False), \
         patch.object(llm, "_gemini_connector_available", return_value=False):
        assert llm.provider(cfg) == "grok"


def test_grok_pinned():
    from shortsmash import llm
    cfg = Config(overrides={"llm_provider": "grok"})
    assert llm.provider(cfg) == "grok"


def test_grok_call_shape(monkeypatch):
    """Grok hits api.x.ai with Bearer auth and the configured model."""
    from shortsmash import llm
    monkeypatch.setenv("XAI_API_KEY", "sk-test")
    cfg = Config(overrides={"llm_provider": "grok", "grok_model": "grok-3"})
    captured = {}

    class FakeResp:
        def raise_for_status(self): pass

        def json(self):
            return {"choices": [{"message": {"content": "hello"}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json)
        return FakeResp()

    with patch.object(llm.httpx, "post", side_effect=fake_post):
        out = llm._grok("sys", "hi", cfg, 0.5, False)
    assert out == "hello"
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "grok-3"
