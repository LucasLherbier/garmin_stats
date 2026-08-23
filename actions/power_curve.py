"""Power curve and power skills from FIT files or 1 Hz power time series."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd

# Standard Strava-like durations (label → seconds).
POWER_CURVE_DURATIONS: dict[str, int] = {
    "1s": 1,
    "5s": 5,
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "2m": 120,
    "5m": 300,
    "10m": 600,
    "20m": 1200,
    "30m": 1800,
    "60m": 3600,
    "90m": 5400,
    "120m": 7200,
}

POWER_SKILLS_BUCKETS: dict[str, list[str]] = {
    "sprinting": ["15s", "30s", "1m"],
    "attacking": ["2m", "5m", "10m"],
    "climbing_sustained": ["20m", "30m", "60m", "90m", "120m"],
}


def duration_display_label(label: str) -> str:
    """Human-readable duration for chart axes (e.g. 5m → 5min, 15s → 15s)."""
    seconds = POWER_CURVE_DURATIONS.get(label)
    if seconds is None:
        return label
    if seconds < 60:
        return label
    return f"{seconds // 60}min"


def parse_fit_power_series(fit_input: bytes | str) -> np.ndarray:
    """Extract second-by-second power from a Garmin FIT file."""
    from fitparse import FitFile

    if isinstance(fit_input, str):
        fit = FitFile(fit_input)
    else:
        fit = FitFile(BytesIO(fit_input))

    rows: list[tuple[pd.Timestamp, float]] = []
    for message in fit.get_messages("record"):
        fields = {field.name: field.value for field in message}
        timestamp = fields.get("timestamp")
        power = fields.get("power")
        if timestamp is None or power is None:
            continue
        try:
            watts = float(power)
        except (TypeError, ValueError):
            continue
        rows.append((pd.Timestamp(timestamp), watts))

    if not rows:
        return np.array([], dtype=float)

    return resample_power_to_1hz(
        pd.Series([r[0] for r in rows]),
        pd.Series([r[1] for r in rows]),
    )


def resample_power_to_1hz(
    times: pd.Series,
    watts: pd.Series,
    *,
    fill_method: str = "ffill_zero",
) -> np.ndarray:
    """
    Normalize irregular power samples to a 1 Hz series.

    fill_method:
      - ffill_zero: forward-fill short gaps, then 0 for leading/missing values
    """
    if times.empty:
        return np.array([], dtype=float)

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(times, errors="coerce"),
            "power": pd.to_numeric(watts, errors="coerce"),
        }
    ).dropna(subset=["time"]).sort_values("time")
    if df.empty:
        return np.array([], dtype=float)

    df = df.set_index("time")
    if fill_method == "ffill_zero":
        series = df["power"].resample("1s").mean().ffill().fillna(0)
    else:
        series = df["power"].resample("1s").mean().fillna(0)

    return series.to_numpy(dtype=float)


def max_mean_power(power_1hz: np.ndarray, window_seconds: int) -> float | None:
    """Highest average power over any contiguous window of length window_seconds."""
    if window_seconds <= 0 or len(power_1hz) < window_seconds:
        return None

    arr = np.asarray(power_1hz, dtype=float)
    cumsum = np.concatenate(([0.0], np.cumsum(arr)))
    window_sums = cumsum[window_seconds:] - cumsum[:-window_seconds]
    return float(window_sums.max() / window_seconds)


def calculate_power_curve(
    power_1hz: np.ndarray,
    durations: dict[str, int] | None = None,
) -> dict[str, float | None]:
    """Peak mean power (W) for each standard duration."""
    durations = durations or POWER_CURVE_DURATIONS
    return {
        label: max_mean_power(power_1hz, seconds)
        for label, seconds in durations.items()
    }


def categorize_power_skills(power_curve: dict[str, float | None]) -> dict[str, dict[str, float | None]]:
    """Group peak powers into sprinting / attacking / climbing-sustained buckets."""
    skills: dict[str, dict[str, float | None]] = {}
    for bucket, labels in POWER_SKILLS_BUCKETS.items():
        skills[bucket] = {label: power_curve.get(label) for label in labels}
    return skills


def build_power_profile(
    power_1hz: np.ndarray,
    *,
    durations: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Full profile for API / frontend consumption.

    Returns JSON-serializable dict with power_curve, power_skills, and metadata.
    """
    curve = calculate_power_curve(power_1hz, durations=durations)
    skills = categorize_power_skills(curve)
    valid = [v for v in curve.values() if v is not None]
    return {
        "power_curve": curve,
        "power_skills": skills,
        "metadata": {
            "sample_seconds": int(len(power_1hz)),
            "duration_labels": list((durations or POWER_CURVE_DURATIONS).keys()),
            "max_curve_watts": max(valid) if valid else None,
        },
    }


def power_profile_from_fit(fit_input: bytes | str) -> dict[str, Any]:
    """Parse FIT and return power curve + skills JSON structure."""
    power_1hz = parse_fit_power_series(fit_input)
    return build_power_profile(power_1hz)


def power_profile_from_telemetry(
    times: pd.Series,
    watts: pd.Series,
) -> dict[str, Any]:
    """Build profile from TCX / telemetry columns (Time, Watts)."""
    power_1hz = resample_power_to_1hz(times, watts)
    return build_power_profile(power_1hz)


def power_profile_to_json(profile: dict[str, Any], *, indent: int | None = 2) -> str:
    return json.dumps(profile, indent=indent)


def has_usable_power(watts: pd.Series, *, min_samples: int = 60) -> bool:
    """True when enough non-null power samples exist for a short curve."""
    numeric = pd.to_numeric(watts, errors="coerce").dropna()
    return len(numeric) >= min_samples and numeric.max() > 0
