"""Race preparation metrics and chart data (ported from tabs/tab_race.py)."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from actions import utils as ut
from api.serializers import safe_float, safe_str
from utils.pipeline.preprocess_activities import TRAINING_RACE_PERIODS

SPORT_COLORS = {
    "running": "#3b82f6",
    "cycling": "#10b981",
    "swimming": "#06b6d4",
    "walking": "#f59e0b",
    "hiking": "#8b5cf6",
    "strength_training": "#ec4899",
    "other": "#94a3b8",
}

RACE_SPORT_CHART_COLORS = {
    "swimming": "#38bdf8",
    "cycling": "#10b981",
    "running": "#3b82f6",
}

WELLNESS_CHART_METRICS = [
    {"key": "avg_sleep_score", "label": "Sleep score", "y_axis_title": "Score", "color": "#8b5cf6"},
    {"key": "avg_hrv", "label": "HRV", "y_axis_title": "ms", "color": "#06b6d4"},
    {"key": "avg_resting_hr", "label": "Resting HR", "y_axis_title": "bpm", "color": "#ef4444"},
    {"key": "avg_stress", "label": "Stress", "y_axis_title": "Level", "color": "#f59e0b"},
]

VOLUME_ROW_ICONS = {
    "duration": "⏱️",
    "swim": "🏊‍♂️",
    "bike": "🚴‍♂️",
    "run": "🏃‍♂️",
}


def _build_volume_row(
    rm: pd.Series,
    *,
    duration_key: str,
    sessions_key: str,
    elevation_key: str,
    swim_key: str,
    bike_key: str,
    run_key: str,
    distance_fmt: str,
    sessions_fmt: str,
    elevation_fmt: str,
    duration_formatter=ut.format_duration,
) -> dict[str, str]:
    return {
        "duration": duration_formatter(rm.get(duration_key)),
        "sessions": sessions_fmt.format(rm.get(sessions_key) or 0),
        "elevation": elevation_fmt.format(rm.get(elevation_key) or 0),
        "swim": distance_fmt.format(rm.get(swim_key) or 0),
        "bike": distance_fmt.format(rm.get(bike_key) or 0),
        "run": distance_fmt.format(rm.get(run_key) or 0),
    }


def build_training_volume(rm: pd.Series) -> list[dict[str, Any]]:
    return [
        {
            "key": "total",
            "title": "Total",
            **_build_volume_row(
                rm,
                duration_key="total_duration",
                sessions_key="total_sessions",
                elevation_key="total_elevation",
                swim_key="total_distance_swim",
                bike_key="total_distance_bike",
                run_key="total_distance_run",
                distance_fmt="{:.0f} km",
                sessions_fmt="{:.0f}",
                elevation_fmt="{:.0f} m",
            ),
        },
        {
            "key": "weekly",
            "title": "Weekly",
            **_build_volume_row(
                rm,
                duration_key=(
                    "average_prep_duration_per_week"
                    if "average_prep_duration_per_week" in rm.index
                    else "average_duration_per_week"
                ),
                sessions_key=(
                    "average_prep_week_sessions"
                    if "average_prep_week_sessions" in rm.index
                    else "average_week_sessions"
                ),
                elevation_key=(
                    "average_prep_week_elevation"
                    if "average_prep_week_elevation" in rm.index
                    else "average_week_elevation"
                ),
                swim_key=(
                    "average_prep_week_distance_swim"
                    if "average_prep_week_distance_swim" in rm.index
                    else "average_week_distance_swim"
                ),
                bike_key=(
                    "average_prep_week_distance_bike"
                    if "average_prep_week_distance_bike" in rm.index
                    else "average_week_distance_bike"
                ),
                run_key=(
                    "average_prep_week_distance_run"
                    if "average_prep_week_distance_run" in rm.index
                    else "average_week_distance_run"
                ),
                distance_fmt="{:.1f} km",
                sessions_fmt="{:.1f}",
                elevation_fmt="{:.0f} m",
                duration_formatter=ut.format_duration_no_days,
            ),
        },
        {
            "key": "8w",
            "title": "8W",
            **_build_volume_row(
                rm,
                duration_key="average_duration_last_8_weeks",
                sessions_key="average_8week_sessions",
                elevation_key="average_8week_elevation",
                swim_key="average_8week_distance_swim",
                bike_key="average_8week_distance_bike",
                run_key="average_8week_distance_run",
                distance_fmt="{:.1f} km",
                sessions_fmt="{:.1f}",
                elevation_fmt="{:.0f} m",
                duration_formatter=ut.format_duration_no_days,
            ),
        },
    ]


def _race_slug(display: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", display.lower()).strip("-") or "race"
    slug = base
    suffix = 2
    while slug in used:
        slug = f"{base}-{suffix}"
        suffix += 1
    used.add(slug)
    return slug


def race_options() -> list[dict[str, Any]]:
    races = TRAINING_RACE_PERIODS[::-1]
    options = []
    used_slugs: set[str] = set()
    for idx, race in enumerate(races):
        parts = race["race"].rsplit(" ", 1)
        name = parts[0]
        year = parts[1] if len(parts) > 1 else ""
        dist = race["distance"]
        if dist == "70.3":
            dist_str = "IRONMAN 70.3"
        elif dist == "140.6":
            dist_str = "IRONMAN"
        else:
            dist_str = dist
        display = f"{year} {dist_str} {name}".strip()
        options.append(
            {
                "index": idx,
                "slug": _race_slug(display, used_slugs),
                "display": display,
                "start": race["start"],
                "end": race["end"],
                "distance": race["distance"],
                "race": race["race"],
            }
        )
    return options


def resolve_race(race_key: str) -> tuple[int, dict[str, Any]]:
    races = TRAINING_RACE_PERIODS[::-1]
    options = race_options()
    if race_key.isdigit():
        idx = int(race_key)
        if 0 <= idx < len(races):
            return idx, races[idx]
    for option in options:
        if option["slug"] == race_key:
            return option["index"], races[option["index"]]
    raise ValueError(f"Race not found: {race_key}")


def analysis_end_date(race: dict[str, Any]) -> str:
    today_dt = pd.Timestamp.now()
    return min(today_dt, pd.to_datetime(race["end"])).strftime("%Y-%m-%d")


def build_race_summary_payload(
    race_index: int,
    race_metrics_row: pd.Series,
    granularity: str,
    distance_by_sport: dict[str, pd.DataFrame],
    activity_duration_df: pd.DataFrame,
) -> dict[str, Any]:
    rm = race_metrics_row

    training_volume = build_training_volume(rm)

    distance_charts = []
    sport_meta = [
        {"name": "swimming", "display": "Swim", "emoji": "🏊‍♂️", "color": RACE_SPORT_CHART_COLORS["swimming"]},
        {"name": "cycling", "display": "Bike", "emoji": "🚴‍♂️", "color": RACE_SPORT_CHART_COLORS["cycling"]},
        {"name": "running", "display": "Run", "emoji": "🏃‍♂️", "color": RACE_SPORT_CHART_COLORS["running"]},
    ]
    for sport in sport_meta:
        df = distance_by_sport.get(sport["name"], pd.DataFrame())
        points = []
        if not df.empty:
            for _, row in df.iterrows():
                points.append(
                    {
                        "time_period": safe_str(row["time_period"]) or "",
                        "total_distance": safe_float(row["total_distance"]),
                    }
                )
        distance_charts.append(
            {
                **sport,
                "y_axis_title": "Distance (km)",
                "x_axis_title": granularity.capitalize(),
                "points": points,
            }
        )

    training_load = volume_chart_payload(activity_duration_df, granularity)

    return {
        "race_index": race_index,
        "granularity": granularity,
        "training_volume": training_volume,
        "volume_icons": VOLUME_ROW_ICONS,
        "distance_charts": distance_charts,
        "training_load": training_load,
    }


def volume_chart_payload(activity_duration_df: pd.DataFrame, granularity: str) -> dict[str, Any]:
    if activity_duration_df.empty:
        return {"granularity": granularity, "rows": [], "totals": [], "sport_colors": SPORT_COLORS}

    df = activity_duration_df.copy()
    df["FormattedDuration"] = df["Duration"].apply(ut.format_duration_no_days)
    df["TimePeriod"] = df["TimePeriod"].astype(str).str[:10]

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "time_period": safe_str(row["TimePeriod"]) or "",
                "activityTypeGrouped": safe_str(row["activityTypeGrouped"]) or "other",
                "duration": safe_float(row["Duration"]),
                "formatted_duration": safe_str(row["FormattedDuration"]) or "",
            }
        )

    totals_df = (
        df.groupby("TimePeriod")["Duration"]
        .sum()
        .reset_index()
        .rename(columns={"Duration": "total_duration"})
    )
    totals_df["formatted_total"] = totals_df["total_duration"].apply(ut.format_duration_no_days)
    totals = [
        {
            "time_period": safe_str(r["TimePeriod"]) or "",
            "total_duration": safe_float(r["total_duration"]),
            "formatted_total": safe_str(r["formatted_total"]) or "",
        }
        for _, r in totals_df.iterrows()
    ]

    max_duration = int(totals_df["total_duration"].max() * 1.1) if not totals_df.empty else 3600
    step = max(3600, (max_duration // 4) // 3600 * 3600)
    tick_vals = list(range(0, max_duration + 1, step if step > 0 else 3600))

    return {
        "granularity": granularity,
        "title": "Total Volume",
        "y_axis_title": "Duration",
        "rows": rows,
        "totals": totals,
        "sport_colors": SPORT_COLORS,
        "y_ticks": [{"value": v, "label": ut.format_duration_no_days(v)} for v in tick_vals],
        "y_max": max_duration,
    }


def _nullable_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(parsed) else parsed


def build_wellness_payload(wellness_df: pd.DataFrame, granularity: str) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    if not wellness_df.empty:
        for _, row in wellness_df.iterrows():
            points.append(
                {
                    "time_period": str(row["time_period"])[:10],
                    "avg_sleep_score": _nullable_float(row.get("avg_sleep_score")),
                    "avg_hrv": _nullable_float(row.get("avg_hrv")),
                    "avg_resting_hr": _nullable_float(row.get("avg_resting_hr")),
                    "avg_body_battery_high": _nullable_float(row.get("avg_body_battery_high")),
                    "avg_body_battery_low": _nullable_float(row.get("avg_body_battery_low")),
                    "avg_stress": _nullable_float(row.get("avg_stress")),
                    "avg_sleep_duration_sec": _nullable_float(row.get("avg_sleep_duration_sec")),
                    "day_count": int(row.get("day_count") or 0),
                }
            )

    charts = []
    for metric in WELLNESS_CHART_METRICS:
        chart_points = []
        for point in points:
            value = point.get(metric["key"])
            if value is None:
                continue
            chart_points.append({"time_period": point["time_period"], "value": value})
        charts.append({**metric, "points": chart_points})

    return {
        "granularity": granularity,
        "points": points,
        "charts": charts,
    }
