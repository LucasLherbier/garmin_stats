"""Build and upload daily_wellness rows to BigQuery."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
from google.cloud import bigquery

from utils import sql_queries as sql
from utils.pipeline.daily_wellness.extract import (
    fetch_bulk_body_battery,
    fetch_bulk_resting_hr,
    fetch_day_wellness,
    iter_date_chunks,
)
from utils.utils_gcp import bq_client, merge_daily_wellness_to_bigquery

logger = logging.getLogger(__name__)

TABLE_NAME = "daily_wellness"

ACTIVITY_ROLLUP_QUERY = f"""
SELECT
    DATE(startTimeLocal) AS day,
    COUNT(*) AS activity_count,
    SUM(COALESCE(duration, 0)) AS total_duration_sec,
    SUM(COALESCE(calories, 0)) AS total_calories,
    SUM(CASE WHEN activityTypeGrouped = 'swimming' THEN COALESCE(distance, 0) ELSE 0 END) AS swim_distance_km,
    SUM(CASE WHEN activityTypeGrouped = 'cycling' THEN COALESCE(distance, 0) ELSE 0 END) AS bike_distance_km,
    SUM(CASE WHEN activityTypeGrouped = 'running' THEN COALESCE(distance, 0) ELSE 0 END) AS run_distance_km,
    SUM(COALESCE(elevationGain, 0)) AS elevation_gain_m
FROM {sql.ACTIVITIES}
WHERE DATE(startTimeLocal) BETWEEN @start_date AND @end_date
GROUP BY day
"""


def iter_days(since: str, until: str):
    start = datetime.strptime(since, "%Y-%m-%d").date()
    end = datetime.strptime(until, "%Y-%m-%d").date()
    current = start
    while current <= end:
        yield current.strftime("%Y-%m-%d")
        current += timedelta(days=1)


def fetch_activity_rollups(since: str, until: str) -> dict[str, dict]:
    if bq_client is None:
        logger.warning("BigQuery client not initialized; activity rollups skipped.")
        return {}

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", since),
            bigquery.ScalarQueryParameter("end_date", "DATE", until),
        ]
    )
    try:
        df = bq_client.query(ACTIVITY_ROLLUP_QUERY, job_config=job_config).to_dataframe()
    except Exception as exc:
        logger.warning("Activity rollup query failed: %s", exc)
        return {}

    if df.empty:
        return {}

    rollups: dict[str, dict] = {}
    for _, row in df.iterrows():
        day = str(row["day"])[:10]
        rollups[day] = {
            "activity_count": int(row.get("activity_count") or 0),
            "total_duration_sec": int(row.get("total_duration_sec") or 0),
            "total_calories": int(row.get("total_calories") or 0),
            "swim_distance_km": float(row.get("swim_distance_km") or 0),
            "bike_distance_km": float(row.get("bike_distance_km") or 0),
            "run_distance_km": float(row.get("run_distance_km") or 0),
            "elevation_gain_m": float(row.get("elevation_gain_m") or 0),
        }
    return rollups


def fetch_existing_days(since: str, until: str) -> set[str]:
    if bq_client is None:
        return set()

    table_id = sql.DAILY_WELLNESS.strip("`")
    query = f"""
        SELECT CAST(day AS STRING) AS day
        FROM `{table_id}`
        WHERE day BETWEEN @start_date AND @end_date
          AND extract_status IN ('ok', 'partial')
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", since),
            bigquery.ScalarQueryParameter("end_date", "DATE", until),
        ]
    )
    try:
        df = bq_client.query(query, job_config=job_config).to_dataframe()
    except Exception:
        return set()
    if df.empty:
        return set()
    return {str(day)[:10] for day in df["day"].tolist()}


def _build_prefetched(client, since: str, until: str) -> dict[str, dict]:
    logger.info("Fetching body battery in bulk (%s → %s)...", since, until)
    body_battery = fetch_bulk_body_battery(client, since, until)
    logger.info("Body battery days: %s", len(body_battery))

    logger.info("Fetching resting HR in bulk (%s → %s)...", since, until)
    resting_hr = fetch_bulk_resting_hr(client, since, until)
    logger.info("Resting HR days: %s", len(resting_hr))

    prefetched: dict[str, dict] = {}
    for day in iter_days(since, until):
        entry: dict = {}
        if day in body_battery:
            entry.update(body_battery[day])
        if day in resting_hr:
            entry["resting_hr"] = resting_hr[day]
        if entry:
            prefetched[day] = entry
    return prefetched


def build_daily_wellness_rows(
    client,
    since: str,
    until: str,
    *,
    request_delay_sec: float = 0.35,
    skip_existing: bool = False,
    include_stress: bool = False,
) -> pd.DataFrame:
    """Fetch Garmin wellness + join activity rollups for each day in range."""
    rollups = fetch_activity_rollups(since, until)
    existing = fetch_existing_days(since, until) if skip_existing else set()
    prefetched = _build_prefetched(client, since, until)

    rows: list[dict] = []
    days = [day for day in iter_days(since, until) if day not in existing]
    if existing:
        logger.info("Skipping %s day(s) already in daily_wellness.", len(existing))
    logger.info("Fetching %s day(s) from Garmin (3 calls/day: sleep, HRV, stats)...", len(days))

    for index, day in enumerate(days, start=1):
        row = fetch_day_wellness(
            client,
            day,
            prefetched=prefetched,
            request_delay_sec=request_delay_sec,
            include_stress=include_stress,
        )
        rollup = rollups.get(day, {})
        row.update(rollup)

        if not row.get("total_calories") and row.get("daily_calories"):
            row["total_calories"] = row["daily_calories"]

        row["extracted_at"] = pd.Timestamp.utcnow().isoformat()
        rows.append(row)

        if index % 25 == 0 or index == len(days):
            logger.info("Progress: %s/%s days", index, len(days))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "extract_errors" not in df.columns:
        df["extract_errors"] = None
    return df


def save_daily_wellness(df: pd.DataFrame) -> bool:
    if df.empty:
        logger.info("No daily wellness rows to upload.")
        return False
    return merge_daily_wellness_to_bigquery(df, TABLE_NAME)


def process_daily_wellness(
    client,
    since: str,
    until: str,
    *,
    upload: bool = True,
    request_delay_sec: float = 0.35,
    skip_existing: bool = False,
    chunk_days: int = 31,
    include_stress: bool = False,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for chunk_start, chunk_end in iter_date_chunks(since, until, chunk_days):
        logger.info("Processing chunk %s → %s", chunk_start, chunk_end)
        chunk_df = build_daily_wellness_rows(
            client,
            chunk_start,
            chunk_end,
            request_delay_sec=request_delay_sec,
            skip_existing=skip_existing,
            include_stress=include_stress,
        )
        if chunk_df.empty:
            continue
        if upload:
            save_daily_wellness(chunk_df)
        frames.append(chunk_df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
