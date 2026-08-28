import os
import secrets
from datetime import date

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

from actions.activity_splits import (
    laps_to_display_dataframe,
    parse_laps_field,
    resolve_sport,
)
from actions.power_curve import power_profile_from_fit, power_profile_from_telemetry
from actions.report_html import build_activity_report_html, build_list_aggregates
from actions.report_map import gpx_track_points
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from api.serializers import df_to_records, record_from_series
from utils import sql_queries as sql
from utils.github_actions import trigger_weekly_sync
from utils.utils_gcp import (
    REPORT_SHARE_EXPIRY_DAYS,
    bucket,
    check_gcs_path_exists,
    publish_report_html,
    query_bigquery_live,
)

router = APIRouter(prefix="/report", tags=["report"])


class SplitListInput(BaseModel):
    name: str = ""
    indices: list[int] = Field(default_factory=list)


class GenerateReportRequest(BaseModel):
    activity_id: int
    split_lists: list[SplitListInput] = Field(default_factory=list)


class SyncRequest(BaseModel):
    password: str = ""


def _verify_sync_password(password: str) -> None:
    expected = os.getenv("UPLOAD_TO_GITHUB", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Sync is not configured. Set UPLOAD_TO_GITHUB in the environment.",
        )
    if not secrets.compare_digest(password, expected):
        raise HTTPException(status_code=403, detail="Incorrect password.")


@router.post("/sync")
def trigger_sync(body: SyncRequest):
    _verify_sync_password(body.password)
    result = trigger_weekly_sync()
    return {
        "ok": result.ok,
        "message": result.message,
        "workflow_url": result.workflow_url,
    }


@router.get("/activities")
def activities_by_date(date_str: str = date.today().isoformat()):
    df = query_bigquery_live(sql.get_activities_by_date_query(date_str))
    if df.empty:
        return {"date": date_str, "activities": []}

    df = df.copy()
    df["start_display"] = df["startTimeLocal"].astype(str).str[11:16]
    activities = []
    for _, row in df.iterrows():
        activities.append(
            {
                "activityId": int(row["activityId"]),
                "activityName": row.get("activityName") or "Activity",
                "activityTypeGrouped": row.get("activityTypeGrouped"),
                "startTimeLocal": str(row.get("startTimeLocal")),
                "startDisplay": row["start_display"],
                "label": (
                    f"{row['start_display']} · {row.get('activityName') or 'Activity'} "
                    f"({row.get('activityTypeGrouped', '?')})"
                ),
            }
        )
    return {"date": date_str, "activities": activities}


@router.get("/activities/{activity_id}")
def activity_report_detail(activity_id: int):
    detail_df = query_bigquery_live(sql.get_activity_report_query(activity_id))
    if detail_df.empty:
        raise HTTPException(status_code=404, detail="Activity not found")

    detail = record_from_series(detail_df.iloc[0])
    sport = resolve_sport(detail_df.iloc[0])
    laps = parse_laps_field(detail.get("laps"))

    return {
        "activity": detail,
        "sport": sport,
        "laps": laps,
        "laps_display": df_to_records(laps_to_display_dataframe(laps, sport)) if laps else [],
        "parse_status": detail.get("parse_status"),
    }


def _load_report_assets(activity_id: int, start_time_local, sport: str):
    power_profile = None
    hr_series = None
    track_points = None

    if not bucket:
        return power_profile, hr_series, track_points

    if start_time_local:
        month = str(start_time_local)[:7]
    else:
        month = date.today().strftime("%Y-%m")
    base = f"data/raw/{month}/{activity_id}"

    gpx_path = f"{base}/{activity_id}.gpx"
    tcx_path = f"{base}/{activity_id}.tcx"
    fit_path = f"{base}/{activity_id}.fit"

    try:
        if check_gcs_path_exists(gpx_path):
            gpx_content = bucket.blob(gpx_path).download_as_bytes()
            track_points = gpx_track_points(gpx_content)

        if check_gcs_path_exists(tcx_path):
            tcx_content = bucket.blob(tcx_path).download_as_bytes()
            df_tcx = parse_tcx_to_dataframe(tcx_content)
            if "HeartRate" in df_tcx.columns:
                hr_series = df_tcx["HeartRate"]
            if sport == "cycling":
                if check_gcs_path_exists(fit_path):
                    fit_content = bucket.blob(fit_path).download_as_bytes()
                    power_profile = power_profile_from_fit(fit_content)
                elif "Watts" in df_tcx.columns:
                    power_profile = power_profile_from_telemetry(df_tcx["Time"], df_tcx["Watts"])
    except Exception:
        pass

    return power_profile, hr_series, track_points


@router.post("/generate")
def generate_report(body: GenerateReportRequest):
    detail_df = query_bigquery_live(sql.get_activity_report_query(body.activity_id))
    if detail_df.empty:
        raise HTTPException(status_code=404, detail="Activity not found")

    detail_row = detail_df.iloc[0]
    sport = resolve_sport(detail_row)
    laps = parse_laps_field(detail_row.get("laps"))

    list_aggregates = None
    if laps and body.split_lists:
        list_picks = [item.indices for item in body.split_lists if item.indices]
        list_names = [item.name or f"List {i + 1}" for i, item in enumerate(body.split_lists) if item.indices]
        if list_picks:
            list_aggregates = build_list_aggregates(laps, list_picks, sport, list_names=list_names)

    power_profile, hr_series, track_points = _load_report_assets(
        body.activity_id, detail_row.get("startTimeLocal"), sport
    )

    html_doc = build_activity_report_html(
        detail_row,
        laps,
        list_aggregates=list_aggregates,
        power_profile=power_profile,
        hr_series=hr_series,
        track_points=track_points,
    )

    date_str = str(detail_row.get("Day") or detail_row.get("startTimeLocal", ""))[:10]
    share_url = publish_report_html(html_doc, body.activity_id, date_str)

    return {
        "activity_id": body.activity_id,
        "html": html_doc,
        "share_url": share_url,
        "share_expiry_days": REPORT_SHARE_EXPIRY_DAYS,
    }
