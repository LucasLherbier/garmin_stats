from fastapi import APIRouter, Depends, HTTPException, Query

from actions.stats_metrics import build_stats_payload
from api.deps import get_query_fn
from utils import sql_queries as sql

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def all_stats(metric: str = Query("duration", pattern="^(duration|distance)$"), query=Depends(get_query_fn)):
    df = query(sql.activities_stats())
    payload = build_stats_payload(df, metric_choice=metric)
    return payload


@router.get("/activity/{activity_id}")
def stats_activity(activity_id: int, query=Depends(get_query_fn)):
    df = query(sql.activities_stats())
    match = df[df["activityId"] == activity_id]
    if match.empty:
        raise HTTPException(status_code=404, detail="Activity not found")
    row = match.iloc[0]
    return {
        "activityId": int(row["activityId"]),
        "activityName": row.get("activityName"),
        "distance": float(row.get("distance") or 0),
        "duration": float(row.get("duration") or 0),
        "averageHR": float(row.get("averageHR") or 0),
        "averageSpeed": float(row.get("averageSpeed") or 0),
        "elevationGain": float(row.get("elevationGain") or 0),
        "calories": float(row.get("calories") or 0),
        "day": str(row.get("Day", ""))[:10],
        "activityTypeGrouped": row.get("activityTypeGrouped"),
    }
