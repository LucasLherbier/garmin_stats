from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, Query

from api.deps import get_query_fn
from api.serializers import df_to_records
from utils import sql_queries as sql
from utils.pipeline.preprocess_activities import TRAINING_RACE_PERIODS

router = APIRouter(prefix="/overview", tags=["overview"])
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
    granularity: str = "week",
    query=Depends(get_query_fn),
):
    if sport == "duration":
        df = query(sql.get_volume_metrics_query_overview(granularity))
    else:
        df = query(sql.get_volume_metrics_query(sport, granularity))
    return {"sport": sport, "granularity": granularity, "periods": df_to_records(df)}


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
