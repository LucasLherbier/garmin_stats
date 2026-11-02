"""Re-download missing GPX/TCX/CSV/FIT exports from Garmin Connect for specific activities."""

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

import pandas as pd

from utils import sql_queries as sql
from utils.pipeline.activity_exports import (
    activity_base_path,
    download_activity_exports,
    missing_export_extensions,
    missing_personal_export_extensions,
)
from utils.pipeline.garmin_client import get_garmin_client, is_personal_client
from utils.utils_gcp import bucket, query_bigquery_live

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill missing activity export files (GPX, TCX, CSV, FIT) on GCS.",
    )
    parser.add_argument(
        "--activity-ids",
        nargs="+",
        type=int,
        required=True,
        help="Garmin activity IDs to backfill.",
    )
    args = parser.parse_args()

    if not bucket:
        logger.error("GCS bucket is not configured.")
        return 1

    client = get_garmin_client()
    if not client:
        logger.error("Failed to connect to Garmin (Personal API or legacy).")
        return 1

    for activity_id in args.activity_ids:
        df = query_bigquery_live(sql.get_activity_by_id_query(activity_id))
        if df.empty:
            logger.warning("Activity %s not found in BigQuery.", activity_id)
            continue
        row = df.iloc[0]
        day = row.get("Day") or row.get("startTimeLocal")
        month = pd.to_datetime(day).strftime("%Y-%m")
        base = activity_base_path(month, activity_id)
        if is_personal_client(client):
            missing = missing_personal_export_extensions(base, activity_id)
        else:
            missing = missing_export_extensions(base, activity_id)
        if not missing:
            logger.info("%s: all exports already on GCS.", activity_id)
            continue
        activity_type = row.get("activityType")
        logger.info("%s: backfilling %s …", activity_id, ", ".join(missing))
        uploaded = download_activity_exports(
            activity_id,
            client,
            base,
            only_extensions=missing,
            activity_type=activity_type,
        )
        logger.info("%s: uploaded %s", activity_id, uploaded or "(none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
