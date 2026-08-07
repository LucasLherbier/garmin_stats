"""Orchestrate workout summary creation and BigQuery upload."""

import json
import logging

import pandas as pd

from utils.pipeline.workout_summaries.constants import (
    PARSER_VERSION,
    SUPPORTED_SPORTS,
    WORKOUT_SUMMARY_RACE_PERIODS,
)
from utils.pipeline.workout_summaries.parse_laps import (
    activity_scalar,
    build_summary_text,
    json_safe,
    laps_to_json,
    normalize_laps_from_csv,
    workout_type_from_label,
)
from utils.pipeline.workout_summaries.lap_analysis import (
    build_cycling_lap_analysis,
    build_running_lap_analysis,
)
from utils.pipeline.workout_summaries.segments import detect_segments
from utils.pipeline.workout_summaries.structure_summary import build_main_structure_summary
from google.cloud import bigquery

from utils.utils_gcp import (
    GCP_DATASET_ID,
    GCP_PROJECT_ID,
    bq_client,
    check_gcs_path_exists,
    read_csv_from_gcs,
    upload_to_bigquery,
)

logger = logging.getLogger(__name__)

TABLE_NAME = "workout_summaries"


def _race_period_sql_filter():
    clauses = []
    for period in WORKOUT_SUMMARY_RACE_PERIODS:
        clauses.append(
            f"(DATE(startTimeLocal) >= '{period['start']}' AND DATE(startTimeLocal) < '{period['end']}')"
        )
    return " OR ".join(clauses)


def get_activities_query(activity_ids=None, since=None, until=None):
    """Build SQL to fetch activities in scoped race periods."""
    sport_list = ", ".join(f"'{sport}'" for sport in sorted(SUPPORTED_SPORTS))
    period_filter = _race_period_sql_filter()
    query = f"""
        SELECT
            activityId,
            startTimeLocal,
            FORMAT_DATE('%Y-%m', DATE(startTimeLocal)) AS month_key,
            Week,
            activityTypeGrouped AS sport,
            activityName,
            duration,
            distance,
            averageHR,
            averageSpeed,
            averageTemperature,
            elevationGain,
            trainingEffectLabel,
            trainingRace
        FROM `{GCP_DATASET_ID}.activities`
        WHERE activityTypeGrouped IN ({sport_list})
          AND ({period_filter})
    """
    if since:
        query += f"\n          AND DATE(startTimeLocal) >= '{since}'"
    if until:
        query += f"\n          AND DATE(startTimeLocal) <= '{until}'"
    if activity_ids:
        ids = ", ".join(str(int(activity_id)) for activity_id in activity_ids)
        query += f"\n          AND activityId IN ({ids})"
    query += "\n        ORDER BY startTimeLocal"
    return query


def fetch_activities(activity_ids=None, since=None, until=None):
    if bq_client is None:
        raise RuntimeError("BigQuery client is not initialized.")
    query = get_activities_query(activity_ids=activity_ids, since=since, until=until)
    return bq_client.query(query).to_dataframe()


def existing_summary_ids(activity_ids):
    if bq_client is None or not activity_ids:
        return set()
    table_id = f"{GCP_DATASET_ID}.{TABLE_NAME}"
    ids = ", ".join(str(int(activity_id)) for activity_id in activity_ids)
    query = f"SELECT activityId FROM `{table_id}` WHERE activityId IN ({ids})"
    try:
        df = bq_client.query(query).to_dataframe()
    except Exception:
        return set()
    if df.empty:
        return set()
    return {int(value) for value in df["activityId"].tolist()}


def csv_path_for_activity(activity_id, month_key):
    return f"data/raw/{month_key}/{activity_id}/{activity_id}.csv"


def process_activity_row(activity_row):
    """Parse one activity CSV into a workout_summaries row."""
    activity_id = int(activity_row["activityId"])
    month_key = activity_row["month_key"]
    sport = activity_row["sport"]
    csv_path = csv_path_for_activity(activity_id, month_key)
    parsed_at = pd.Timestamp.now()

    base_row = {
        "activityId": activity_id,
        "startTimeLocal": pd.to_datetime(activity_row["startTimeLocal"]),
        "month_key": month_key,
        "Week": pd.to_datetime(activity_row["Week"]).date() if pd.notna(activity_row.get("Week")) else None,
        "sport": sport,
        "activityName": activity_row.get("activityName"),
        "duration": activity_scalar(activity_row, "duration"),
        "distance": activity_scalar(activity_row, "distance"),
        "averageHR": activity_scalar(activity_row, "averageHR"),
        "averageTemperature": activity_scalar(activity_row, "averageTemperature"),
        "elevationGain": activity_scalar(activity_row, "elevationGain"),
        "training_effect_label": activity_row.get("trainingEffectLabel"),
        "trainingRace": activity_row.get("trainingRace"),
        "csv_path": csv_path,
        "parser_version": PARSER_VERSION,
        "parsed_at": parsed_at,
        "segments": json.dumps([]),
    }

    if sport not in SUPPORTED_SPORTS:
        base_row.update(
            {
                "summary_text": None,
                "workout_type": "unsupported_sport",
                "workout_type_source": "none",
                "laps": laps_to_json([]),
                "lap_count": 0,
                "parse_status": "unsupported_sport",
            }
        )
        return base_row

    if not check_gcs_path_exists(csv_path):
        base_row.update(
            {
                "summary_text": None,
                "workout_type": "unknown",
                "workout_type_source": "none",
                "laps": laps_to_json([]),
                "lap_count": 0,
                "parse_status": "no_csv",
            }
        )
        return base_row

    df_csv = read_csv_from_gcs(csv_path)
    laps, detected_sport = normalize_laps_from_csv(df_csv, sport)
    if detected_sport == "empty_csv":
        base_row.update(
            {
                "summary_text": None,
                "workout_type": "unknown",
                "workout_type_source": "none",
                "laps": laps_to_json([]),
                "lap_count": 0,
                "parse_status": "empty_csv",
            }
        )
        return base_row

    if detected_sport == "unsupported_sport":
        base_row.update(
            {
                "summary_text": None,
                "workout_type": "unknown",
                "workout_type_source": "none",
                "laps": laps_to_json([]),
                "lap_count": 0,
                "parse_status": "unsupported_sport",
            }
        )
        return base_row

    workout_type, workout_type_source = workout_type_from_label(activity_row.get("trainingEffectLabel"))
    segments = detect_segments(laps, detected_sport, activity_row)
    if detected_sport == "running":
        lap_analysis = build_running_lap_analysis(laps, activity_row)
    elif detected_sport == "cycling":
        lap_analysis = build_cycling_lap_analysis(laps, activity_row)
    else:
        lap_analysis = []
    phases = [row["phase"] for row in lap_analysis] if lap_analysis else None
    structure_summary = build_main_structure_summary(
        segments, detected_sport, activity_row, laps, phases
    )
    summary_text = build_summary_text(activity_row, laps, detected_sport)
    if structure_summary:
        summary_text = f"{summary_text} | {structure_summary}"

    base_row.update(
        {
            "sport": detected_sport,
            "summary_text": summary_text,
            "structure_summary": structure_summary,
            "workout_type": workout_type,
            "workout_type_source": workout_type_source,
            "laps": laps_to_json(laps),
            "segments": json.dumps(json_safe(segments), allow_nan=False),
            "lap_analysis": json.dumps(json_safe(lap_analysis), allow_nan=False),
            "lap_count": len(laps),
            "parse_status": "ok",
        }
    )
    return base_row


def build_workout_summaries(activity_ids=None, skip_existing=True, since=None, until=None):
    """Build workout summary rows for scoped activities."""
    activities = fetch_activities(activity_ids=activity_ids, since=since, until=until)
    if activities.empty:
        logger.info("No activities found for workout summary processing.")
        return pd.DataFrame()

    existing_ids = existing_summary_ids(activities["activityId"].tolist()) if skip_existing else set()
    skipped = 0
    rows = []
    for _, activity_row in activities.iterrows():
        activity_id = int(activity_row["activityId"])
        if activity_id in existing_ids:
            skipped += 1
            continue
        rows.append(process_activity_row(activity_row))

    if skipped:
        logger.info("Skipped %s activities already in workout_summaries.", skipped)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def delete_workout_summaries_ids(activity_ids):
    """Remove rows so a forced re-parse can be re-uploaded (append-only upload helper)."""
    if bq_client is None or not activity_ids:
        return False
    table_id = f"{GCP_PROJECT_ID}.{GCP_DATASET_ID}.{TABLE_NAME}"
    if "." in GCP_DATASET_ID:
        table_id = (
            GCP_DATASET_ID
            if TABLE_NAME in GCP_DATASET_ID
            else f"{GCP_DATASET_ID}.{TABLE_NAME}"
        )
    ids = [int(i) for i in activity_ids]
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("ids", "INT64", ids),
        ]
    )
    query = f"DELETE FROM `{table_id}` WHERE activityId IN UNNEST(@ids)"
    bq_client.query(query, job_config=job_config).result()
    logger.info("Deleted %s existing workout_summaries row(s) before re-upload.", len(ids))
    return True


def save_workout_summaries(df, replace_existing=False):
    if df.empty:
        logger.info("No workout summaries to upload.")
        return False
    if replace_existing:
        delete_workout_summaries_ids(df["activityId"].astype(int).tolist())
    return upload_to_bigquery(df, TABLE_NAME)


def process_workout_summaries(
    activity_ids=None, skip_existing=True, upload=True, since=None, until=None, replace_existing=False
):
    """End-to-end workout summary processing."""
    df = build_workout_summaries(
        activity_ids=activity_ids,
        skip_existing=skip_existing,
        since=since,
        until=until,
    )
    if df.empty:
        return df
    if upload:
        save_workout_summaries(df, replace_existing=replace_existing)
    return df
