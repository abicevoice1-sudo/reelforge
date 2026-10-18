#!/usr/bin/env python3
"""Hourly Agnes queue probe: try one generation, notify only on success.

The free Agnes video queue has been full for extended stretches. This
probes once per hour; on the first successful generation it verifies the
mp4 and reports back. Quiet otherwise.
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/hatch/workspace/reelforge")
sys.path.insert(0, "/home/hatch/workspace/reelforge/.venv/lib/python3.12/site-packages")

from reelforge import agnes
from reelforge.config import Config

out = Path("/tmp/agnes_probe.mp4")
try:
    # Single attempt, no backoff: the cron itself is the retry loop.
    import reelforge.agnes as ag
    orig_generate = ag.generate
    def one_shot(prompt, out, cfg, duration=4.0, aspect="9:16"):
        create = ag._call(f"{ag.BASE}/v1/videos", {
            "model": ag.MODEL, "mode": "text",
            "prompt": f"Cinematic vertical video, no on-screen text, no watermark: {prompt}",
            "size": "720P", "aspect_ratio": aspect,
            "seconds": str(min(12, max(4, int(round(duration))))), "n": 1,
        })
        video_id = create.get("video_id") or create.get("id") or create.get("task_id")
        if not video_id:
            print("PROBE: no video_id")
            return None
        import time
        for _ in range(100):
            time.sleep(6)
            st = ag._call(f"{ag.BASE}/agnesapi?video_id={video_id}&model_name={ag.MODEL}")
            status = str(st.get("status", "")).lower()
            if status == "completed":
                url = ((st.get("metadata") or {}).get("url") or st.get("url")
                       or st.get("video_url"))
                if url:
                    ag._download(url, out)
                    return out
                print("PROBE: completed but no URL")
                return None
            if status in ("failed", "error"):
                print(f"PROBE: generation failed: {str(st)[:150]}")
                return None
        print("PROBE: poll timed out")
        return None
    result = one_shot(
        "espresso pouring into a glass cup, macro slow motion, warm dramatic lighting",
        out, Config(), duration=5.0)
    if result and result.stat().st_size > 100000:
        print(f"PROBE SUCCESS: {result} {result.stat().st_size} bytes")
    else:
        print("PROBE: no video yet")
except ag.AgnesError as e:
    print(f"PROBE: {e}")
