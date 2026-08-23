"""Normalize Garmin lap CSV exports into a consistent JSON-friendly structure."""

import json
import re

import numpy as np
import pandas as pd

def _is_missing(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return True
    text = str(value).strip()
    return text in {"", "--", "nan", "None"}


def _to_float(value):
    if _is_missing(value):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _parse_duration_seconds(value):
    if _is_missing(value):
        return None
    text = str(value).strip()
    parts = text.split(":")
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return None
    return None


def _parse_pace_seconds(value):
    if _is_missing(value):
        return None
    text = str(value).strip()
    if ":" not in text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except ValueError:
        return None
    return None


def _normalize_columns(df):
    return df.rename(columns={col: col.strip() for col in df.columns})


def _detect_sport(df, sport_hint):
    columns = set(df.columns)
    if sport_hint == "swimming" or "Swim Stroke" in columns:
        return "swimming"
    if "Avg Power" in columns or "Normalized Power" in columns:
        return "cycling"
    if "Avg Pace" in columns or "Avg Run Cadence" in columns:
        return "running"
    return sport_hint


def _running_pace_s_km(row) -> float | None:
    """Prefer moving pace; Garmin Avg Pace includes stopped time on short splits."""
    for col in ("Avg Moving Paces", "Avg Moving Pace"):
        if col in row.index:
            pace = _parse_pace_seconds(row.get(col))
            if pace is not None:
                return float(pace)
    moving_s = _parse_duration_seconds(row.get("Moving Time"))
    distance_km = _to_float(row.get("Distance"))
    if moving_s and distance_km and distance_km > 0:
        return float(moving_s) / float(distance_km)
    pace = _parse_pace_seconds(row.get("Avg Pace"))
    return float(pace) if pace is not None else None


def _normalize_running_laps(df):
    laps = []
    for _, row in df.iterrows():
        split = str(row.get("Split", "")).strip()
        if not split or split.upper() == "REST":
            continue
        laps.append(
            {
                "split": split,
                "time_s": _parse_duration_seconds(row.get("Time")),
                "moving_time_s": _parse_duration_seconds(row.get("Moving Time")),
                "distance_km": _to_float(row.get("Distance")),
                "elevation_gain_m": _to_float(row.get("Elevation Gain")),
                "elevation_loss_m": _to_float(row.get("Elev Loss")),
                "avg_pace_s_km": _running_pace_s_km(row),
                "best_pace_s_km": _parse_pace_seconds(row.get("Best Pace")),
                "avg_hr": _to_float(row.get("Avg HR")),
                "max_hr": _to_float(row.get("Max HR")),
                "avg_cadence": _to_float(row.get("Avg Run Cadence")),
                "avg_temperature_c": _to_float(row.get("Avg Temperature")),
                "calories": _to_float(row.get("Calories")),
            }
        )
    return laps


def _normalize_cycling_laps(df):
    laps = []
    for _, row in df.iterrows():
        split = str(row.get("Split", "")).strip()
        if not split:
            continue
        laps.append(
            {
                "split": split,
                "time_s": _parse_duration_seconds(row.get("Time")),
                "moving_time_s": _parse_duration_seconds(row.get("Moving Time")),
                "distance_km": _to_float(row.get("Distance")),
                "elevation_gain_m": _to_float(row.get("Elevation Gain")),
                "elevation_loss_m": _to_float(row.get("Elev Loss")),
                "avg_speed_kmh": _to_float(row.get("Avg Speed")),
                "max_speed_kmh": _to_float(row.get("Max Speed")),
                "avg_hr": _to_float(row.get("Avg HR")),
                "max_hr": _to_float(row.get("Max HR")),
                "avg_power_w": _to_float(row.get("Avg Power")),
                "normalized_power_w": _to_float(row.get("Normalized Power")),
                "max_power_w": _to_float(row.get("Max Power")),
                "avg_cadence": _to_float(row.get("Avg Bike Cadence")),
                "avg_temperature_c": _to_float(row.get("Avg Temperature")),
                "calories": _to_float(row.get("Calories")),
            }
        )
    return laps


def cycling_lap_power_w(lap: dict) -> float | None:
    """Normalized power per lap when present; otherwise average power."""
    np_val = lap.get("normalized_power_w")
    if np_val is not None:
        return float(np_val)
    avg = lap.get("avg_power_w")
    return float(avg) if avg is not None else None


def cycling_lap_speed_kmh(lap: dict) -> float | None:
    speed = lap.get("avg_speed_kmh")
    return float(speed) if speed is not None else None


def cycling_ride_uses_power(laps: list[dict], min_fraction: float = 0.5) -> bool:
    if not laps:
        return False
    with_power = sum(1 for lap in laps if cycling_lap_power_w(lap) is not None)
    return with_power >= max(1, len(laps) * min_fraction)


def cycling_lap_intensity(lap: dict, prefer_power: bool) -> tuple[str, float | None]:
    """Primary intensity for work/recovery: NP/avg power, else lap speed."""
    if prefer_power:
        power = cycling_lap_power_w(lap)
        if power is not None:
            return "power", power
    speed = cycling_lap_speed_kmh(lap)
    if speed is not None:
        return "speed", speed
    if not prefer_power:
        power = cycling_lap_power_w(lap)
        if power is not None:
            return "power", power
    return "none", None


def activity_scalar(row, key):
    """Match activities table semantics: missing/null -> None (not NaN)."""
    if key not in row.index if hasattr(row, "index") else key not in row:
        return None
    val = row[key]
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (np.floating, float)):
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    if isinstance(val, (np.integer, int)):
        return int(val)
    return val


def json_safe(value):
    if value is None:
        return None
    if isinstance(value, (float, np.floating)):
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


def laps_to_json(laps):
    return json.dumps(json_safe(laps), allow_nan=False)


def _normalize_swimming_laps(df):
    laps = []
    for _, row in df.iterrows():
        split = str(row.get("Split", "")).strip()
        if not split:
            continue
        is_rest = split.upper() == "REST" or "REST" in split.upper()
        stroke = row.get("Swim Stroke")
        laps.append(
            {
                "split": split,
                "stroke": None if _is_missing(stroke) else str(stroke).strip(),
                "lengths": _to_float(row.get("Lengths")),
                "distance_m": _to_float(row.get("Distance")),
                "time_s": _parse_duration_seconds(row.get("Time")),
                "avg_pace_s_100m": _parse_pace_seconds(row.get("Avg Pace")),
                "best_pace_s_100m": _parse_pace_seconds(row.get("Best Pace")),
                "avg_swolf": _to_float(row.get("Avg SWOLF")),
                "avg_hr": _to_float(row.get("Avg HR")),
                "max_hr": _to_float(row.get("Max HR")),
                "total_strokes": _to_float(row.get("Total Strokes")),
                "calories": _to_float(row.get("Calories")),
                "is_rest": is_rest,
            }
        )
    return laps


def _is_summary_lap(lap: dict) -> bool:
    split = str(lap.get("split", "")).strip().lower()
    return split in {"summary", "total"} or "summary" in split


def normalize_laps_from_csv(df, sport):
    """Return normalized lap rows for run, bike, or swim CSV exports."""
    if df is None or df.empty:
        return [], "empty_csv"

    df = _normalize_columns(df)
    sport = _detect_sport(df, sport)

    if sport == "running":
        laps = _normalize_running_laps(df)
    elif sport == "cycling":
        laps = _normalize_cycling_laps(df)
    elif sport == "swimming":
        laps = _normalize_swimming_laps(df)
    else:
        return [], "unsupported_sport"
    return [lap for lap in laps if not _is_summary_lap(lap)], sport


def format_pace(seconds):
    if seconds is None or np.isnan(seconds):
        return None
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}/km"


def format_duration(seconds):
    if seconds is None or np.isnan(seconds):
        return None
    seconds = int(round(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _activity_pace_s_km(activity_row):
    """Overall run pace from activity duration and distance (km)."""
    duration = activity_row.get("duration")
    distance = activity_row.get("distance")
    if duration is None or distance is None or pd.isna(duration) or pd.isna(distance):
        return None
    if float(distance) <= 0:
        return None
    return float(duration) / float(distance)


def _activity_speed_kmh(activity_row):
    """Overall speed from duration/distance; fallback to averageSpeed (Garmin m/s in BQ)."""
    duration = activity_row.get("duration")
    distance = activity_row.get("distance")
    if duration is not None and distance is not None and not pd.isna(duration) and not pd.isna(distance):
        if float(duration) > 0 and float(distance) > 0:
            return float(distance) / (float(duration) / 3600.0)
    avg_speed = activity_row.get("averageSpeed")
    if avg_speed is None or pd.isna(avg_speed):
        return None
    speed = float(avg_speed)
    # Stored as m/s in activities (see sql_queries * 3.6 for display)
    if speed < 20:
        speed *= 3.6
    return speed


def build_summary_text(activity_row, laps, sport):
    """Build a one-line workout summary from activity metadata and normalized laps."""
    name = activity_row.get("activityName") or sport
    distance = activity_row.get("distance")
    duration = activity_row.get("duration")
    avg_hr = activity_row.get("averageHR")
    label = activity_row.get("trainingEffectLabel")

    parts = [str(name).strip()]

    if distance is not None and not pd.isna(distance):
        if sport == "swimming":
            parts.append(f"{distance * 1000:.0f} m")
        else:
            parts.append(f"{distance:.1f} km")

    if duration is not None and not pd.isna(duration):
        parts.append(format_duration(duration))

    work_laps = [lap for lap in laps if not lap.get("is_rest")]
    if work_laps:
        parts.append(f"{len(work_laps)} laps")

    if sport == "running":
        pace_s_km = _activity_pace_s_km(activity_row)
        if pace_s_km is not None:
            parts.append(f"avg pace {format_pace(pace_s_km)}")
    elif sport == "cycling":
        speed_kmh = _activity_speed_kmh(activity_row)
        if speed_kmh is not None:
            parts.append(f"avg {speed_kmh:.1f} km/h")
    elif sport == "swimming":
        if duration is not None and distance is not None and not pd.isna(duration) and not pd.isna(distance):
            if float(distance) > 0:
                pace_100m = float(duration) / (float(distance) * 10.0)
                parts.append(f"avg pace {format_pace(pace_100m)}/100m")

    if avg_hr is not None and not pd.isna(avg_hr):
        parts.append(f"HR {int(round(avg_hr))}")

    if label and not pd.isna(label):
        parts.append(str(label).replace("_", " ").title())

    summary = " - ".join(parts[:1] + [" | ".join(parts[1:])]) if len(parts) > 1 else parts[0]
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary


def workout_type_from_label(training_effect_label):
    if training_effect_label is None or (isinstance(training_effect_label, float) and pd.isna(training_effect_label)):
        return "unknown", "none"
    normalized = str(training_effect_label).strip().lower()
    if not normalized:
        return "unknown", "none"
    return normalized, "garmin_fallback"
