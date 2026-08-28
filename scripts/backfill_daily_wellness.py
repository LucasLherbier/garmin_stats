"""Backfill daily_wellness (sleep, HRV, activity rollups) from Garmin Connect."""

from __future__ import annotations

import argparse
import logging
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

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SINCE = "2022-05-01"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill daily_wellness from Garmin Connect.")
    parser.add_argument(
        "--since",
        help="Start date (YYYY-MM-DD). Default: 7 days ago.",
    )
    parser.add_argument(
        "--until",
        help="End date (YYYY-MM-DD). Default: yesterday.",
    )
    parser.add_argument(
        "--full-backfill",
        action="store_true",
        help=f"Shorthand for --since {DEFAULT_SINCE} through yesterday.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print summary without uploading to BigQuery.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds between per-day Garmin calls (default: 0.5 weekly, 1.0 full backfill).",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=31,
        help="Upload after each chunk of N days (default: 31).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip days already stored with ok/partial status.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch days even if they already exist in BigQuery.",
    )
    parser.add_argument(
        "--include-stress",
        action="store_true",
        help="Also fetch daily stress (extra API call per day).",
    )
    args = parser.parse_args()

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    if args.full_backfill:
        since = DEFAULT_SINCE
    else:
        since = args.since or last_week
    until = args.until or yesterday

    if args.delay is None:
        delay = 1.0 if args.full_backfill else 0.5
    else:
        delay = args.delay

    skip_existing = args.skip_existing or (args.full_backfill and not args.force)

    logger.info("Daily wellness range: %s to %s", since, until)
    logger.info(
        "Mode: delay=%ss chunk=%sd skip_existing=%s stress=%s",
        delay,
        args.chunk_days,
        skip_existing,
        args.include_stress,
    )

    client = garmin_cookies.main()
    if not client:
        logger.error("Failed to connect to Garmin Connect. Check USER_EMAIL / USER_PASSWORD.")
        return 1

    df = process_daily_wellness(
        client,
        since,
        until,
        upload=not args.dry_run,
        request_delay_sec=delay,
        skip_existing=skip_existing,
        chunk_days=args.chunk_days,
        include_stress=args.include_stress,
    )

    if df.empty:
        logger.info("Nothing fetched.")
        return 0

    ok = int((df["extract_status"] == "ok").sum()) if "extract_status" in df.columns else 0
    partial = int((df["extract_status"] == "partial").sum()) if "extract_status" in df.columns else 0
    logger.info(
        "Fetched %s day(s): ok=%s partial=%s other=%s",
        len(df),
        ok,
        partial,
        len(df) - ok - partial,
    )

    sample_cols = [
        "day",
        "sleep_score",
        "hrv_last_night_avg",
        "hrv_status",
        "total_calories",
        "total_duration_sec",
        "activity_count",
        "extract_status",
    ]
    present = [c for c in sample_cols if c in df.columns]
    logger.info("\n%s", df[present].tail(min(7, len(df))).to_string(index=False))

    if args.dry_run:
        logger.info("Dry run complete — %s row(s) fetched, not uploaded.", len(df))
    else:
        logger.info("Uploaded %s row(s) to daily_wellness.", len(df))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
