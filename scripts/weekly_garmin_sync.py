"""Single Garmin login for weekly CI: activities, summaries, daily wellness."""

from __future__ import annotations

import argparse
import logging
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

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Weekly Garmin sync with one login session.")
    parser.add_argument("--start_date", required=True, help="Activity extract start (YYYY-MM-DD).")
    args = parser.parse_args()

    client = garmin_cookies.main()
    if not client:
        logger.error("Failed to connect to Garmin Connect.")
        return 1

    process_date_range(args.start_date, client=client)

    summaries_cmd = [
        sys.executable,
        str(_ROOT / "scripts" / "backfill_workout_summaries.py"),
        "--start_date",
        args.start_date,
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
