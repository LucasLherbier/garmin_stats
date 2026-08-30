import os
import secrets
from datetime import date

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

load_dotenv()

from actions.activity_splits import (
    laps_to_display_dataframe,
    parse_laps_field,
    resolve_sport,
)
from actions.report_assets import load_report_assets
from actions.report_html import build_activity_report_html, build_list_aggregates
from api.serializers import df_to_records, record_from_series
from utils import sql_queries as sql
from utils.github_actions import trigger_weekly_sync
from utils.utils_gcp import (
    publish_report_html,
    query_bigquery_live,
    read_shared_report_html,
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


def _build_report_html(activity_id: int):
    detail_df = query_bigquery_live(sql.get_activity_report_query(activity_id))
    if detail_df.empty:
        raise HTTPException(status_code=404, detail="Activity not found")

    detail_row = detail_df.iloc[0]
    sport = resolve_sport(detail_row)
    laps = parse_laps_field(detail_row.get("laps"))

    power_profile, hr_series, track_points, telemetry_df = load_report_assets(
        activity_id, detail_row.get("startTimeLocal"), sport
    )

    html_doc = build_activity_report_html(
        detail_row,
        laps,
        list_aggregates=None,
        power_profile=power_profile,
        hr_series=hr_series,
        track_points=track_points,
        telemetry_df=telemetry_df,
    )
    return detail_row, html_doc


@router.get("/r/{token}")
def view_shared_report(token: str):
    """Serve a published report via a short token (no long GCS signed URL)."""
    html_doc = read_shared_report_html(token)
    if not html_doc:
        raise HTTPException(status_code=404, detail="Report not found or link expired.")
    return HTMLResponse(content=html_doc, media_type="text/html; charset=utf-8")


@router.post("/generate")
def generate_report(body: GenerateReportRequest):
    detail_row, html_doc = _build_report_html(body.activity_id)

    date_str = str(detail_row.get("Day") or detail_row.get("startTimeLocal", ""))[:10]
    share_url, share_expiry_days = publish_report_html(html_doc, body.activity_id, date_str)

    return {
        "activity_id": body.activity_id,
        "html": html_doc,
        "share_url": share_url,
        "share_url_long": None,
        "share_expiry_days": share_expiry_days,
    }


@router.get("/download/{activity_id}")
def download_report(activity_id: int):
    detail_row, html_doc = _build_report_html(activity_id)
    date_str = str(detail_row.get("Day") or detail_row.get("startTimeLocal", ""))[:10]
    filename = f"report_{activity_id}_{date_str}.html"
    return HTMLResponse(
        content=html_doc,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
