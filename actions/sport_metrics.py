"""Period volume metrics from per-activity facts.

Single implementation behind the sport pages (metric cards + trend chart) and
the overview benchmarks, so every view sums the same activities the same way.

Windows only contain complete periods (the current week/month is excluded):
- last_N: the N periods before the current one (not clipped to the year)
- last_all: year to date, activities of the current year only
- all_time: from the first recorded activity (any sport)
The chart points of a window are exactly the periods its metrics sum over.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from actions.cycling_splits import aggregate_selected_laps, parse_laps_field

RECENT_WINDOWS = {"last_1": 1, "last_4": 4, "last_12": 12, "last_18": 18}
WINDOW_NAMES = (*RECENT_WINDOWS, "last_all", "all_time")


def activity_np_from_laps(laps_value) -> float | None:
    """Activity NP, duration-weighted over laps (same as the activity detail page)."""
    laps = parse_laps_field(laps_value)
    if not laps:
        return None
    return aggregate_selected_laps(laps, list(range(len(laps)))).get("avg_np_w")


def _period_start(day: date, granularity: str) -> date:
    if granularity == "month":
        return day.replace(day=1)
    return day - timedelta(days=day.weekday())


def _shift(period: date, n: int, granularity: str) -> date:
    if granularity == "month":
        months = period.year * 12 + period.month - 1 + n
        return date(months // 12, months % 12 + 1, 1)
    return period + timedelta(weeks=n)


def _period_range(start: date, end: date, granularity: str) -> list[date]:
    """Periods in [start, end)."""
    periods = []
    current = start
    while current < end:
        periods.append(current)
        current = _shift(current, 1, granularity)
    return periods


def _round_half_up(value: float | None) -> int | None:
    # Matches BigQuery CAST(x AS INT64) for positive values.
    if value is None:
        return None
    return int(math.floor(value + 0.5))


def _weighted(values: pd.Series, durations: pd.Series) -> int | None:
    mask = (values > 0) & (durations > 0)
    weight = durations[mask].sum()
    if weight <= 0:
        return None
    return _round_half_up(float((values[mask] * durations[mask]).sum() / weight))


def _with_periods(facts: pd.DataFrame, granularity: str) -> pd.DataFrame:
    df = facts.copy()
    start = pd.to_datetime(df["startTimeLocal"])
    df["_date"] = start.dt.date
    df["_year"] = start.dt.year
    df["_period"] = [_period_start(d, granularity) for d in df["_date"]]
    for col in ("duration", "distance", "calories", "elevationGain", "totalNumberOfStrokes"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    for col in ("averageHR", "averageSwolf", "avg_np_w"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _window_metrics(name: str, acts: pd.DataFrame, periods: list[date], with_points: bool) -> dict:
    n = len(periods)
    duration_total = float(acts["duration"].sum())
    distance_total = float(acts["distance"].sum())
    row = {
        "name": name,
        "period_count": n,
        "duration_total": duration_total,
        "duration_avg": duration_total / n if n else None,
        "nb_trainings": int(len(acts)),
        "distance_total": distance_total,
        "distance_avg": distance_total / n if n else None,
        "calories": float(acts["calories"].sum()),
        "elevationGain": float(acts["elevationGain"].sum()),
        "totalNumberOfStrokes": float(acts["totalNumberOfStrokes"].sum()),
        "averageHR": _weighted(acts["averageHR"], acts["duration"]),
        "averageSwolf": _weighted(acts["averageSwolf"], acts["duration"]),
        "avgNpW": _weighted(acts["avg_np_w"], acts["duration"]),
    }
    if with_points:
        by_period = acts.groupby("_period")[["distance", "duration"]].sum()
        row["points"] = [
            {
                "Week": p.isoformat(),
                "total_distance": float(by_period["distance"].get(p, 0.0)),
                "total_duration": float(by_period["duration"].get(p, 0.0)),
            }
            for p in periods
        ]
    return row


def period_metrics(
    facts: pd.DataFrame,
    sport: str | None,
    granularity: str = "week",
    windows: tuple[str, ...] = WINDOW_NAMES,
    with_points: bool = False,
    today: date | None = None,
) -> list[dict]:
    """Metrics per window for one sport (None = all activities).

    `today` defaults to the UTC date, like CURRENT_DATE() in the SQL views.
    """
    today = today or datetime.now(timezone.utc).date()
    current = _period_start(today, granularity)

    df = _with_periods(facts, granularity)
    first_period = _period_start(min(df["_date"]), granularity) if not df.empty else current
    df = df[df["_period"] < current]
    if sport is not None:
        df = df[df["activityTypeGrouped"] == sport]

    rows = []
    for name in windows:
        if name in RECENT_WINDOWS:
            periods = _period_range(_shift(current, -RECENT_WINDOWS[name], granularity), current, granularity)
            acts = df[df["_period"].isin(periods)]
        elif name == "last_all":
            periods = _period_range(_period_start(date(today.year, 1, 1), granularity), current, granularity)
            acts = df[df["_period"].isin(periods) & (df["_year"] == today.year)]
        elif name == "all_time":
            periods = _period_range(first_period, current, granularity)
            acts = df
        else:
            raise ValueError(f"Unknown window: {name}")
        rows.append(_window_metrics(name, acts, periods, with_points))
    return rows
