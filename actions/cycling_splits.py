"""Cycling lap splits table and duration-weighted aggregation from workout_summaries laps."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from utils.pipeline.workout_summaries.parse_laps import format_duration


def parse_laps_field(value: Any) -> list[dict]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _lap_duration_s(lap: dict) -> float:
    return float(lap.get("moving_time_s") or lap.get("time_s") or 0)


def _weighted_mean(laps: list[dict], getter) -> float | None:
    """Duration-weighted average (not a simple arithmetic mean)."""
    weighted_sum = 0.0
    weight = 0.0
    for lap in laps:
        duration = _lap_duration_s(lap)
        value = getter(lap)
        if duration > 0 and value is not None:
            weighted_sum += float(value) * duration
            weight += duration
    return weighted_sum / weight if weight > 0 else None


def laps_to_display_dataframe(laps: list[dict]) -> pd.DataFrame:
    rows = []
    for lap in laps:
        duration_s = _lap_duration_s(lap)
        rows.append(
            {
                "Split": lap.get("split"),
                "Time": format_duration(duration_s) if duration_s else None,
                "Distance (km)": lap.get("distance_km"),
                "NP (W)": lap.get("normalized_power_w"),
                "Avg Power (W)": lap.get("avg_power_w"),
                "Avg HR": lap.get("avg_hr"),
                "Cadence": lap.get("avg_cadence"),
                "Speed (km/h)": lap.get("avg_speed_kmh"),
                "Elev gain (m)": lap.get("elevation_gain_m"),
            }
        )
    return pd.DataFrame(rows)


def split_label_for_index(laps: list[dict], index: int) -> str:
    lap = laps[index]
    duration_s = _lap_duration_s(lap)
    time_s = format_duration(duration_s) if duration_s else "?"
    return f"{lap.get('split', index + 1)} ({time_s})"


def split_drag_item(laps: list[dict], index: int) -> str:
    """Stable drag item id (split label must be unique within a ride)."""
    return split_label_for_index(laps, index)


def parse_split_drag_item(item: str, laps: list[dict]) -> int | None:
    for i in range(len(laps)):
        if split_drag_item(laps, i) == item:
            return i
    if ":" in item and item.split(":", 1)[0].isdigit():
        idx = int(item.split(":", 1)[0])
        if 0 <= idx < len(laps):
            return idx
    return None


def build_split_board(laps: list[dict], num_lists: int = 1) -> list[dict]:
    available = [split_drag_item(laps, i) for i in range(len(laps))]
    board: list[dict] = [{"header": "Available splits", "items": available}]
    for n in range(1, num_lists + 1):
        board.append({"header": f"List {n}", "items": []})
    return board


def board_lists_hash(board: list[dict]) -> tuple:
    return tuple(tuple(c.get("items") or []) for c in board[1:])


def picks_from_board(board: list[dict], laps: list[dict]) -> list[list[int]]:
    picks: list[list[int]] = []
    for container in board[1:]:
        indices = []
        for item in container.get("items") or []:
            idx = parse_split_drag_item(item, laps)
            if idx is not None:
                indices.append(idx)
        picks.append(indices)
    return picks


def aggregate_to_summary_row(name: str, split_labels: str, agg: dict[str, Any]) -> dict[str, str]:
    """One compact row for comparing multiple split selections."""
    def _fmt_num(val, fmt: str) -> str:
        return fmt.format(val) if val is not None else "—"

    return {
        "List": name,
        "Splits": split_labels,
        "Dist (km)": _fmt_num(agg.get("distance_km"), "{:.2f}"),
        "Time": agg.get("time") or "—",
        "NP (W)": _fmt_num(agg.get("avg_np_w"), "{:.0f}"),
        "Power (W)": _fmt_num(agg.get("avg_power_w"), "{:.0f}"),
        "HR": _fmt_num(agg.get("avg_hr"), "{:.0f}"),
        "Cad": _fmt_num(agg.get("avg_cadence"), "{:.0f}"),
        "Speed": _fmt_num(agg.get("avg_speed_kmh"), "{:.1f}"),
        "Elev (m)": _fmt_num(agg.get("elevation_gain_m"), "{:.0f}"),
    }


def aggregate_selected_laps(laps: list[dict], selected_indices: list[int]) -> dict[str, Any]:
    """
    Combine selected splits using duration-weighted metrics.

    - Distance, time, elevation: summed
    - Power, NP, HR, cadence, speed: weighted by split duration
    - Speed also cross-checks total distance / total moving time
    """
    selected = [laps[i] for i in selected_indices if 0 <= i < len(laps)]
    if not selected:
        return {}

    total_time_s = sum(_lap_duration_s(lap) for lap in selected)
    total_distance_km = sum(float(lap.get("distance_km") or 0) for lap in selected)
    total_elev_m = sum(float(lap.get("elevation_gain_m") or 0) for lap in selected)

    avg_power = _weighted_mean(selected, lambda l: l.get("avg_power_w"))
    avg_np = _weighted_mean(selected, lambda l: l.get("normalized_power_w"))
    avg_hr = _weighted_mean(selected, lambda l: l.get("avg_hr"))
    avg_cadence = _weighted_mean(selected, lambda l: l.get("avg_cadence"))
    avg_speed = _weighted_mean(selected, lambda l: l.get("avg_speed_kmh"))

    if total_time_s > 0 and total_distance_km > 0:
        speed_from_totals = total_distance_km / (total_time_s / 3600)
    else:
        speed_from_totals = None

    return {
        "split_count": len(selected),
        "time_s": total_time_s,
        "time": format_duration(total_time_s) if total_time_s else None,
        "distance_km": total_distance_km,
        "elevation_gain_m": total_elev_m,
        "avg_power_w": avg_power,
        "avg_np_w": avg_np,
        "avg_hr": avg_hr,
        "avg_cadence": avg_cadence,
        "avg_speed_kmh": speed_from_totals if speed_from_totals is not None else avg_speed,
    }
