"""Remove GCS files and BigQuery rows on/after a calendar date (for re-sync)."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from utils.utils_gcp import GCP_DATASET_ID, _table_id, bq_client, bucket, initialize_clients

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def _parse_since(value: str) -> datetime.date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _fetch_activity_rows(since: str) -> pd.DataFrame:
    activities = _table_id("activities")
    query = f"""
        SELECT activityId, startTimeLocal
        FROM `{activities}`
        WHERE DATE(startTimeLocal) >= @since
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("since", "DATE", since)]
    )
    return bq_client.query(query, job_config=job_config).to_dataframe()


def _delete_bq_by_activity_ids(table_name: str, activity_ids: list[int], dry_run: bool) -> None:
    if not activity_ids:
        return
    table_id = _table_id(table_name)
    if table_name == "logs":
        id_param = bigquery.ArrayQueryParameter("ids", "STRING", [str(i) for i in activity_ids])
        predicate = "activity_id IN UNNEST(@ids)"
    else:
        id_param = bigquery.ArrayQueryParameter("ids", "INT64", activity_ids)
        predicate = "activityId IN UNNEST(@ids)"
    query = f"DELETE FROM `{table_id}` WHERE {predicate}"
    job_config = bigquery.QueryJobConfig(query_parameters=[id_param])
    if dry_run:
        logger.info("[dry-run] Would run: DELETE FROM %s (%s ids)", table_name, len(activity_ids))
        return
    bq_client.query(query, job_config=job_config).result()
    logger.info("Deleted rows from %s (%s activity ids).", table_name, len(activity_ids))


def _delete_daily_wellness(since: str, dry_run: bool) -> None:
    table_id = _table_id("daily_wellness")
    query = f"DELETE FROM `{table_id}` WHERE day >= @since"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("since", "DATE", since)]
    )
    if dry_run:
        logger.info("[dry-run] Would delete daily_wellness rows with day >= %s", since)
        return
    bq_client.query(query, job_config=job_config).result()
    logger.info("Deleted daily_wellness rows with day >= %s.", since)


def _delete_activities_by_date(since: str, dry_run: bool) -> None:
    table_id = _table_id("activities")
    query = f"DELETE FROM `{table_id}` WHERE DATE(startTimeLocal) >= @since"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("since", "DATE", since)]
    )
    if dry_run:
        logger.info("[dry-run] Would delete activities with DATE(startTimeLocal) >= %s", since)
        return
    bq_client.query(query, job_config=job_config).result()
    logger.info("Deleted activities with DATE(startTimeLocal) >= %s.", since)


def _delete_workout_summaries_by_date(since: str, dry_run: bool) -> None:
    activities = _table_id("activities")
    ws = _table_id("workout_summaries")
    query = f"""
        DELETE FROM `{ws}` AS w
        WHERE w.activityId IN (
            SELECT activityId FROM `{activities}` WHERE DATE(startTimeLocal) >= @since
        )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("since", "DATE", since)]
    )
    if dry_run:
        logger.info("[dry-run] Would delete workout_summaries for activities since %s", since)
        return
    bq_client.query(query, job_config=job_config).result()
    logger.info("Deleted workout_summaries tied to activities since %s.", since)


def _week_mondays_from(since_date) -> list[str]:
    """Mondays (YYYY-MM-DD) for weekly raw/processed files to remove."""
    monday = since_date - timedelta(days=since_date.weekday())
    today = datetime.now().date()
    out: list[str] = []
    current = monday
    while current <= today:
        out.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=7)
    return out


def _gcs_delete_prefix(prefix: str, dry_run: bool) -> int:
    if bucket is None:
        logger.warning("GCS bucket not configured; skipping prefix %s", prefix)
        return 0
    count = 0
    for blob in bucket.list_blobs(prefix=prefix):
        if dry_run:
            logger.info("[dry-run] Would delete gs://%s/%s", bucket.name, blob.name)
        else:
            blob.delete()
            logger.info("Deleted gs://%s/%s", bucket.name, blob.name)
        count += 1
    return count


def _purge_gcs(activity_rows: pd.DataFrame, since_date, dry_run: bool) -> None:
    if activity_rows is not None and not activity_rows.empty:
        for _, row in activity_rows.iterrows():
            activity_id = int(row["activityId"])
            month = pd.to_datetime(row["startTimeLocal"]).strftime("%Y-%m")
            prefix = f"data/raw/{month}/{activity_id}/"
            _gcs_delete_prefix(prefix, dry_run)

    for monday in _week_mondays_from(since_date):
        month = monday[:7]
        raw_weekly = f"data/raw/{month}/{monday}_raw.csv"
        processed = f"data/processed/{month}/{monday}_activities_processed_.csv"
        for path in (raw_weekly, processed):
            if bucket is None:
                continue
            blob = bucket.blob(path)
            if not blob.exists():
                continue
            if dry_run:
                logger.info("[dry-run] Would delete gs://%s/%s", bucket.name, path)
            else:
                blob.delete()
                logger.info("Deleted gs://%s/%s", bucket.name, path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Purge GCS + BigQuery data on/after a date so a Garmin sync can be re-run.",
    )
    parser.add_argument("--since", required=True, help="First calendar day to remove (YYYY-MM-DD).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without deleting.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required to perform deletes (ignored with --dry-run).",
    )
    args = parser.parse_args()

    since_date = _parse_since(args.since)
    since_str = args.since

    if not args.dry_run and not args.yes:
        logger.error("Refusing to delete without --yes (or use --dry-run).")
        return 1

    initialize_clients()
    if bq_client is None:
        logger.error("BigQuery client not initialized (credentials?).")
        return 1

    logger.info("Dataset: %s | since: %s | dry_run=%s", GCP_DATASET_ID, since_str, args.dry_run)

    activity_rows = _fetch_activity_rows(since_str)
    activity_ids = (
        activity_rows["activityId"].astype(int).tolist() if not activity_rows.empty else []
    )
    logger.info("Found %s activity row(s) in BigQuery on/after %s.", len(activity_ids), since_str)

    # Order: summaries (by join), logs, activities, wellness; GCS last.
    _delete_workout_summaries_by_date(since_str, args.dry_run)
    _delete_bq_by_activity_ids("logs", activity_ids, args.dry_run)
    _delete_activities_by_date(since_str, args.dry_run)
    _delete_daily_wellness(since_str, args.dry_run)
    _purge_gcs(activity_rows, since_date, args.dry_run)

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
