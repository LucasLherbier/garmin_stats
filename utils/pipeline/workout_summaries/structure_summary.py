"""One-line description of the main workout pattern (for coach / LLM context)."""

from __future__ import annotations

import statistics
from typing import Any

from utils.pipeline.workout_summaries.parse_laps import activity_scalar
from utils.pipeline.workout_summaries.segments import format_duration_short


def _avg(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return float(statistics.mean(clean)) if clean else None


def _intense_hills_in_work(laps: list[dict] | None, phases: list[str] | None) -> bool:
    if not laps or not phases or len(laps) != len(phases):
        return False
    work_elevs = [
        float(lap["elevation_gain_m"])
        for lap, phase in zip(laps, phases)
        if phase == "work" and lap.get("elevation_gain_m") is not None
    ]
    if not work_elevs:
        return False
    all_elevs = [float(lap["elevation_gain_m"]) for lap in laps if lap.get("elevation_gain_m") is not None]
    med = statistics.median(all_elevs) if all_elevs else 0
    hard_climbs = sum(1 for e in work_elevs if e >= max(50, med * 2.5))
    return hard_climbs >= 2 or max(work_elevs) >= 80


def build_main_structure_summary(
    segments: list[dict],
    sport: str,
    activity_row=None,
    laps: list[dict] | None = None,
    phases: list[str] | None = None,
) -> str | None:
    """Human-readable main set (not every segment). LLM can refine later in tab_race."""
    if not segments:
        return None

    duration_s = activity_scalar(activity_row, "duration") if activity_row is not None else None
    duration_h = float(duration_s) / 3600 if duration_s else None

    interval = next((s for s in segments if s.get("phase") == "intervals"), None)
    work_segments = [s for s in segments if s.get("phase") == "work"]
    hills = _intense_hills_in_work(laps, phases)

    if sport == "cycling":
        prefix = "Long Ride" if duration_h and duration_h >= 2.0 else "Ride"
        core: str | None = None

        if interval:
            reps = interval.get("reps")
            work_s = interval.get("work_duration_s")
            if reps and work_s:
                mins = max(1, round(work_s / 60))
                hr = interval.get("avg_hr")
                watts = interval.get("avg_power_w")
                if hr:
                    core = f"{reps}×{mins}min ~{hr} Avg HR"
                elif watts:
                    core = f"{reps}×{mins}min ~{watts}W"
                else:
                    core = f"{reps}×{mins}min"
        elif work_segments:
            work_hrs = _avg([s.get("avg_hr") for s in work_segments])
            if duration_h and duration_h >= 2.5 and len(work_segments) >= 2:
                if work_hrs:
                    core = f"sustained mixed efforts ~{round(work_hrs)} Avg HR"
                else:
                    core = "sustained mixed efforts"
            elif work_segments:
                longest = max(work_segments, key=lambda s: s.get("duration_s") or 0)
                dur = format_duration_short(longest.get("duration_s"))
                hr = longest.get("avg_hr")
                if dur and hr:
                    core = f"main block {dur} ~{hr} Avg HR"
                elif dur:
                    core = f"main block {dur}"

        if not core:
            return prefix

        line = f"{prefix} - {core}"
        if hills:
            line += " - with additional intense hills"
        return line

    if sport == "running":
        if interval:
            reps = interval.get("reps")
            dist = interval.get("rep_distance_km")
            pace = interval.get("avg_pace_s_km")
            parts = []
            if reps and dist:
                parts.append(f"{reps}×{dist} km")
            if pace:
                m, s = divmod(int(round(pace)), 60)
                parts.append(f"@ {m}:{s:02d}/km")
            core = " ".join(parts) if parts else "intervals"
            prefix = "Long run" if duration_h and duration_h >= 1.5 else "Run"
            line = f"{prefix} - {core}"
            if hills:
                line += " - hilly"
            return line

        if duration_h and duration_h >= 1.25:
            return "Long run - steady distance" + (" - hilly" if hills else "")
        return None

    return None
