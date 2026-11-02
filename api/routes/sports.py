from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from actions import utils as ut
from actions.activity_splits import laps_to_display_dataframe, parse_laps_field
from actions.cycling_splits import aggregate_selected_laps, power_from_csv
from actions.parse_fit import fit_track_points, parse_fit_to_dataframe
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.power_curve import (
    POWER_CURVE_DURATIONS,
    duration_display_label,
    normalized_power_1hz,
    parse_fit_power_series,
    power_profile_from_fit,
    power_profile_from_telemetry,
)
from actions.report_map import gpx_track_points
from actions.sport_metrics import period_metrics
from api.activity_facts import get_activity_facts
from api.deps import get_query_fn
from api.serializers import df_to_records, record_from_series, safe_float, safe_int, safe_str
from utils import sql_queries as sql
from utils.pipeline.workout_summaries.parse_laps import normalize_laps_from_csv
from utils.utils_gcp import bucket, check_gcs_path_exists, query_bigquery_live, read_csv_from_gcs

router = APIRouter(prefix="/sports", tags=["sports"])

VALID_SPORTS = {"running", "cycling", "swimming"}
# Period filters on the sport pages: 12 weeks, 18 weeks, YTD, All.
SPORT_PAGE_WINDOWS = ("last_12", "last_18", "last_all", "all_time")


def _pace_from_speed(avg_speed: float) -> str:
    if not avg_speed or avg_speed <= 0:
        return "N/A"
    pace_min = 60 / avg_speed
    p_m, p_s = divmod(int(pace_min * 60), 60)
    return f"{p_m}:{p_s:02d} /km"


def _paginate_rows(df: pd.DataFrame, page_size: int) -> tuple[pd.DataFrame, bool]:
    has_more = len(df) > page_size
    return df.iloc[:page_size], has_more


def _serialize_activity_summary(row, sport: str) -> dict:
    avg_speed = safe_float(row.get("averageSpeed"))
    return {
        "activityId": safe_int(row.get("activityId")),
        "day": safe_str(row.get("Day")),
        "activityName": safe_str(row.get("activityName")),
        "locationName": safe_str(row.get("locationName")),
        "distance": round(safe_float(row.get("distance")), 2),
        "duration": ut.format_duration_no_days(row.get("duration")),
        "averageHR": safe_float(row.get("averageHR")),
        "averageSpeed": avg_speed,
        "pace": _pace_from_speed(avg_speed) if sport == "running" else None,
        "elevationGain": safe_float(row.get("elevationGain")),
        "averageSwolf": safe_float(row.get("averageSwolf")),
        "trainingEffectLabel": safe_str(row.get("trainingEffectLabel")),
    }


def _downsample_telemetry_df(df: pd.DataFrame, max_points: int = 800) -> pd.DataFrame:
    if len(df) <= max_points:
        return df.reset_index(drop=True)
    idx = np.linspace(0, len(df) - 1, max_points, dtype=int)
    return df.iloc[idx].reset_index(drop=True)


def _add_elapsed_seconds(df: pd.DataFrame) -> pd.DataFrame:
    if "Time" not in df.columns or df.empty:
        return df
    times = pd.to_datetime(df["Time"], errors="coerce")
    if times.isna().all():
        return df
    out = df.copy()
    out["elapsed_s"] = (times - times.iloc[0]).dt.total_seconds()
    return out


def _apply_power_profile(result: dict, profile: dict | None) -> None:
    if not profile:
        return
    curve = profile.get("power_curve", {})
    curve_np = profile.get("power_curve_np") or {}
    labels = [label for label in POWER_CURVE_DURATIONS if curve.get(label) is not None]
    result["power_profile"] = {
        "labels": labels,
        "display_labels": [duration_display_label(label) for label in labels],
        "values": [curve[label] for label in labels],
        "np_values": [curve_np.get(label) for label in labels],
        "seconds": [POWER_CURVE_DURATIONS[label] for label in labels],
        "skills": profile.get("power_skills"),
        "metadata": profile.get("metadata"),
    }


def _telemetry_from_dataframe(df: pd.DataFrame) -> list[dict] | None:
    cols = [
        c
        for c in ("Time", "HeartRate", "Cadence", "Speed", "Watts", "Altitude")
        if c in df.columns and df[c].notna().any()
    ]
    if not cols:
        return None
    telemetry_df = _add_elapsed_seconds(df[cols])
    telemetry_df = _downsample_telemetry_df(telemetry_df)
    out_cols = [c for c in (*cols, "elapsed_s") if c in telemetry_df.columns]
    return df_to_records(telemetry_df[out_cols])


def _cycling_power_from_laps(laps: list[dict] | None) -> tuple[int | None, int | None]:
    if not laps:
        return None, None
    agg = aggregate_selected_laps(laps, list(range(len(laps))))
    avg_power = agg.get("avg_power_w")
    avg_np = agg.get("avg_np_w")
    return (
        int(round(avg_power)) if avg_power is not None else None,
        int(round(avg_np)) if avg_np is not None else None,
    )


def _gcs_base_path(day_value, activity_id: int) -> str:
    if isinstance(day_value, str):
        activity_month = datetime.strptime(day_value[:10], "%Y-%m-%d").strftime("%Y-%m")
    else:
        activity_month = str(day_value)[:7]
    return f"data/raw/{activity_month}/{activity_id}"


@router.get("/{sport}/summary")
def summary(sport: str):
    """Metrics and weekly chart points for every period filter, computed from one cached dataset."""
    if sport not in VALID_SPORTS:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")
    facts = get_activity_facts()
    if facts.empty:
        return {"sport": sport, "periods": []}
    periods = period_metrics(facts, sport, windows=SPORT_PAGE_WINDOWS, with_points=True)
    return {"sport": sport, "periods": periods}


@router.get("/{sport}/activities")
def activities(
    sport: str,
    offset: int = Query(0, ge=0),
    page_size: int = Query(3, ge=1, le=50, alias="pageSize"),
):
    if sport not in VALID_SPORTS:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")

    facts = get_activity_facts()
    df = facts[facts["activityTypeGrouped"] == sport] if not facts.empty else facts
    page_df, has_more = _paginate_rows(df.iloc[offset:], page_size)
    items = [_serialize_activity_summary(row, sport) for _, row in page_df.iterrows()]

    return {
        "sport": sport,
        "offset": offset,
        "page_size": page_size,
        "has_more": has_more,
        "activities": items,
    }


@router.get("/activities/{activity_id}")
def activity_detail(activity_id: int, query=Depends(get_query_fn)):
    df = query(sql.get_activity_by_id_query(activity_id))
    if df.empty:
        raise HTTPException(status_code=404, detail="Activity not found")

    row = df.iloc[0]
    sport_type = safe_str(row.get("activityTypeGrouped")) or "running"
    if sport_type not in VALID_SPORTS:
        raise HTTPException(status_code=404, detail="Activity not found")

    detail = record_from_series(row)
    avg_speed = float(row.get("averageSpeed") or 0)
    detail["pace"] = _pace_from_speed(avg_speed) if sport_type == "running" else None
    detail["durationFormatted"] = ut.format_duration_no_days(row.get("duration"))

    result: dict = {
        "activity": detail,
        "sport": sport_type,
        "structure_summary": None,
        "track": None,
        "splits": None,
        "telemetry": None,
        "avg_power_w": None,
        "avg_np_w": None,
        "power_profile": None,
        "workout_laps": None,
        "laps": None,
    }

    if not bucket:
        return result

    base = _gcs_base_path(row.get("Day"), activity_id)
    gpx_path = f"{base}/{activity_id}.gpx"
    csv_path = f"{base}/{activity_id}.csv"
    tcx_path = f"{base}/{activity_id}.tcx"

    fit_path = f"{base}/{activity_id}.fit"

    try:
        if check_gcs_path_exists(gpx_path):
            gpx_content = bucket.blob(gpx_path).download_as_bytes()
            points = gpx_track_points(gpx_content)
            result["track"] = [{"lat": lat, "lon": lon} for lat, lon in points]
    except Exception:
        pass

    try:
        if check_gcs_path_exists(csv_path):
            df_csv = read_csv_from_gcs(csv_path)
            if sport_type == "cycling":
                avg_power, avg_np = power_from_csv(df_csv)
                result["avg_power_w"] = int(round(avg_power)) if avg_power is not None else None
                result["avg_np_w"] = int(round(avg_np)) if avg_np is not None else None
            df_csv = df_csv[df_csv["Split"] != "Summary"]
            result["splits"] = df_to_records(df_csv)
            if result["laps"] is None and sport_type in VALID_SPORTS:
                lap_rows, _detected = normalize_laps_from_csv(df_csv, sport_type)
                if lap_rows:
                    result["laps"] = lap_rows
    except Exception:
        pass

    try:
        if check_gcs_path_exists(tcx_path):
            tcx_content = bucket.blob(tcx_path).download_as_bytes()
            df_tcx = parse_tcx_to_dataframe(tcx_content)
            result["telemetry"] = _telemetry_from_dataframe(df_tcx)
            if sport_type == "cycling":
                if check_gcs_path_exists(fit_path):
                    fit_content = bucket.blob(fit_path).download_as_bytes()
                    profile = power_profile_from_fit(fit_content)
                elif "Watts" in df_tcx.columns:
                    profile = power_profile_from_telemetry(df_tcx["Time"], df_tcx["Watts"])
                else:
                    profile = None
                _apply_power_profile(result, profile)
    except Exception:
        pass

    try:
        if check_gcs_path_exists(fit_path):
            fit_content = bucket.blob(fit_path).download_as_bytes()
            if not result["track"]:
                points = fit_track_points(fit_content)
                if points:
                    result["track"] = [{"lat": lat, "lon": lon} for lat, lon in points]
            if not result["telemetry"]:
                result["telemetry"] = _telemetry_from_dataframe(parse_fit_to_dataframe(fit_content))
            if sport_type == "cycling":
                if result["avg_np_w"] is None:
                    power_1hz = parse_fit_power_series(fit_content)
                    np_val = normalized_power_1hz(power_1hz)
                    if np_val is not None:
                        result["avg_np_w"] = int(round(np_val))
                if not result["power_profile"]:
                    _apply_power_profile(result, power_profile_from_fit(fit_content))
    except Exception:
        pass

    try:
        summary_df = query_bigquery_live(sql.get_workout_summary_detail_query(activity_id))
        if not summary_df.empty:
            summary_row = summary_df.iloc[0]
            structure = summary_row.get("structure_summary")
            if structure is not None and str(structure).strip() and str(structure).lower() != "nan":
                result["structure_summary"] = str(structure).strip()
            if summary_row.get("parse_status") == "ok":
                laps = parse_laps_field(summary_row.get("laps"))
                if laps:
                    result["laps"] = df_to_records(pd.DataFrame(laps))
                    display_df = laps_to_display_dataframe(laps, sport_type)
                    result["workout_laps"] = df_to_records(display_df)
                    if sport_type == "cycling":
                        avg_power_w, avg_np_w = _cycling_power_from_laps(laps)
                        if avg_power_w is not None:
                            result["avg_power_w"] = avg_power_w
                        if avg_np_w is not None:
                            result["avg_np_w"] = avg_np_w
    except Exception:
        pass

    return result
