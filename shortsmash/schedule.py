"""Scheduler: a durable SQLite queue + a worker that publishes on time.

`shortsmash schedule "topic" --at "Friday 6pm" --platforms youtube,tiktok`
parses the natural-language time (timezone-aware), renders the video NOW
(rendering is the slow part), and queues the publish job. `shortsmash worker`
runs the queue (APScheduler, survives restarts — jobs live in SQLite, not RAM).

Job states: queued → done | failed. Retries: 3x with backoff on API errors.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dateutil import parser as dateparser

from .config import QUEUE_DB, Config, ensure_home


def _db() -> sqlite3.Connection:
    ensure_home()
    con = sqlite3.connect(QUEUE_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL, run_at TEXT NOT NULL,
        kind TEXT NOT NULL, payload TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'queued',
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT, finished_at TEXT)""")
    con.commit()
    return con


_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday",
             "friday", "saturday", "sunday")


def parse_when(text: str, tz: str) -> datetime:
    """Parse 'Friday 6pm', 'in 2 hours', '2026-10-20 18:00' → aware datetime.

    Bare times that already passed today roll to tomorrow; a named weekday
    that already passed rolls a full week forward (so "Friday" stays Friday).
    """
    from datetime import timedelta

    zone = ZoneInfo(tz)
    now = datetime.now(zone)
    lowered = text.strip().lower()

    # relative phrases dateutil can't parse: "in 2 hours", "in 30 minutes"
    m = re.match(r"in\s+(\d+)\s*(hour|hr|minute|min|day)s?$", lowered)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"hour": timedelta(hours=n), "hr": timedelta(hours=n),
                 "minute": timedelta(minutes=n), "min": timedelta(minutes=n),
                 "day": timedelta(days=n)}[unit]
        return now + delta

    dt = dateparser.parse(text, default=now.replace(hour=9, minute=0,
                                                    second=0, microsecond=0))
    if dt is None:
        raise ValueError(f"Could not understand time: {text!r}. "
                         'Try e.g. "Friday 6pm", "tomorrow 9am", "in 2 hours".')
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone)

    step = timedelta(days=7) if any(d in lowered for d in _WEEKDAYS) \
        else timedelta(days=1)
    if dt <= now:
        # jump whole periods forward in O(1) — works for ancient dates too
        dt += ((now - dt) // step + 1) * step
    return dt


def enqueue(run_at: datetime, kind: str, payload: dict) -> int:
    con = _db()
    cur = con.execute(
        "INSERT INTO jobs(created_at, run_at, kind, payload) VALUES(?,?,?,?)",
        (datetime.now().isoformat(), run_at.isoformat(), kind,
         json.dumps(payload)))
    con.commit()
    job_id = cur.lastrowid
    con.close()
    return job_id


def list_jobs(state: str | None = None) -> list[dict]:
    con = _db()
    q = "SELECT id, created_at, run_at, kind, payload, state, attempts, last_error FROM jobs"
    if state:
        q += " WHERE state=?"
        rows = con.execute(q + " ORDER BY run_at", (state,)).fetchall()
    else:
        rows = con.execute(q + " ORDER BY run_at").fetchall()
    con.close()
    return [dict(zip(["id", "created_at", "run_at", "kind", "payload",
                      "state", "attempts", "last_error"], r)) for r in rows]


def cancel(job_id: int) -> bool:
    con = _db()
    cur = con.execute("UPDATE jobs SET state='cancelled' WHERE id=? AND state='queued'",
                      (job_id,))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok


def _run_auto_generate(payload: dict, cfg) -> None:
    """Generate a video from a niche trend, dub if needed, queue publishing."""
    from datetime import datetime, timedelta
    from . import api_limits as lim, pipeline, trends as tmod, dub as dubmod

    niche = payload.get("niche", "general")
    language = payload.get("language", "en")
    platforms = payload.get("platforms", [])
    post_time = payload.get("post_time", "18:00")

    # Respect daily API limits — skip quietly if quota is exhausted.
    if lim.videos_possible_today() < 1:
        print("[worker] auto_generate skipped: API quota exhausted today")
        return

    harvested = tmod.harvest(niche, 1)
    topic = tmod.to_video_prompt(harvested[0], niche) if harvested else f"{niche} facts"
    workdir = pipeline.create_project(topic, 30, cfg)
    slug = workdir.name
    lim.record("gemini", 2)
    lim.record("pixabay", 3)

    if language != "en":
        slug = dubmod.dub_project(slug, language, cfg).name

    if platforms:
        hh, mm = (post_time.split(":") + ["0"])[:2]
        run_at = datetime.now().replace(hour=int(hh), minute=int(mm),
                                        second=0, microsecond=0)
        if run_at <= datetime.now():
            run_at += timedelta(days=1)
        enqueue(run_at, "publish", {"slug": slug, "platforms": platforms})
        print(f"[worker] auto video {slug} → publish at {run_at:%H:%M}")
    else:
        print(f"[worker] auto video {slug} ready (no platforms set)")


def run_worker(poll_seconds: int = 30, once: bool = False,
               cfg: Config | None = None) -> None:
    """Publish due jobs. Runs forever unless once=True."""
    from . import pipeline  # deferred: heavy imports stay out of CLI startup

    cfg = cfg or Config()
    while True:
        con = _db()
        now = datetime.now().isoformat()
        due = con.execute(
            "SELECT id, kind, payload, attempts FROM jobs "
            "WHERE state='queued' AND run_at <= ? ORDER BY run_at LIMIT 5",
            (now,)).fetchall()
        for job_id, kind, payload, attempts in due:
            payload = json.loads(payload)
            try:
                if kind == "publish":
                    pipeline.publish_project(payload["slug"],
                                             payload["platforms"], cfg,
                                             dry_run=payload.get("dry_run", False))
                elif kind == "auto_generate":
                    _run_auto_generate(payload, cfg)
                else:
                    raise ValueError(f"unknown job kind {kind!r}")
                con.execute("UPDATE jobs SET state='done', finished_at=? WHERE id=?",
                            (datetime.now().isoformat(), job_id))
                print(f"[worker] job {job_id} done")
            except Exception as exc:  # noqa: BLE001 — jobs must never kill the worker
                err = f"{type(exc).__name__}: {exc}"[:500]
                if attempts + 1 >= 3:
                    con.execute("UPDATE jobs SET state='failed', last_error=?, "
                                "attempts=attempts+1 WHERE id=?", (err, job_id))
                    print(f"[worker] job {job_id} FAILED: {err}")
                else:
                    con.execute("UPDATE jobs SET attempts=attempts+1, last_error=?, "
                                "run_at=? WHERE id=?",
                                (err, datetime.now().isoformat(), job_id))
                    print(f"[worker] job {job_id} retry {attempts + 1}: {err}")
            con.commit()
        con.close()
        if once:
            break
        time.sleep(poll_seconds)
