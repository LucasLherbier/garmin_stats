from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from actions.home_ytd import build_history_volume, build_home_ytd, build_year_compare
from actions.sport_metrics import period_metrics
from api.activity_facts import get_activity_facts
from api.deps import get_query_fn
from api.serializers import df_to_records
from utils import sql_queries as sql
from utils.pipeline.preprocess_activities import TRAINING_RACE_PERIODS

router = APIRouter(prefix="/overview", tags=["overview"])
BENCHMARK_WINDOWS = ("last_1", "last_4", "last_12", "last_18", "last_all")
SPORT_LABELS = {
    "swimming": "Swim",
    "cycling": "Bike",
    "running": "Run",
    "duration": "Overall",
}


@router.get("/weekly-totals")
def weekly_totals(query=Depends(get_query_fn)):
    df = query(sql.get_weekly_metrics_with_delta_query_overview())
    if df.empty:
        return {"sports": [], "totals": {"duration": 0, "duration_delta": 0, "trainings": 0, "trainings_delta": 0}}

    week_total_duration = float(df["current_duration"].sum())
    last_week_total_duration = float(df["second_total_duration"].sum())
    week_nb_trainings = float(df["current_nb_trainings"].sum())
    last_week_nb_trainings = float(df["second_nb_trainings"].sum())

    sports = []
    for sport in ("swimming", "cycling", "running"):
        sport_df = df[df["activityTypeGrouped"] == sport]
        if sport_df.empty:
            sports.append(
                {
                    "sport": sport,
                    "label": SPORT_LABELS[sport],
                    "distance": 0,
                    "distance_delta": 0,
                    "duration": 0,
                }
            )
        else:
            row = sport_df.iloc[0]
            sports.append(
                {
                    "sport": sport,
                    "label": SPORT_LABELS[sport],
                    "distance": float(row["current_distance"] or 0),
                    "distance_delta": float(row["distance_delta"] or 0),
                    "duration": float(row["current_duration"] or 0),
                }
            )

    return {
        "totals": {
            "duration": week_total_duration,
            "duration_delta": week_total_duration - last_week_total_duration,
            "trainings": week_nb_trainings,
            "trainings_delta": week_nb_trainings - last_week_nb_trainings,
        },
        "sports": sports,
    }


@router.get("/volume-chart")
def volume_chart(
    sport: str = "duration",
    time_range: str = "4_units",
    granularity: str = "week",
    query=Depends(get_query_fn),
):
    df = query(sql.get_weekly_sport_query(sport, time_range, granularity))
    y_column = "total_duration" if sport == "duration" else "total_distance"
    return {
        "sport": sport,
        "y_column": y_column,
        "granularity": granularity,
        "time_range": time_range,
        "points": df_to_records(df),
    }


@router.get("/benchmarks")
def benchmarks(
    sport: str = "duration",
    granularity: str = Query("week", pattern="^(week|month)$"),
):
    facts = get_activity_facts()
    if facts.empty:
        return {"sport": sport, "granularity": granularity, "periods": []}
    periods = period_metrics(
        facts,
        None if sport == "duration" else sport,
        granularity,
        windows=BENCHMARK_WINDOWS,
    )
    return {"sport": sport, "granularity": granularity, "periods": periods}


@router.get("/weekly-breakdown")
def weekly_breakdown(query=Depends(get_query_fn)):
    df = query(sql.get_weekly_metrics_with_delta_query_overview())
    main_sports = df[df["activityTypeGrouped"].isin(["swimming", "cycling", "running"])]
    return {"sports": df_to_records(main_sports)}


def _active_race_window() -> tuple[str, str] | None:
    today = date.today()
    for race in TRAINING_RACE_PERIODS[::-1]:
        start = pd.to_datetime(race["start"]).date()
        end = pd.to_datetime(race["end"]).date()
        if start <= today < end:
            return race["start"], min(today, end).isoformat()
    return None


@router.get("/activity-heatmap")
def activity_heatmap(
    sport: str = Query("running", pattern="^(swimming|cycling|running|race)$"),
    query=Depends(get_query_fn),
):
    if sport == "race":
        window = _active_race_window()
        if not window:
            return {"sport": sport, "cells": [], "week_start": None}
        start_date, end_date = window
        sport_filter = (
            f"DATE(startTimeLocal) >= '{start_date}' AND DATE(startTimeLocal) <= '{end_date}'"
        )
    else:
        sport_filter = f"activityTypeGrouped = '{sport}'"

    df = query(sql.get_activity_heatmap_query(sport_filter))
    cells = []
    if not df.empty:
        for _, row in df.iterrows():
            cells.append(
                {
                    "dow": int(row["dow"]),
                    "slot": str(row["slot"]),
                    "count": int(row["activity_count"]),
                }
            )

    week_start_df = query(
        f"SELECT FORMAT_DATE('%Y-%m-%d', DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))) AS week_start"
    )
    week_start = None
    if not week_start_df.empty:
        week_start = str(week_start_df.iloc[0]["week_start"])

    return {"sport": sport, "week_start": week_start, "cells": cells}


@router.get("/home-ytd")
def home_ytd(query=Depends(get_query_fn)):
    today = date.today()
    start = date(today.year, 1, 1).isoformat()
    df = query(sql.get_activities_date_window_query(start, today.isoformat()))
    return build_home_ytd(df, today=today)


@router.get("/year-compare")
def year_compare(
    sport: str = Query("duration", pattern="^(duration|swimming|cycling|running|hiking)$"),
    compare_year: int | None = Query(None, ge=2020, le=2100),
    baseline_year: int | None = Query(None, ge=2020, le=2100),
    query=Depends(get_query_fn),
):
    """Cumulative volume for two calendar years (aligned weeks)."""
    today = date.today()
    current = compare_year or today.year
    baseline = baseline_year if baseline_year is not None else current - 1
    if baseline == current:
        raise HTTPException(status_code=400, detail="baseline_year and compare_year must differ.")
    y_min = min(baseline, current)
    start = date(y_min, 1, 1).isoformat()
    df = query(sql.get_activities_date_window_query(start, today.isoformat()))
    try:
        return build_year_compare(
            df,
            sport=sport,
            compare_year=current,
            baseline_year=baseline,
            today=today,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history-volume")
def history_volume(
    year: int = Query(..., ge=2020, le=2100),
    sport: str = Query("duration", pattern="^(duration|swimming|cycling|running|hiking)$"),
    query=Depends(get_query_fn),
):
    today = date.today()
    compare_year = today.year - 1
    if year != compare_year:
        raise HTTPException(
            status_code=400,
            detail=f"Only the previous calendar year ({compare_year}) is supported for comparison.",
        )
    start = date(year, 1, 1).isoformat()
    end = date(year, 12, 31).isoformat()
    df = query(sql.get_activities_date_window_query(start, end))
    return build_history_volume(df, year=year, sport=sport, today=today)


@router.get("/activity-calendar")
def activity_calendar(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    query=Depends(get_query_fn),
):
    df = query(sql.get_activity_calendar_month_query(year, month))
    activities = []
    if not df.empty:
        for _, row in df.iterrows():
            activities.append(
                {
                    "day": int(row["day"]),
                    "sport": str(row["sport"]),
                    "slot": str(row["slot"]),
                }
            )
    return {"year": year, "month": month, "activities": activities}
