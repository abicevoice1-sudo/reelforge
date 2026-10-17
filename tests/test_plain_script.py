"""Tests for the plain-text script format (reasoning-LLM path)."""

from reelforge.plain_script import parse_plan

SAMPLE = """TITLE: Biryani Like You've Never Seen
HOOK: Hyderabad's biryani has a 400-year-old secret.
SCENES:
1. [7s] SAY: In Hyderabad, biryani isn't food, it's an emotion. | TEXT: Not just food | SHOW: hyderabadi biryani handi
2. [8s] SAY: The dum pukht method seals every grain with saffron steam. | TEXT: Sealed with steam | SHOW: dum biryani cooking pot
3. [7s] SAY: One spoonful and you taste four centuries of Nizam kitchens. | TEXT: 400 years of flavor | SHOW: biryani rice closeup
4. [8s] SAY: No city on earth does it like Hyderabad. | TEXT: Hyderabad wins | SHOW: hyderabad old city food
CTA: Follow for India's best food stories
HASHTAGS: #biryani #hyderabad #foodie #indianfood #shorts
"""


def test_parse_plan_fields():
    plan = parse_plan(SAMPLE, "Hyderabadi biryani", 30)
    assert plan.title == "Biryani Like You've Never Seen"
    assert "400-year-old" in plan.hook
    assert len(plan.scenes) == 4
    assert plan.scenes[0].voiceover.startswith("In Hyderabad")
    assert plan.scenes[0].on_screen_text == "Not just food"
    assert plan.scenes[0].stock_query == "hyderabadi biryani handi"
    assert plan.cta.startswith("Follow for")
    assert "#biryani" in plan.hashtags


def test_parse_plan_rescales_duration():
    plan = parse_plan(SAMPLE, "Hyderabadi biryani", 30)
    total = sum(s.duration for s in plan.scenes)
    assert abs(total - 30) < 1.0


def test_parse_plan_rejects_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_plan("hello world, no scenes here", "topic", 30)


def test_rank_hits_prefers_tag_overlap():
    from reelforge.stock import _rank_hits
    hits = [
        {"tags": "pasta, italian, food", "id": 1},
        {"tags": "biryani, rice, indian food", "id": 2},
        {"tags": "eggplant, garden", "id": 3},
    ]
    ranked = _rank_hits(hits, "hyderabadi biryani rice", seed=1)
    assert ranked[0]["id"] == 2  # most tag overlap wins
    assert {h["id"] for h in ranked[1:]} == {1, 3}  # zero-overlap ties after


def test_rank_hits_deterministic_with_seed():
    from reelforge.stock import _rank_hits
    hits = [{"tags": "biryani rice", "id": i} for i in range(5)]
    a = [h["id"] for h in _rank_hits(hits, "biryani", seed=7)]
    b = [h["id"] for h in _rank_hits(hits, "biryani", seed=7)]
    assert a == b
