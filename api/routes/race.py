from fastapi import APIRouter, Depends, HTTPException, Query



from actions import utils as ut

from actions.race_metrics import (

    analysis_end_date,

    build_race_summary_payload,

    build_wellness_payload,

    race_options,

)

from api.deps import get_query_fn

from api.serializers import safe_float, safe_int

from utils import sql_queries as sql

from utils.pipeline.preprocess_activities import TRAINING_RACE_PERIODS



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





@router.get("/races")

def list_races():

    return {"races": race_options()}





@router.get("/{race_index}/activities")

def race_activities(

    race_index: int,

    sport: str = Query("swimming", pattern="^(swimming|cycling|running|gym)$"),

    page: int = Query(1, ge=1),

    page_size: int = Query(5, ge=1, le=50, alias="pageSize"),

    query=Depends(get_query_fn),

):

    races = TRAINING_RACE_PERIODS[::-1]

    if race_index < 0 or race_index >= len(races):

        raise HTTPException(status_code=404, detail="Race not found")



    race = races[race_index]

    end_date = analysis_end_date(race)

    sport_types = RACE_ACTIVITY_SPORTS[sport]



    df = query(sql.get_race_activities_query(race["start"], end_date, sport_types))

    if df.empty:

        return {

            "sport": sport,

            "total": 0,

            "page": page,

            "page_size": page_size,

            "total_pages": 0,

            "activities": [],

            "summary": {

                "distance_km": 0,

                "duration": "0:00:00",

                "sessions": 0,

                "average_hr": 0,

                "elevation_gain_m": 0,

            },

        }



    if "Day" in df.columns:

        df["Day"] = df["Day"].astype(str).str[:10]



    total = len(df)

    duration_seconds = float(df["duration"].fillna(0).astype(float).sum())

    hr_series = df["averageHR"].fillna(0).astype(float)

    hr_series = hr_series[hr_series > 0]

    avg_hr = float(hr_series.mean()) if not hr_series.empty else 0

    summary = {

        "distance_km": round(float(df["distance"].fillna(0).astype(float).sum()), 1),

        "duration": ut.format_duration_no_days(duration_seconds),

        "sessions": total,

        "average_hr": int(round(avg_hr)) if avg_hr > 0 else 0,

        "elevation_gain_m": int(float(df["elevationGain"].fillna(0).astype(float).sum())),

    }

    start = (page - 1) * page_size

    page_df = df.iloc[start : start + page_size]



    items = []

    for _, row in page_df.iterrows():

        avg_speed = safe_float(row.get("averageSpeed"))

        grouped_sport = str(row.get("activityTypeGrouped") or sport)

        items.append(

            {

                "activityId": safe_int(row.get("activityId")),

                "day": row.get("Day"),

                "activityName": row.get("activityName"),

                "locationName": row.get("locationName"),

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

                "trainingEffectLabel": row.get("trainingEffectLabel"),

                "calories": safe_float(row.get("calories")),

                "sport": grouped_sport,

            }

        )



    return {

        "sport": sport,

        "total": total,

        "page": page,

        "page_size": page_size,

        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 0,

        "activities": items,

        "summary": summary,

    }





@router.get("/{race_index}")

def race_detail(

    race_index: int,

    granularity: str = Query("week", pattern="^(week|month)$"),

    query=Depends(get_query_fn),

):

    races = TRAINING_RACE_PERIODS[::-1]

    if race_index < 0 or race_index >= len(races):

        raise HTTPException(status_code=404, detail="Race not found")



    race = races[race_index]

    end_date = analysis_end_date(race)



    race_metrics_df = query(sql.get_race_metrics_query(race["start"], end_date))

    if race_metrics_df.empty:

        return {"race_index": race_index, "race": race_options()[race_index], "empty": True}



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

    return payload

