"""Sport-aware lap splits display and duration-weighted aggregation for reports."""

from __future__ import annotations

from typing import Any

import pandas as pd

from actions.cycling_splits import (
    aggregate_selected_laps as aggregate_cycling_laps,
    aggregate_to_summary_row as cycling_summary_row,
    parse_laps_field,
    split_label_for_index,
    _lap_duration_s,
    _weighted_mean,
)
from utils.pipeline.workout_summaries.parse_laps import format_duration, format_pace


def resolve_sport(activity_row, summary_sport: str | None = None) -> str:
    sport = summary_sport or activity_row.get("sport") or activity_row.get("summary_sport")
    if sport:
        return str(sport).lower()
    grouped = str(activity_row.get("activityTypeGrouped") or "").lower()
    if "run" in grouped:
        return "running"
    if "cycl" in grouped or "bike" in grouped:
        return "cycling"
    if "swim" in grouped:
        return "swimming"
    return grouped or "unknown"


def _swim_duration_s(lap: dict) -> float:
    return float(lap.get("time_s") or 0)


def _format_pace_100m(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}/100m"


def laps_to_display_dataframe(laps: list[dict], sport: str) -> pd.DataFrame:
    sport = sport.lower()
    if sport == "cycling":
        from actions.cycling_splits import laps_to_display_dataframe as cycling_df

        return cycling_df(laps)

    rows = []
    for lap in laps:
        if sport == "running":
            duration_s = _lap_duration_s(lap)
            pace_s = lap.get("avg_pace_s_km")
            rows.append(
                {
                    "Split": lap.get("split"),
                    "Time": format_duration(duration_s) if duration_s else None,
                    "Distance (km)": lap.get("distance_km"),
                    "Pace": format_pace(pace_s) if pace_s else None,
                    "Elev (m)": lap.get("elevation_gain_m"),
                    "Avg HR": lap.get("avg_hr"),
                }
            )
        elif sport == "swimming":
            duration_s = _swim_duration_s(lap)
            pace_s = lap.get("avg_pace_s_100m")
            rows.append(
                {
                    "Split": lap.get("split"),
                    "Time": format_duration(duration_s) if duration_s else None,
                    "Distance (m)": lap.get("distance_m"),
                    "Pace": _format_pace_100m(pace_s),
                    "Stroke": lap.get("stroke"),
                    "SWOLF": lap.get("avg_swolf"),
                    "Avg HR": lap.get("avg_hr"),
                }
            )
    return pd.DataFrame(rows)


def aggregate_selected_laps(laps: list[dict], selected_indices: list[int], sport: str) -> dict[str, Any]:
    sport = sport.lower()
    if sport == "cycling":
        return aggregate_cycling_laps(laps, selected_indices)

    selected = [laps[i] for i in selected_indices if 0 <= i < len(laps)]
    if not selected:
        return {}

    if sport == "running":
        total_time_s = sum(_lap_duration_s(lap) for lap in selected)
        total_distance_km = sum(float(lap.get("distance_km") or 0) for lap in selected)
        total_elev_m = sum(float(lap.get("elevation_gain_m") or 0) for lap in selected)
        total_calories = sum(float(lap.get("calories") or 0) for lap in selected if lap.get("calories"))
        avg_hr = _weighted_mean(selected, lambda lap: lap.get("avg_hr"))
        avg_cadence = _weighted_mean(selected, lambda lap: lap.get("avg_cadence"))
        pace_s_km = total_time_s / total_distance_km if total_distance_km > 0 else None

        stride_weighted = 0.0
        stride_weight = 0.0
        for lap in selected:
            pace = lap.get("avg_pace_s_km")
            cad = lap.get("avg_cadence")
            dur = _lap_duration_s(lap)
            if pace and cad and cad > 0 and dur > 0:
                speed_m_min = (1000.0 / float(pace)) * 60.0
                stride_m = speed_m_min / float(cad)
                stride_weighted += stride_m * dur
                stride_weight += dur
        avg_stride_m = stride_weighted / stride_weight if stride_weight > 0 else None

        return {
            "split_count": len(selected),
            "time_s": total_time_s,
            "time": format_duration(total_time_s) if total_time_s else None,
            "distance_km": total_distance_km,
            "elevation_gain_m": total_elev_m,
            "calories": total_calories or None,
            "avg_hr": avg_hr,
            "avg_cadence": avg_cadence,
            "avg_stride_m": avg_stride_m,
            "avg_pace_s_km": pace_s_km,
            "avg_pace": format_pace(pace_s_km) if pace_s_km else None,
        }

    if sport == "swimming":
        total_time_s = sum(_swim_duration_s(lap) for lap in selected)
        total_distance_m = sum(float(lap.get("distance_m") or 0) for lap in selected)
        total_calories = sum(float(lap.get("calories") or 0) for lap in selected if lap.get("calories"))
        avg_hr = _weighted_mean(selected, lambda lap: lap.get("avg_hr"))
        avg_swolf = _weighted_mean(selected, lambda lap: lap.get("avg_swolf"))
        pace_s_100m = (total_time_s / total_distance_m * 100.0) if total_distance_m > 0 else None
        return {
            "split_count": len(selected),
            "time_s": total_time_s,
            "time": format_duration(total_time_s) if total_time_s else None,
            "distance_m": total_distance_m,
            "calories": total_calories or None,
            "avg_hr": avg_hr,
            "avg_swolf": avg_swolf,
            "avg_pace_s_100m": pace_s_100m,
            "avg_pace": _format_pace_100m(pace_s_100m),
        }

    return {}


def aggregate_to_summary_row(name: str, split_labels: str, agg: dict[str, Any], sport: str) -> dict[str, str]:
    sport = sport.lower()

    def _fmt_num(val, fmt: str) -> str:
        return fmt.format(val) if val is not None else "—"

    if sport == "cycling":
        return cycling_summary_row(name, split_labels, agg)

    if sport == "running":
        return {
            "List": name,
            "Splits": split_labels,
            "Dist (km)": _fmt_num(agg.get("distance_km"), "{:.2f}"),
            "Time": agg.get("time") or "—",
            "Pace": agg.get("avg_pace") or "—",
            "Elev (m)": _fmt_num(agg.get("elevation_gain_m"), "{:.0f}"),
            "HR": _fmt_num(agg.get("avg_hr"), "{:.0f}"),
            "Cal": _fmt_num(agg.get("calories"), "{:.0f}"),
        }

    if sport == "swimming":
        dist_m = agg.get("distance_m")
        dist_display = f"{dist_m:.0f} m" if dist_m is not None else "—"
        return {
            "List": name,
            "Splits": split_labels,
            "Distance": dist_display,
            "Time": agg.get("time") or "—",
            "Pace": agg.get("avg_pace") or "—",
            "SWOLF": _fmt_num(agg.get("avg_swolf"), "{:.0f}"),
            "HR": _fmt_num(agg.get("avg_hr"), "{:.0f}"),
        }

    return {"List": name, "Splits": split_labels}
