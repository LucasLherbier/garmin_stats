"""Single Garmin login for weekly CI: activities, summaries, daily wellness."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import utils.pipeline.garmin_cookies as garmin_cookies
from utils.pipeline.daily_wellness.process import process_daily_wellness
from utils.pipeline.extract_weekly_activities import process_date_range
from utils.pipeline.garmintokens_persist import persist_refreshed_garmintokens

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_weekly_sync(
    start_date: str, token_blob: str | None = None
) -> tuple[int, str | None]:
    """Run the full weekly sync (activities, summaries, daily wellness).

    token_blob: explicit DI token blob (in-app vault path). When None, falls
    back to garmin_cookies.main() (env-based, CI path).
    Returns (exit_code, refreshed_token_blob or None).
    """
    if token_blob:
        client = garmin_cookies.login_with_blob(token_blob)
    else:
        client = garmin_cookies.main()
    if not client:
        logger.error("Failed to connect to Garmin Connect.")
        return 1, None

    process_date_range(start_date, client=client)

    summaries_cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "backfill_workout_summaries.py"),
        "--start_date",
        start_date,
    ]
    logger.info("Running: %s", " ".join(summaries_cmd))
    child_env = os.environ.copy()
    child_env.setdefault("OPENBLAS_NUM_THREADS", "1")
    child_env.setdefault("OMP_NUM_THREADS", "1")
    subprocess.run(summaries_cmd, check=True, cwd=_ROOT, env=child_env)

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    logger.info("Daily wellness catch-up: %s to %s", last_week, yesterday)
    wellness_df = process_daily_wellness(client, last_week, yesterday)
    if wellness_df.empty:
        logger.info("Daily wellness catch-up: nothing fetched.")
    else:
        logger.info("Daily wellness catch-up: fetched %s day(s) (see logs for BigQuery upsert).", len(wellness_df))

    refreshed = garmin_cookies.export_token_blob(client)
    if not refreshed:
        logger.warning("Could not export Garmin tokens after sync.")
    return 0, refreshed


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Garmin sync with one login session.")
    parser.add_argument("--start_date", required=True, help="Activity extract start (YYYY-MM-DD).")
    args = parser.parse_args()

    code, refreshed = run_weekly_sync(args.start_date)
    if code == 0 and refreshed:
        persist_refreshed_garmintokens(refreshed)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
