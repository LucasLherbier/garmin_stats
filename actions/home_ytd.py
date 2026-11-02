"""Home YTD aggregates — one BQ row scan, pandas rollups in-process."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

SPORTS = ("swimming", "cycling", "running")
HIKE_GROUPS = frozenset({"hiking", "walking"})


def _prepare_activity_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize groups (hike/walk) and parse day."""
    if df.empty:
        return df
    work = df.copy()
    work["day"] = pd.to_datetime(work["day"]).dt.date
    grouped = work["activityTypeGrouped"].astype(str).str.strip().str.lower()
    grouped = grouped.where(~grouped.isin({"nan", "none", ""}), None)
    work["activityTypeGrouped"] = grouped
    if "activityType" in work.columns:
        raw = work["activityType"].astype(str).str.lower()
        hike_mask = work["activityTypeGrouped"].isin(HIKE_GROUPS) | raw.str.contains(
            r"hik|walk|trek", case=False, na=False, regex=True
        )
        work.loc[hike_mask, "activityTypeGrouped"] = "hiking"
    else:
        work.loc[work["activityTypeGrouped"].isin(HIKE_GROUPS), "activityTypeGrouped"] = "hiking"
    return work


def _filter_sport(work: pd.DataFrame, sport: str) -> pd.DataFrame:
    if sport == "duration":
        return work
    if sport == "hiking":
        return work[work["activityTypeGrouped"] == "hiking"]
    return work[work["activityTypeGrouped"] == sport]


def _monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _monday_week(d: date) -> date:
    return _monday_on_or_before(d)


def _week_series(start: date, end: date) -> list[date]:
    """Mondays from week of start through week of end (inclusive)."""
    cur = _monday_week(start)
    end_mon = _monday_week(end)
    out: list[date] = []
    while cur <= end_mon:
        out.append(cur)
        cur += timedelta(days=7)
    return out


def _completed_week_cutoff(today: date) -> date:
    """Latest Monday strictly before the current ISO week (matches volume charts)."""
    this_mon = _monday_week(today)
    if today == this_mon:
        return this_mon - timedelta(days=7)
    return this_mon


def _iso(d: date) -> str:
    return d.isoformat()


def build_home_ytd(df: pd.DataFrame, *, today: date | None = None) -> dict:
    today = today or date.today()
    year = today.year
    ytd_start = date(year, 1, 1)
    chart_end = _completed_week_cutoff(today)

    if df.empty:
        empty_weeks = [_iso(w) for w in _week_series(ytd_start, chart_end) if w <= chart_end]
        return {
            "year": year,
            "heatmap": {"days": []},
            "weekly": {
                "hours": [{"week": w, "value": 0.0} for w in empty_weeks],
                "swim_km": [{"week": w, "value": 0.0} for w in empty_weeks],
                "bike_km": [{"week": w, "value": 0.0} for w in empty_weeks],
                "run_km": [{"week": w, "value": 0.0} for w in empty_weeks],
                "hike_km": [{"week": w, "value": 0.0} for w in empty_weeks],
            },
            "summary": _empty_summary(ytd_start, today),
        }

    work = _prepare_activity_frame(df)
    work = work[(work["day"] >= ytd_start) & (work["day"] <= today)]

    daily = work.groupby("day", as_index=False).size().rename(columns={"size": "count"})
    heat_days = [{"date": _iso(r.day), "count": int(r.count)} for r in daily.itertuples()]

    work["week"] = work["day"].map(_monday_week)
    weekly = work.groupby("week", as_index=False).agg(hours=("duration", "sum"))
    for sport, col in (
        ("swimming", "swim_km"),
        ("cycling", "bike_km"),
        ("running", "run_km"),
        ("hiking", "hike_km"),
    ):
        part = _filter_sport(work, sport).groupby("week")["distance"].sum()
        weekly[col] = weekly["week"].map(part).fillna(0.0)

    week_index = {w: i for i, w in enumerate(_week_series(ytd_start, chart_end))}

    def series_for(col: str) -> list[dict]:
        rows: list[dict] = []
        for w, idx in sorted(week_index.items(), key=lambda x: x[1]):
            if w > chart_end:
                continue
            match = weekly[weekly["week"] == w]
            val = float(match[col].iloc[0]) if not match.empty else 0.0
            rows.append({"week": _iso(w), "value": val})
        return rows

    summary = _summary_from_frame(work, ytd_start, today)
    return {
        "year": year,
        "heatmap": {"days": heat_days},
        "weekly": {
            "hours": series_for("hours"),
            "swim_km": series_for("swim_km"),
            "bike_km": series_for("bike_km"),
            "run_km": series_for("run_km"),
            "hike_km": series_for("hike_km"),
        },
        "summary": summary,
    }


def _empty_summary(ytd_start: date, today: date) -> dict:
    weeks = max(1, (_monday_week(today) - _monday_week(ytd_start)).days // 7 + 1)
    zero = {
        "total_hours": 0.0,
        "weekly_avg_hours": 0.0,
        "total_swim_km": 0.0,
        "weekly_avg_swim_km": 0.0,
        "total_bike_km": 0.0,
        "weekly_avg_bike_km": 0.0,
        "total_run_km": 0.0,
        "weekly_avg_run_km": 0.0,
        "total_hike_km": 0.0,
        "weekly_avg_hike_km": 0.0,
        "total_sessions": 0,
        "weeks_in_period": weeks,
    }
    return zero


def _summary_from_frame(work: pd.DataFrame, ytd_start: date, today: date) -> dict:
    weeks = max(1, (_monday_week(today) - _monday_week(ytd_start)).days // 7 + 1)
    total_hours = float(work["duration"].sum())
    swim = work[work["activityTypeGrouped"] == "swimming"]["distance"].sum()
    bike = work[work["activityTypeGrouped"] == "cycling"]["distance"].sum()
    run = work[work["activityTypeGrouped"] == "running"]["distance"].sum()
    hike = _filter_sport(work, "hiking")["distance"].sum()
    return {
        "total_hours": total_hours,
        "weekly_avg_hours": total_hours / weeks,
        "total_swim_km": float(swim),
        "weekly_avg_swim_km": float(swim) / weeks,
        "total_bike_km": float(bike),
        "weekly_avg_bike_km": float(bike) / weeks,
        "total_run_km": float(run),
        "weekly_avg_run_km": float(run) / weeks,
        "total_hike_km": float(hike),
        "weekly_avg_hike_km": float(hike) / weeks,
        "total_sessions": int(len(work)),
        "weeks_in_period": weeks,
    }


def build_history_volume(
    df: pd.DataFrame,
    *,
    year: int,
    sport: str,
    today: date | None = None,
) -> dict:
    """Full calendar year cumulative weekly volume for comparison."""
    today = today or date.today()
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    if year == today.year:
        end = today
    chart_end = end if year < today.year else _completed_week_cutoff(today)

    if df.empty:
        return _empty_history(year, sport, start, chart_end)

    work = _prepare_activity_frame(df)
    work = work[(work["day"] >= start) & (work["day"] <= end)]

    work["week"] = work["day"].map(_monday_week)
    scoped = _filter_sport(work, sport)
    if sport == "duration":
        weekly = work.groupby("week", as_index=False).agg(value=("duration", "sum"))
        total = float(work["duration"].sum())
        metric = "hours"
    else:
        weekly = scoped.groupby("week", as_index=False).agg(value=("distance", "sum"))
        total = float(scoped["distance"].sum())
        metric = "distance_km"

    weeks = [w for w in _week_series(start, chart_end) if w <= chart_end]
    by_week = {r.week: float(r.value) for r in weekly.itertuples()}
    cumulative: list[dict] = []
    running = 0.0
    for w in weeks:
        running += by_week.get(w, 0.0)
        cumulative.append({"week": _iso(w), "value": running, "week_value": by_week.get(w, 0.0)})

    n_weeks = max(1, len(weeks))
    return {
        "year": year,
        "sport": sport,
        "metric": metric,
        "points": cumulative,
        "summary": {
            "total": total,
            "weekly_avg": total / n_weeks,
            "weeks_in_period": n_weeks,
        },
    }


def build_year_compare(
    df: pd.DataFrame,
    *,
    sport: str,
    compare_year: int | None = None,
    baseline_year: int | None = None,
    today: date | None = None,
) -> dict:
    """Cumulative weekly volume for two calendar years (aligned by week index)."""
    today = today or date.today()
    current_year = int(compare_year or today.year)
    prior_year = int(baseline_year if baseline_year is not None else current_year - 1)
    if prior_year == current_year:
        raise ValueError("baseline_year and compare_year must differ")

    cur_start = date(current_year, 1, 1)
    chart_end = (
        _completed_week_cutoff(today)
        if current_year == today.year
        else date(current_year, 12, 31)
    )
    weeks_current = [w for w in _week_series(cur_start, chart_end) if w <= chart_end]
    weeks_prior_all = _week_series(date(prior_year, 1, 1), date(prior_year, 12, 31))
    weeks_prior = weeks_prior_all[: len(weeks_current)]

    prior_payload = build_history_volume(df, year=prior_year, sport=sport, today=today)
    current_payload = build_history_volume(df, year=current_year, sport=sport, today=today)
    metric = prior_payload["metric"]

    prior_by_week = {p["week"]: p for p in prior_payload["points"]}
    current_by_week = {p["week"]: p for p in current_payload["points"]}

    points: list[dict] = []
    for i, w_cur in enumerate(weeks_current):
        w_pri = weeks_prior[i] if i < len(weeks_prior) else None
        pri_point = prior_by_week.get(_iso(w_pri)) if w_pri else None
        cur_point = current_by_week.get(_iso(w_cur))
        label = _iso(w_cur)[5:10].replace("-", "/")
        points.append(
            {
                "week": label,
                "prior": float(pri_point["value"]) if pri_point else 0.0,
                "current": float(cur_point["value"]) if cur_point else 0.0,
            }
        )

    return {
        "sport": sport,
        "metric": metric,
        "prior_year": prior_year,
        "current_year": current_year,
        "points": points,
        "summary": {
            "prior": prior_payload["summary"],
            "current": current_payload["summary"],
        },
    }


def _empty_history(year: int, sport: str, start: date, chart_end: date) -> dict:
    metric = "hours" if sport == "duration" else "distance_km"
    weeks = [w for w in _week_series(start, chart_end) if w <= chart_end]
    return {
        "year": year,
        "sport": sport,
        "metric": metric,
        "points": [{"week": _iso(w), "value": 0.0, "week_value": 0.0} for w in weeks],
        "summary": {"total": 0.0, "weekly_avg": 0.0, "weeks_in_period": max(1, len(weeks))},
    }
