from fastapi import APIRouter, Depends, HTTPException, Query

import pandas as pd

from actions import utils as ut
from actions.race_metrics import (
    analysis_end_date,
    build_race_summary_payload,
    build_wellness_payload,
    race_options,
    resolve_race,
)
from api.deps import get_query_fn
from api.serializers import safe_float, safe_int, safe_str, sanitize_payload
from utils import sql_queries as sql



router = APIRouter(prefix="/race", tags=["race"])



RACE_ACTIVITY_SPORTS = {

    "swimming": ["swimming"],

    "cycling": ["cycling"],

    "running": ["running"],

    "gym": ["musculation", "gym_fitness", "physical_reinforcement"],

}





def _pace_from_speed(avg_speed: float) -> str:

    if not avg_speed or avg_speed <= 0:

        return "N/A"

    pace_min = 60 / avg_speed

    p_m, p_s = divmod(int(pace_min * 60), 60)

    return f"{p_m}:{p_s:02d} /km"





def _swim_pace_from_speed(avg_speed: float) -> str:

    if not avg_speed or avg_speed <= 0:

        return "N/A"

    pace_sec = 360.0 / avg_speed

    p_m, p_s = divmod(int(round(pace_sec)), 60)

    return f"{p_m}:{p_s:02d} /100m"


def _paginate_rows(df: pd.DataFrame, page_size: int) -> tuple[pd.DataFrame, bool]:
    has_more = len(df) > page_size
    return df.iloc[:page_size], has_more


@router.get("/races")

def list_races():

    return {"races": race_options()}


@router.get("/{race_key}/activities")

def race_activities(

    race_key: str,

    sport: str = Query("swimming", pattern="^(swimming|cycling|running|gym)$"),

    offset: int = Query(0, ge=0),

    page_size: int = Query(5, ge=1, le=50, alias="pageSize"),

    query=Depends(get_query_fn),

):

    try:
        race_index, race = resolve_race(race_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Race not found") from exc

    end_date = analysis_end_date(race)

    sport_types = RACE_ACTIVITY_SPORTS[sport]

    df = query(
        sql.get_race_activities_query(
            race["start"],
            end_date,
            sport_types,
            limit=page_size + 1,
            offset=offset,
        )
    )

    if df.empty:

        return {

            "sport": sport,

            "offset": offset,

            "page_size": page_size,

            "has_more": False,

            "activities": [],

        }



    if "Day" in df.columns:

        df["Day"] = df["Day"].astype(str).str[:10]

    page_df, has_more = _paginate_rows(df, page_size)

    items = []

    for _, row in page_df.iterrows():

        avg_speed = safe_float(row.get("averageSpeed"))

        grouped_sport = safe_str(row.get("activityTypeGrouped")) or sport

        items.append(

            {

                "activityId": safe_int(row.get("activityId")),

                "day": safe_str(row.get("Day")),

                "activityName": safe_str(row.get("activityName")),

                "locationName": safe_str(row.get("locationName")),

                "distance": safe_float(row.get("distance")),

                "duration": ut.format_duration_no_days(row.get("duration")),

                "averageHR": safe_float(row.get("averageHR")),

                "averageSpeed": avg_speed,

                "pace": (
                    _pace_from_speed(avg_speed)
                    if grouped_sport == "running"
                    else _swim_pace_from_speed(avg_speed)
                    if grouped_sport == "swimming"
                    else None
                ),

                "elevationGain": safe_float(row.get("elevationGain")),

                "trainingEffectLabel": safe_str(row.get("trainingEffectLabel")),

                "calories": safe_float(row.get("calories")),

                "sport": grouped_sport,

            }

        )



    return {

        "sport": sport,

        "offset": offset,

        "page_size": page_size,

        "has_more": has_more,

        "activities": items,

    }


@router.get("/{race_key}")

def race_detail(

    race_key: str,

    granularity: str = Query("week", pattern="^(week|month)$"),

    query=Depends(get_query_fn),

):

    try:
        race_index, race = resolve_race(race_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Race not found") from exc

    end_date = analysis_end_date(race)



    race_metrics_df = query(sql.get_race_metrics_query(race["start"], end_date, race["end"]))

    if race_metrics_df.empty:

        return {"race_index": race_index, "race": race_options()[race_index], "empty": True, "slug": race_options()[race_index]["slug"]}



    distance_by_sport = {}

    for sport in ("swimming", "cycling", "running"):

        distance_by_sport[sport] = query(

            sql.get_race_distance_by_timerange_query(race["start"], end_date, granularity, sport)

        )



    activity_duration_df = query(

        sql.get_activity_duration_by_granularity_query(race["start"], race["end"], granularity)

    )



    wellness_df = query(

        sql.get_race_wellness_daily_query(race["start"], end_date)

    )



    payload = build_race_summary_payload(

        race_index,

        race_metrics_df.iloc[0],

        granularity,

        distance_by_sport,

        activity_duration_df,

    )

    payload["race"] = race_options()[race_index]

    payload["empty"] = False

    payload["wellness"] = build_wellness_payload(wellness_df, "day")

    return sanitize_payload(payload)

