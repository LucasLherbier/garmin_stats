"""Per-lap metrics and % vs activity average pace (and carry similar laps)."""

from __future__ import annotations

import statistics
from typing import Any

from utils.pipeline.workout_summaries.parse_laps import (
    _activity_speed_kmh,
    activity_scalar,
    cycling_lap_intensity,
    cycling_lap_power_w,
    cycling_ride_uses_power,
    format_duration,
    format_pace,
)


def _lap_duration(lap: dict) -> float | None:
    return lap.get("moving_time_s") or lap.get("time_s")


def _is_full_km_lap(lap: dict) -> bool:
    d = lap.get("distance_km")
    return d is not None and 0.85 <= d <= 1.15


def _mean(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return float(statistics.mean(clean)) if clean else None


def _median(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return float(statistics.median(clean)) if clean else None


def _pct_vs_baseline(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None or baseline == 0:
        return None
    return round((float(value) - float(baseline)) / float(baseline) * 100, 1)


def _activity_avg_pace_s_km(activity_row) -> float | None:
    duration = activity_scalar(activity_row, "duration")
    distance = activity_scalar(activity_row, "distance")
    if duration and distance and float(distance) > 0:
        return float(duration) / float(distance)
    return None


def _activity_avg_hr(activity_row) -> float | None:
    return activity_scalar(activity_row, "averageHR")


def _elev_stable(
    elev: float,
    med_elev: float | None,
    use_elev: bool,
    threshold: float = 0.05,
) -> bool:
    if not use_elev or med_elev is None:
        return True
    return abs(elev - med_elev) / max(med_elev, 1) <= threshold


def _classify_lap_phase(
    lap: dict,
    avg_pace: float | None,
    avg_hr: float | None,
    med_elev: float | None,
    use_elev: bool,
    threshold: float = 0.05,
) -> str:
    pace = lap.get("avg_pace_s_km")
    hr = lap.get("avg_hr")
    elev = lap.get("elevation_gain_m") or 0
    stable = _elev_stable(elev, med_elev, use_elev, threshold)

    if pace and avg_pace and avg_pace > 0:
        pace_delta = (pace - avg_pace) / avg_pace
        if pace_delta <= -threshold and stable:
            return "work"
        if pace_delta >= threshold and stable:
            return "recovery"

    work_signals = 0
    easy_signals = 0

    if hr and avg_hr and avg_hr > 0:
        hr_delta = (hr - avg_hr) / avg_hr
        if hr_delta >= threshold:
            work_signals += 1
        elif hr_delta <= -threshold:
            easy_signals += 1

    if use_elev and med_elev is not None:
        elev_delta = (elev - med_elev) / max(med_elev, 1)
        if elev_delta >= threshold:
            work_signals += 1
        elif elev_delta <= -threshold:
            easy_signals += 1

    if pace and avg_pace and avg_pace > 0:
        if abs(pace - avg_pace) / avg_pace <= threshold:
            hr_up = hr and avg_hr and (hr - avg_hr) / avg_hr >= threshold
            elev_up = use_elev and (elev - med_elev) / max(med_elev, 1) >= threshold
            if hr_up and elev_up:
                work_signals += 1

    if work_signals >= 2:
        return "work"
    if easy_signals >= 2:
        return "recovery"
    return "steady"


def _classify_cycling_lap_phase(
    intensity: float | None,
    avg_intensity: float | None,
    lap: dict,
    avg_hr: float | None,
    med_elev: float | None,
    use_elev: bool,
    threshold: float = 0.05,
) -> str:
    hr = lap.get("avg_hr")
    elev = lap.get("elevation_gain_m") or 0

    if intensity and avg_intensity and avg_intensity > 0:
        delta = (intensity - avg_intensity) / avg_intensity
        if delta >= threshold:
            return "work"
        if delta <= -threshold:
            return "recovery"

    work_signals = 0
    easy_signals = 0

    if hr and avg_hr and avg_hr > 0:
        hr_delta = (hr - avg_hr) / avg_hr
        if hr_delta >= threshold:
            work_signals += 1
        elif hr_delta <= -threshold:
            easy_signals += 1

    if use_elev and med_elev is not None:
        elev_delta = (elev - med_elev) / max(med_elev, 1)
        if elev_delta >= threshold:
            work_signals += 1
        elif elev_delta <= -threshold:
            easy_signals += 1

    if intensity and avg_intensity and avg_intensity > 0:
        if abs(intensity - avg_intensity) / avg_intensity <= threshold:
            hr_up = hr and avg_hr and (hr - avg_hr) / avg_hr >= threshold
            elev_up = use_elev and (elev - med_elev) / max(med_elev, 1) >= threshold
            if hr_up and elev_up:
                work_signals += 1

    if work_signals >= 2:
        return "work"
    if easy_signals >= 2:
        return "recovery"
    return "steady"


def _apply_split_to_split_phases_cycling(rows: list[dict], threshold_pct: float = 5.0) -> None:
    """After work, recovery only if intensity dropped vs prev and no longer above ride avg."""
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]
        vs_prev = cur.get("intensity_pct_prev_lap")
        if vs_prev is None:
            continue
        intensity_pct = cur.get("intensity_pct")
        if prev["phase"] == "work" and vs_prev <= -threshold_pct:
            if intensity_pct is None or intensity_pct <= threshold_pct:
                cur["phase"] = "recovery"
        elif prev["phase"] == "recovery" and vs_prev >= threshold_pct:
            if intensity_pct is not None and intensity_pct >= threshold_pct:
                cur["phase"] = "work"


def _apply_consecutive_intensity_carry(rows: list[dict], value_key: str, threshold: float = 0.05) -> None:
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]
        v0 = prev.get(value_key)
        v1 = cur.get(value_key)
        if not v0 or not v1 or v0 <= 0:
            continue
        if abs(v1 - v0) / v0 > threshold:
            continue
        if prev["phase"] in ("work", "recovery"):
            cur["phase"] = prev["phase"]


def _apply_cycling_warmup_cooldown(rows: list[dict]) -> None:
    first_work = next((i for i, row in enumerate(rows) if row["phase"] == "work"), None)
    if first_work is not None:
        for i in range(first_work):
            if rows[i]["phase"] == "steady":
                rows[i]["phase"] = "warmup"
    last_work = max((i for i, row in enumerate(rows) if row["phase"] == "work"), default=-1)
    if last_work >= 0:
        for i in range(last_work + 1, len(rows)):
            if rows[i]["phase"] in ("steady", "warmup"):
                rows[i]["phase"] = "cooldown"


def _apply_split_to_split_phases(rows: list[dict], threshold_pct: float = 5.0) -> None:
    """Work then much slower vs previous split -> recovery; fast lap after rest -> work."""
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]
        vs_prev = cur.get("pace_pct_prev_lap")
        if vs_prev is None:
            continue
        if prev["phase"] == "work" and vs_prev >= threshold_pct:
            cur["phase"] = "recovery"
        elif prev["phase"] == "recovery" and vs_prev <= -threshold_pct:
            pace_pct = cur.get("pace_pct")
            if pace_pct is not None and pace_pct <= -threshold_pct:
                cur["phase"] = "work"


def _apply_consecutive_pace_carry(rows: list[dict], threshold: float = 0.05) -> None:
    """Same pace as previous lap (~0%) -> same phase (e.g. work + work)."""
    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]
        p0 = prev.get("pace_s_km")
        p1 = cur.get("pace_s_km")
        if not p0 or not p1 or p0 <= 0:
            continue
        if abs(p1 - p0) / p0 > threshold:
            continue
        if prev["phase"] in ("work", "recovery"):
            cur["phase"] = prev["phase"]


def _activity_avg_power_w(laps: list[dict]) -> float | None:
    weighted_num = 0.0
    weighted_den = 0.0
    for lap in laps:
        power = cycling_lap_power_w(lap)
        duration = _lap_duration(lap)
        if power is not None and duration:
            weighted_num += float(power) * float(duration)
            weighted_den += float(duration)
    if weighted_den > 0:
        return weighted_num / weighted_den
    return _mean([cycling_lap_power_w(l) for l in laps])


def _activity_avg_speed_kmh(laps: list[dict], activity_row=None) -> float | None:
    weighted_num = 0.0
    weighted_den = 0.0
    for lap in laps:
        speed = lap.get("avg_speed_kmh")
        duration = _lap_duration(lap)
        if speed is not None and duration:
            weighted_num += float(speed) * float(duration)
            weighted_den += float(duration)
    if weighted_den > 0:
        return weighted_num / weighted_den
    avg = _activity_speed_kmh(activity_row) if activity_row is not None else None
    if avg is not None:
        return avg
    return _mean([l.get("avg_speed_kmh") for l in laps])


def build_cycling_lap_analysis(laps: list[dict], activity_row=None) -> list[dict[str, Any]]:
    """Per-lap NP% or Spd% vs ride avg; phase from intensity vs ride avg (+ split rules)."""
    if not laps:
        return []

    prefer_power = cycling_ride_uses_power(laps)
    ride_metric = "normalized_power" if prefer_power else "speed"
    avg_power = _activity_avg_power_w(laps) if prefer_power else None
    avg_speed = _activity_avg_speed_kmh(laps, activity_row)
    avg_intensity = avg_power if prefer_power else avg_speed

    avg_hr = _activity_avg_hr(activity_row)
    if avg_hr is None:
        avg_hr = _mean([l.get("avg_hr") for l in laps])
    if avg_speed is None:
        avg_speed = _mean([l.get("avg_speed_kmh") for l in laps])

    med_elev = _median([l.get("elevation_gain_m") for l in laps])
    use_elev = med_elev is not None and med_elev > 3

    rows: list[dict[str, Any]] = []
    prev_intensity: float | None = None
    carry_key = "power_w" if prefer_power else "avg_speed_kmh"
    for lap in laps:
        duration_s = _lap_duration(lap)
        kind, intensity = cycling_lap_intensity(lap, prefer_power)
        speed = lap.get("avg_speed_kmh")
        power = cycling_lap_power_w(lap)
        phase = _classify_cycling_lap_phase(
            intensity, avg_intensity, lap, avg_hr, med_elev, use_elev
        )
        intensity_pct = _pct_vs_baseline(intensity, avg_intensity)
        row = {
            "split": str(lap.get("split", "")),
            "duration_s": round(duration_s) if duration_s else None,
            "duration": format_duration(duration_s) if duration_s else None,
            "distance_km": lap.get("distance_km"),
            "ride_intensity_metric": ride_metric,
            "lap_intensity_kind": kind,
            "power_w": round(power) if power is not None else None,
            "avg_speed_kmh": round(speed, 1) if speed is not None else None,
            "avg_hr": lap.get("avg_hr"),
            "elevation_gain_m": lap.get("elevation_gain_m"),
            "intensity_pct": intensity_pct,
            "intensity_pct_prev_lap": _pct_vs_baseline(intensity, prev_intensity),
            "power_pct": _pct_vs_baseline(power, avg_power) if avg_power else None,
            "power_pct_prev_lap": _pct_vs_baseline(power, prev_intensity if kind == "power" else None),
            "speed_pct": _pct_vs_baseline(speed, avg_speed),
            "hr_pct": _pct_vs_baseline(lap.get("avg_hr"), avg_hr),
            "elev_pct": _pct_vs_baseline(lap.get("elevation_gain_m"), med_elev)
            if use_elev
            else None,
            "phase": phase,
        }
        rows.append(row)
        if intensity is not None:
            prev_intensity = intensity

    _apply_split_to_split_phases_cycling(rows)
    _apply_consecutive_intensity_carry(rows, carry_key)
    _apply_cycling_warmup_cooldown(rows)
    return rows


def classify_cycling_phases(laps: list[dict], activity_row=None) -> list[str]:
    return [row["phase"] for row in build_cycling_lap_analysis(laps, activity_row)]


def build_running_lap_analysis(laps: list[dict], activity_row=None) -> list[dict[str, Any]]:
    """One row per lap; Pace% vs activity average pace (negative = faster)."""
    if not laps:
        return []

    avg_pace = _activity_avg_pace_s_km(activity_row)
    if avg_pace is None:
        avg_pace = _mean([l.get("avg_pace_s_km") for l in laps])

    avg_hr = _activity_avg_hr(activity_row)
    if avg_hr is None:
        avg_hr = _mean([l.get("avg_hr") for l in laps])

    med_elev = _median([l.get("elevation_gain_m") for l in laps])
    use_elev = med_elev is not None and med_elev > 3

    rows: list[dict[str, Any]] = []
    prev_pace_s: float | None = None
    for lap in laps:
        duration_s = _lap_duration(lap)
        pace_s = lap.get("avg_pace_s_km")
        phase = _classify_lap_phase(lap, avg_pace, avg_hr, med_elev, use_elev)
        row = {
            "split": str(lap.get("split", "")),
            "duration_s": round(duration_s) if duration_s else None,
            "duration": format_duration(duration_s) if duration_s else None,
            "distance_km": lap.get("distance_km"),
            "pace_s_km": round(pace_s) if pace_s else None,
            "pace": format_pace(pace_s) if pace_s else None,
            "avg_hr": lap.get("avg_hr"),
            "elevation_gain_m": lap.get("elevation_gain_m"),
            "pace_pct": _pct_vs_baseline(pace_s, avg_pace),
            "pace_pct_prev_lap": _pct_vs_baseline(pace_s, prev_pace_s),
            "hr_pct": _pct_vs_baseline(lap.get("avg_hr"), avg_hr),
            "elev_pct": _pct_vs_baseline(lap.get("elevation_gain_m"), med_elev)
            if use_elev
            else None,
            "phase": phase,
            "auto_km_lap": _is_full_km_lap(lap),
        }
        rows.append(row)
        if pace_s:
            prev_pace_s = pace_s

    _apply_split_to_split_phases(rows)
    _apply_consecutive_pace_carry(rows)
    return rows


def classify_running_phases(laps: list[dict], activity_row=None) -> list[str]:
    return [row["phase"] for row in build_running_lap_analysis(laps, activity_row)]


def _fmt_cell(value, width, align=">"):
    text = "--" if value is None else str(value)
    return f"{text:{align}{width}}"


def format_lap_table(analysis: list[dict]) -> str:
    if not analysis:
        return "(no laps)"
    row0 = analysis[0]
    if row0.get("pace_s_km") is not None:
        return _format_running_lap_table(analysis)
    if row0.get("ride_intensity_metric") == "speed":
        return _format_cycling_speed_lap_table(analysis)
    return _format_cycling_lap_table(analysis)


def _format_running_lap_table(analysis: list[dict]) -> str:
    if not analysis:
        return "(no laps)"
    lines = [
        f"{'Split':>6} {'Dist':>6} {'Time':>8} {'Pace':>8} {'Pace%':>7} {'vsPrev':>7} "
        f"{'HR':>4} {'HR%':>6} {'Elev':>5} {'Elev%':>6} {'Phase':>9} {'1km?':>5}",
        "-" * 94,
    ]
    for row in analysis:
        dist = row.get("distance_km")
        dist_s = f"{dist:.2f}" if dist is not None else "--"
        lines.append(
            f"{_fmt_cell(row.get('split'), 6)} "
            f"{dist_s:>6} "
            f"{_fmt_cell(row.get('duration'), 8)} "
            f"{_fmt_cell(row.get('pace'), 8)} "
            f"{_fmt_cell(row.get('pace_pct'), 7)} "
            f"{_fmt_cell(row.get('pace_pct_prev_lap'), 7)} "
            f"{_fmt_cell(row.get('avg_hr'), 4, '>'):>4} "
            f"{_fmt_cell(row.get('hr_pct'), 6)} "
            f"{_fmt_cell(row.get('elevation_gain_m'), 5, '>'):>5} "
            f"{_fmt_cell(row.get('elev_pct'), 6)} "
            f"{_fmt_cell(row.get('phase'), 9)} "
            f"{('yes' if row.get('auto_km_lap') else 'no'):>5}"
        )
    lines.append("")
    lines.append("Pace% vs activity avg pace; vsPrev vs previous lap (0% = same speed).")
    return "\n".join(lines)


def _format_cycling_lap_table(analysis: list[dict]) -> str:
    lines = [
        f"{'Split':>6} {'Dist':>6} {'Time':>8} {'NP':>6} {'NP%':>7} {'vsPrev':>7} "
        f"{'Spd':>5} {'Spd%':>6} {'HR':>4} {'HR%':>6} {'Elev':>5} {'Elev%':>6} {'Phase':>9}",
        "-" * 96,
    ]
    for row in analysis:
        dist = row.get("distance_km")
        dist_s = f"{dist:.2f}" if dist is not None else "--"
        spd = row.get("avg_speed_kmh")
        spd_s = f"{spd:.1f}" if spd is not None else "--"
        lines.append(
            f"{_fmt_cell(row.get('split'), 6)} "
            f"{dist_s:>6} "
            f"{_fmt_cell(row.get('duration'), 8)} "
            f"{_fmt_cell(row.get('power_w'), 6)} "
            f"{_fmt_cell(row.get('power_pct') or row.get('intensity_pct'), 7)} "
            f"{_fmt_cell(row.get('power_pct_prev_lap') or row.get('intensity_pct_prev_lap'), 7)} "
            f"{spd_s:>5} "
            f"{_fmt_cell(row.get('speed_pct'), 6)} "
            f"{_fmt_cell(row.get('avg_hr'), 4, '>'):>4} "
            f"{_fmt_cell(row.get('hr_pct'), 6)} "
            f"{_fmt_cell(row.get('elevation_gain_m'), 5, '>'):>5} "
            f"{_fmt_cell(row.get('elev_pct'), 6)} "
            f"{_fmt_cell(row.get('phase'), 9)}"
        )
    lines.append("")
    lines.append(
        "NP%/Spd%/HR%/Elev% vs ride averages (NP when available; else speed for phases). "
        "vsPrev = same metric as NP%. Work when intensity ≥5% above ride avg."
    )
    return "\n".join(lines)


def _format_cycling_speed_lap_table(analysis: list[dict]) -> str:
    lines = [
        f"{'Split':>6} {'Dist':>6} {'Time':>8} {'Spd':>5} {'Spd%':>7} {'vsPrev':>7} "
        f"{'HR':>4} {'HR%':>6} {'Elev':>5} {'Elev%':>6} {'Phase':>9}",
        "-" * 88,
    ]
    for row in analysis:
        dist = row.get("distance_km")
        dist_s = f"{dist:.2f}" if dist is not None else "--"
        spd = row.get("avg_speed_kmh")
        spd_s = f"{spd:.1f}" if spd is not None else "--"
        lines.append(
            f"{_fmt_cell(row.get('split'), 6)} "
            f"{dist_s:>6} "
            f"{_fmt_cell(row.get('duration'), 8)} "
            f"{spd_s:>5} "
            f"{_fmt_cell(row.get('intensity_pct') or row.get('speed_pct'), 7)} "
            f"{_fmt_cell(row.get('intensity_pct_prev_lap'), 7)} "
            f"{_fmt_cell(row.get('avg_hr'), 4, '>'):>4} "
            f"{_fmt_cell(row.get('hr_pct'), 6)} "
            f"{_fmt_cell(row.get('elevation_gain_m'), 5, '>'):>5} "
            f"{_fmt_cell(row.get('elev_pct'), 6)} "
            f"{_fmt_cell(row.get('phase'), 9)}"
        )
    lines.append("")
    lines.append("No power on this ride — Spd% vs ride avg speed drives work/recovery.")
    return "\n".join(lines)
