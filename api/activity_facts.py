"""Per-activity facts shared by the sport and overview routes.

Loaded from BigQuery once per data version (table last-modified time), kept in
memory, and mirrored to GCS so a cold start does not query BigQuery again.
"""

from __future__ import annotations

import json
import logging
import threading

import pandas as pd

from actions.sport_metrics import activity_np_from_laps
from utils import sql_queries as sql
from utils import utils_gcp

logger = logging.getLogger(__name__)

FACTS_TABLES = ("activities", "workout_summaries")
GCS_PATH = "cache/activity_facts.json"

_lock = threading.Lock()
_cache: dict = {"version": None, "facts": None}


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["startTimeLocal"] = pd.to_datetime(df["startTimeLocal"], errors="coerce")
    df["Day"] = df["Day"].astype(str).str[:10]
    df = df.dropna(subset=["startTimeLocal"])
    return df.sort_values("startTimeLocal", ascending=False).reset_index(drop=True)


def _load_from_bigquery() -> pd.DataFrame:
    facts = utils_gcp.query_bigquery_live(sql.get_activity_facts_query())
    if facts.empty:
        return facts
    laps = utils_gcp.query_bigquery_live(sql.get_parsed_laps_query())
    np_by_id = {}
    if not laps.empty:
        np_by_id = {
            int(row.activityId): activity_np_from_laps(row.laps)
            for row in laps.itertuples(index=False)
        }
    facts["avg_np_w"] = [np_by_id.get(int(a)) for a in facts["activityId"]]
    return _normalize(facts)


def _read_gcs(version: str) -> pd.DataFrame | None:
    if utils_gcp.bucket is None:
        return None
    try:
        blob = utils_gcp.bucket.get_blob(GCS_PATH)
        if blob is None or (blob.metadata or {}).get("version") != version:
            return None
        return _normalize(pd.DataFrame(json.loads(blob.download_as_text())))
    except Exception as e:
        logger.warning(f"Activity facts cache read failed: {e}")
        return None


def _write_gcs(facts: pd.DataFrame, version: str) -> None:
    if utils_gcp.bucket is None:
        return
    try:
        blob = utils_gcp.bucket.blob(GCS_PATH)
        blob.metadata = {"version": version}
        blob.upload_from_string(
            facts.to_json(orient="records", date_format="iso"),
            content_type="application/json",
        )
    except Exception as e:
        logger.warning(f"Activity facts cache write failed: {e}")


def get_activity_facts() -> pd.DataFrame:
    """All activities (newest first) with the columns used by sport metrics and lists."""
    version = utils_gcp.data_version(FACTS_TABLES, daily=False)
    if _cache["version"] == version:
        return _cache["facts"]
    with _lock:
        if _cache["version"] == version:
            return _cache["facts"]
        facts = _read_gcs(version)
        if facts is None:
            facts = _load_from_bigquery()
            if facts.empty:
                # Query failed or no data: do not cache, retry on next request.
                return facts
            _write_gcs(facts, version)
        _cache.update(version=version, facts=facts)
        return facts
