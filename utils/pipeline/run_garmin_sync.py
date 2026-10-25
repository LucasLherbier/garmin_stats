"""Full Garmin pipeline run (activities, summaries, wellness) — shared by CLI and API."""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from utils.pipeline.daily_wellness.process import process_daily_wellness
from utils.pipeline.extract_weekly_activities import process_date_range
from utils.pipeline.garmin_client import get_garmin_client

logger = logging.getLogger(__name__)
_ROOT = Path(__file__).resolve().parents[2]


def sync_start_date() -> str:
    """Same window as the GitHub workflow: 14 days ago (Monday alignment in process_date_range)."""
    return (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")


def run_garmin_sync(start_date: str | None = None) -> None:
    start_date = start_date or sync_start_date()
    client = get_garmin_client()
    if not client:
        raise RuntimeError(
            "Garmin client unavailable. Set GARMIN_PERSONAL_API_KEY or GARMIN_SOURCE=legacy."
        )

    process_date_range(start_date, client=client)

    summaries_cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "backfill_workout_summaries.py"),
        "--start_date",
        start_date,
    ]
    logger.info("Running: %s", " ".join(summaries_cmd))
    subprocess.run(summaries_cmd, check=True, cwd=_ROOT)

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    logger.info("Daily wellness catch-up: %s to %s", last_week, yesterday)
    wellness_df = process_daily_wellness(client, last_week, yesterday)
    if wellness_df.empty:
        logger.info("Daily wellness catch-up: nothing fetched.")
    else:
        logger.info("Daily wellness catch-up: upserted %s day(s).", len(wellness_df))
