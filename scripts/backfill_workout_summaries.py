"""CLI for workout_summaries. All parse/upload logic lives in utils.pipeline.workout_summaries.process."""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils.pipeline.workout_summaries.process import process_workout_summaries
from utils.pipeline.workout_summaries.lap_analysis import format_lap_table
from utils.pipeline.workout_summaries.segments import format_segments_for_log
from utils.utils_gcp import bucket

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Build workout_summaries from GCS lap CSV files.")
    parser.add_argument(
        "--activity-ids",
        nargs="+",
        type=int,
        help="Process only these Garmin activity IDs.",
    )
    parser.add_argument(
        "--since",
        help="Include activities on or after this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--until",
        help="Include activities on or before this date (YYYY-MM-DD). Default: today.",
    )
    parser.add_argument(
        "--last-year",
        action="store_true",
        help="Shorthand for --since 365 days ago (still limited to configured race periods).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild summaries even if the activity already exists in workout_summaries.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse activities and print results without uploading to BigQuery.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log every activity (default: summary counts only).",
    )
    args = parser.parse_args()

    if not bucket:
        logger.error("GCS bucket is not configured or inaccessible.")
        sys.exit(1)

    since = args.since
    until = args.until or datetime.now().strftime("%Y-%m-%d")
    if args.last_year:
        since = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    if since:
        logger.info("Date filter: %s to %s (plus race-period scope).", since, until)

    df = process_workout_summaries(
        activity_ids=args.activity_ids,
        skip_existing=not args.force,
        upload=not args.dry_run,
        since=since,
        until=until,
        replace_existing=args.force and not args.dry_run,
    )

    if df.empty:
        logger.info("Nothing processed.")
        return

    if args.verbose:
        for _, row in df.iterrows():
            logger.info(
                "%s | %s | %s | %s",
                row["activityId"],
                row["sport"],
                row["parse_status"],
                row["summary_text"],
            )
            if row.get("structure_summary"):
                logger.info("Main structure: %s", row["structure_summary"])
            if row.get("lap_analysis"):
                la = json.loads(row["lap_analysis"]) if isinstance(row["lap_analysis"], str) else row["lap_analysis"]
                if la:
                    logger.info("\n%s", format_lap_table(la))
            if row.get("segments"):
                segs = json.loads(row["segments"]) if isinstance(row["segments"], str) else row["segments"]
                if segs:
                    logger.info("\nSegments (work/rest blocks):\n%s", format_segments_for_log(segs))
    else:
        by_status = df.groupby("parse_status").size()
        logger.info("Parsed %s activities: %s", len(df), by_status.to_dict())

    if args.dry_run:
        logger.info("Dry run complete — %s row(s) parsed, not uploaded.", len(df))
    else:
        logger.info("Uploaded %s row(s) to workout_summaries.", len(df))


if __name__ == "__main__":
    main()
