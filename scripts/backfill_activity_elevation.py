"""Backfill elevationGain / elevationLoss in BigQuery from Garmin Connect summary API.

Use when stored activity metadata is stale (e.g. after editing elevation in Garmin Connect).
GPX/TCX tracks are not used — summaryDTO is the source of truth for gain/loss.

Example:
  python scripts/backfill_activity_elevation.py --activity-ids 24212180431 24416479329
  python scripts/backfill_activity_elevation.py --activity-ids 24212180431 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from google.cloud import bigquery

import utils.pipeline.garmin_cookies as garmin_cookies
from utils import sql_queries as sql
from utils.utils_gcp import bq_client, initialize_clients, _table_id

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Running activities with bad elevation snapshots (Aug–Sep 2026 batch).
KNOWN_BAD_ELEVATION_RUN_IDS = [
    24164988421,
    24185411282,
    24212180431,
    24247025094,
    24340564791,
    24349882214,
    24416476785,
    24416478754,
    24416479329,
    24416480525,
]


def _require_bq() -> None:
    initialize_clients()
    if bq_client is None:
        logger.error("BigQuery client is not configured.")
        sys.exit(1)


def fetch_garmin_elevation(client, activity_id: int) -> tuple[float | None, float | None, str | None]:
    details = client.get_activity(activity_id)
    summary = details.get("summaryDTO") or {}
    name = details.get("activityName")
    gain = summary.get("elevationGain")
    loss = summary.get("elevationLoss")
    if gain is not None:
        gain = float(gain)
    if loss is not None:
        loss = float(loss)
    return gain, loss, name


def fetch_bq_elevation(activity_ids: list[int]) -> dict[int, dict]:
    query = f"""
        SELECT activityId, elevationGain, elevationLoss, activityName,
               CAST(DATE(startTimeLocal) AS STRING) AS day
        FROM {sql.ACTIVITIES}
        WHERE activityId IN UNNEST(@ids)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("ids", "INT64", activity_ids)]
    )
    df = bq_client.query(query, job_config=job_config).to_dataframe()
    out: dict[int, dict] = {}
    for _, row in df.iterrows():
        out[int(row["activityId"])] = row.to_dict()
    return out


def update_activity_row(activity_id: int, gain: float | None, loss: float | None) -> int:
    table_id = _table_id("activities")
    query = f"""
        UPDATE `{table_id}`
        SET elevationGain = @gain, elevationLoss = @loss
        WHERE activityId = @activity_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("gain", "FLOAT64", gain),
            bigquery.ScalarQueryParameter("loss", "FLOAT64", loss),
            bigquery.ScalarQueryParameter("activity_id", "INT64", activity_id),
        ]
    )
    job = bq_client.query(query, job_config=job_config)
    job.result()
    return job.num_dml_affected_rows or 0


def update_workout_summary_row(activity_id: int, gain: float | None) -> int:
    table_id = _table_id("workout_summaries")
    query = f"""
        UPDATE `{table_id}`
        SET elevationGain = @gain
        WHERE activityId = @activity_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("gain", "FLOAT64", gain),
            bigquery.ScalarQueryParameter("activity_id", "INT64", activity_id),
        ]
    )
    job = bq_client.query(query, job_config=job_config)
    job.result()
    return job.num_dml_affected_rows or 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill elevationGain/elevationLoss from Garmin Connect into BigQuery.",
    )
    parser.add_argument(
        "--activity-ids",
        nargs="+",
        type=int,
        help="Garmin activity IDs to refresh.",
    )
    parser.add_argument(
        "--known-bad-batch",
        action="store_true",
        help=f"Use built-in list of {len(KNOWN_BAD_ELEVATION_RUN_IDS)} corrupted running IDs (Aug–Sep 2026).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Garmin vs BigQuery without writing.",
    )
    parser.add_argument(
        "--skip-workout-summaries",
        action="store_true",
        help="Do not update workout_summaries.elevationGain.",
    )
    args = parser.parse_args()

    activity_ids = list(args.activity_ids or [])
    if args.known_bad_batch:
        activity_ids = sorted(set(activity_ids) | set(KNOWN_BAD_ELEVATION_RUN_IDS))
    if not activity_ids:
        parser.error("Provide --activity-ids and/or --known-bad-batch.")

    client = garmin_cookies.main()
    if not client:
        logger.error("Garmin Connect login failed.")
        return 1

    _require_bq()
    bq_rows = fetch_bq_elevation(activity_ids)

    updated = 0
    for activity_id in activity_ids:
        gain, loss, api_name = fetch_garmin_elevation(client, activity_id)
        bq = bq_rows.get(activity_id)
        if not bq:
            logger.warning("%s: not in activities table — skipped", activity_id)
            continue

        old_gain = bq.get("elevationGain")
        old_loss = bq.get("elevationLoss")
        logger.info(
            "%s %s | BQ gain/loss: %s / %s → API: %s / %s",
            activity_id,
            api_name or bq.get("activityName") or "",
            old_gain,
            old_loss,
            gain,
            loss,
        )

        if args.dry_run:
            continue

        n = update_activity_row(activity_id, gain, loss)
        if n:
            updated += 1
        else:
            logger.warning("%s: activities UPDATE matched 0 rows", activity_id)

        if not args.skip_workout_summaries and gain is not None:
            ws = update_workout_summary_row(activity_id, gain)
            if ws:
                logger.info("%s: workout_summaries elevationGain updated", activity_id)

    if args.dry_run:
        logger.info("Dry run — no BigQuery changes.")
    else:
        logger.info("Done. Updated %s / %s activities.", updated, len(activity_ids))
        logger.info(
            "If daily_wellness elevation totals look off, rerun daily_wellness for affected days "
            "(scripts/backfill_daily_wellness.py --since … --until …)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
