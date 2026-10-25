"""Build Connect-style lap CSV from a Garmin FIT file (Personal API path)."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
from fitparse import FitFile


def _field_map(message) -> dict[str, Any]:
    return {field.name: field.value for field in message}


def _duration_str(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    total = int(round(float(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _pace_str_s_per_km(sec_per_km: float | None) -> str | None:
    if sec_per_km is None or sec_per_km <= 0:
        return None
    sec = int(round(sec_per_km))
    return f"{sec // 60}:{sec % 60:02d}"


def _sport_group(activity_type: str | None) -> str:
    key = (activity_type or "").lower()
    if "swim" in key:
        return "swimming"
    if "cycle" in key or "bike" in key or "virtual_ride" in key:
        return "cycling"
    if "run" in key or "trail" in key:
        return "running"
    return "other"


def fit_bytes_to_connect_lap_csv(
    fit_bytes: bytes, *, activity_type: str | None = None
) -> pd.DataFrame | None:
    """Return a DataFrame compatible with workout_summaries.parse_laps."""
    sport = _sport_group(activity_type)
    if sport == "other":
        return None

    fit = FitFile(io.BytesIO(fit_bytes))
    laps = [_field_map(msg) for msg in fit.get_messages("lap")]
    if not laps:
        return None

    rows: list[dict[str, Any]] = []
    for index, lap in enumerate(laps, start=1):
        split = str(lap.get("wkt_step_name") or index)
        timer_s = lap.get("total_timer_time") or lap.get("total_elapsed_time")
        moving_s = lap.get("total_moving_time") or timer_s
        dist_m = lap.get("total_distance")
        dist_km = float(dist_m) / 1000.0 if dist_m is not None else None

        row: dict[str, Any] = {
            "Split": split,
            "Time": _duration_str(timer_s),
            "Moving Time": _duration_str(moving_s),
            "Distance": dist_km,
            "Elevation Gain": lap.get("total_ascent"),
            "Elev Loss": lap.get("total_descent"),
            "Avg HR": lap.get("avg_heart_rate"),
            "Max HR": lap.get("max_heart_rate"),
            "Calories": lap.get("total_calories"),
            "Avg Temperature": lap.get("avg_temperature"),
        }

        if sport == "running":
            pace = None
            if timer_s and dist_km and dist_km > 0:
                pace = float(timer_s) / dist_km
            row["Avg Pace"] = _pace_str_s_per_km(pace)
            row["Avg Run Cadence"] = lap.get("avg_cadence") or lap.get(
                "avg_running_cadence"
            )
        elif sport == "cycling":
            speed = lap.get("avg_speed")
            speed_kmh = float(speed) * 3.6 if speed is not None and float(speed) < 20 else speed
            row["Avg Speed"] = speed_kmh
            max_speed = lap.get("max_speed")
            row["Max Speed"] = (
                float(max_speed) * 3.6
                if max_speed is not None and float(max_speed) < 20
                else max_speed
            )
            row["Avg Power"] = lap.get("avg_power")
            row["Normalized Power"] = lap.get("normalized_power")
            row["Max Power"] = lap.get("max_power")
            row["Avg Bike Cadence"] = lap.get("avg_cadence")
        elif sport == "swimming":
            row["Swim Stroke"] = lap.get("swim_stroke") or lap.get("sub_sport")
            row["Lengths"] = lap.get("num_lengths")
            if dist_m is not None:
                row["Distance"] = float(dist_m)
            row["Avg SWOLF"] = lap.get("avg_swolf")
            row["Total Strokes"] = lap.get("total_strokes")

        rows.append(row)

    if not rows:
        return None
    return pd.DataFrame(rows)
