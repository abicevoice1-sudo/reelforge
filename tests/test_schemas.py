import pytest
from pydantic import ValidationError

from reelforge.schemas import AgentJob, EditPlan, Scene
from reelforge.script import fallback_plan


def _scene(**kw):
    base = dict(id=1, voiceover="Hello world", on_screen_text="Hi",
                stock_query="city night", duration=5.0)
    base.update(kw)
    return Scene(**base)


def test_scene_rejects_bad_transition():
    with pytest.raises(ValidationError):
        _scene(transition="spin")


def test_plan_totals_and_cap():
    plan = EditPlan(title="T", hook="H", scenes=[_scene(id=1, duration=10.0),
                                                _scene(id=2, duration=10.0)])
    assert plan.total_duration == 20.0
    plan.validate_runtime(25)
    with pytest.raises(ValueError):
        plan.validate_runtime(15)


def test_hashtags_normalized():
    plan = EditPlan(title="T", hook="H", hashtags=["shorts", "#viral"],
                    scenes=[_scene()])
    assert plan.hashtags == ["#shorts", "#viral"]


def test_fallback_plan_sane():
    plan = fallback_plan("hyderabadi biryani", 30)
    assert 25 <= plan.total_duration <= 35
    assert plan.hook
    assert all(s.stock_query for s in plan.scenes)


def test_agent_job_defaults():
    job = AgentJob(action="create", topic="biryani")
    assert job.duration == 30
    assert "youtube" in job.platforms
