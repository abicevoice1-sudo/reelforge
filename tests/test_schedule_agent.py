from datetime import datetime
from zoneinfo import ZoneInfo

from reelforge import agent
from reelforge.config import Config
from reelforge.schedule import parse_when


def test_parse_when_friday_6pm():
    # Anchor: Wednesday 2026-10-14 12:00 ET → "Friday 6pm" is 2026-10-16 18:00
    dt = parse_when("Friday 6pm", "America/New_York")
    assert dt.tzinfo is not None
    assert dt > datetime.now(ZoneInfo("America/New_York"))
    assert dt.weekday() == 4 and dt.hour == 18


def test_parse_when_past_time_rolls_forward():
    dt = parse_when("2000-01-01 00:00", "America/New_York")
    assert dt > datetime.now(ZoneInfo("America/New_York"))


def test_agent_regex_full():
    cfg = Config()
    job = agent._regex_parse(
        "make a 30s reel about hyderabadi biryani and post it Friday at 6pm", cfg)
    assert job.topic == "hyderabadi biryani"
    assert job.duration == 30
    assert job.schedule_at is not None
    assert "youtube" in job.platforms


def test_agent_regex_platform_filter():
    cfg = Config()
    job = agent._regex_parse("make a 15s video about chai just for youtube", cfg)
    assert job.duration == 15
    assert job.platforms == ["youtube"]
    assert job.schedule_at is None


def test_agent_describe():
    cfg = Config()
    job = agent._regex_parse("draft replies to my comments", cfg)
    assert job.action == "engage"
    assert "approve" in agent.describe(job)
