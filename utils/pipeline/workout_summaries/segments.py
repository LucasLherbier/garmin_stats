"""Detect workout structure (intervals by time or distance) from normalized laps."""

from __future__ import annotations

import json
import statistics
from typing import Any

import numpy as np

from utils.pipeline.workout_summaries.lap_analysis import classify_cycling_phases, classify_running_phases
from utils.pipeline.workout_summaries.parse_laps import cycling_lap_intensity, cycling_lap_power_w


def _lap_duration(lap: dict) -> float | None:
    return lap.get("moving_time_s") or lap.get("time_s")


def _is_full_km_lap(lap: dict) -> bool:
    d = lap.get("distance_km")
    return d is not None and 0.85 <= d <= 1.15


def _full_km_laps(laps: list[dict]) -> list[dict]:
    return [lap for lap in laps if _is_full_km_lap(lap)]


def _lap_intensity(lap: dict, sport: str) -> float | None:
    if sport == "running":
        pace = lap.get("avg_pace_s_km")
        if pace and pace > 0:
            return 1000.0 / pace
        duration = _lap_duration(lap)
        distance = lap.get("distance_km")
        if duration and distance and duration > 0:
            return distance * 1000.0 / duration
    if sport == "cycling":
        _kind, intensity = cycling_lap_intensity(lap, prefer_power=True)
        if intensity is not None:
            return intensity
        speed = lap.get("avg_speed_kmh")
        if speed is not None:
            return speed
    if sport == "swimming":
        if lap.get("is_rest"):
            return None
        pace = lap.get("avg_pace_s_100m")
        if pace and pace > 0:
            return 100.0 / pace
    return None


def _total_distance_km(laps: list[dict]) -> float:
    return sum(l.get("distance_km") or 0 for l in laps)


def _median(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    return float(statistics.median(clean)) if clean else None


def _is_steady_distance_run(laps: list[dict], phases: list[str] | None = None, activity_row=None) -> bool:
    full_km = _full_km_laps(laps)
    if len(full_km) < 8:
        return False
    total = _total_distance_km(laps)
    full_dist = _total_distance_km(full_km)
    if total <= 0 or full_dist < total * 0.65:
        return False
    if phases is None:
        phases = classify_running_phases(laps, activity_row)
    full_km_phases = [phases[i] for i, lap in enumerate(laps) if _is_full_km_lap(lap)]
    if len(full_km_phases) < 8:
        return False
    return full_km_phases.count("steady") / len(full_km_phases) >= 0.70


def _detect_running_segments(laps: list[dict], activity_row=None) -> list[dict]:
    phases = classify_running_phases(laps, activity_row)
    full_km = _full_km_laps(laps)

    if _is_steady_distance_run(laps, phases, activity_row):
        rep_km = round(statistics.median([l["distance_km"] for l in full_km]), 2)
        return [
            {
                "phase": "steady",
                "basis": "distance",
                "label": f"Steady run - {len(laps)} laps ({len(full_km)}x{rep_km} km auto-splits)",
                "rep_distance_km": rep_km,
                "reps": len(full_km),
                "lap_splits": [str(l.get("split")) for l in laps],
                "avg_pace_s_km": round(_avg([l.get("avg_pace_s_km") for l in full_km]) or 0) or None,
            }
        ]

    merged = _merge_by_phase(laps, phases, "running")

    work_blocks = [b for b in merged if b["phase"] == "work"]
    if len(work_blocks) >= 2 and _running_interval_pattern(work_blocks):
        rest_blocks = [b for b in merged if b["phase"] == "recovery"]
        rest_pace = _avg([b.get("avg_pace_s_km") for b in rest_blocks])
        interval = {
            "phase": "intervals",
            "basis": "distance",
            "label": _format_run_interval_label(work_blocks, rest_blocks),
            "reps": sum(len(b["lap_indices"]) for b in work_blocks),
            "rep_distance_km": round(
                statistics.median(
                    [
                        l.get("distance_km")
                        for b in work_blocks
                        for l in [laps[i] for i in b["lap_indices"]]
                        if l.get("distance_km")
                    ]
                ),
                2,
            ),
            "avg_pace_s_km": round(_avg([b.get("avg_pace_s_km") for b in work_blocks]) or 0) or None,
            "rest_avg_pace_s_km": round(rest_pace) if rest_pace else None,
            "lap_splits": [s for b in work_blocks for s in b["lap_splits"]],
        }
        segments = [interval]
    else:
        segments = [_block_to_segment(block, "running") for block in merged]

    return segments


def _running_interval_pattern(work_blocks: list[dict]) -> bool:
    rep_counts = [len(b["lap_indices"]) for b in work_blocks]
    return len(work_blocks) >= 2 and sum(rep_counts) >= 2


def _format_run_interval_label(work_blocks: list[dict], rest_blocks: list[dict]) -> str:
    reps = sum(len(b["lap_indices"]) for b in work_blocks)
    pace = _avg([b.get("avg_pace_s_km") for b in work_blocks])
    pace_str = format_pace_short(pace) if pace else "?"
    parts = [f"{reps}×1 km @ {pace_str}"]
    if rest_blocks:
        parts.append(f"{len(rest_blocks)} recovery km")
    return " - ".join(parts)


def _classify_laps(laps: list[dict], sport: str) -> list[str]:
    if not laps:
        return []

    intensities = [_lap_intensity(lap, sport) for lap in laps]
    valid = [v for v in intensities if v is not None]
    if not valid:
        return ["steady"] * len(laps)

    median = float(np.median(valid))
    p25 = float(np.percentile(valid, 25))
    p75 = float(np.percentile(valid, 75))
    spread = (p75 - p25) / median if median > 0 else 0

    if spread < 0.08:
        return ["steady"] * len(laps)

    phases: list[str] = []
    prev: str | None = None
    for idx, lap in enumerate(laps):
        if sport == "swimming" and lap.get("is_rest"):
            phases.append("recovery")
            prev = "recovery"
            continue

        duration = _lap_duration(lap) or 0
        intensity = intensities[idx]
        if intensity is None:
            phases.append("steady")
            prev = "steady"
            continue

        is_recovery = intensity <= p25 * 1.02 or intensity < median * 0.9
        is_work = intensity >= p75 * 0.98 or intensity > median * 1.1

        if sport == "cycling" and prev == "work" and duration <= 480:
            prev_lap = laps[idx - 1]
            prev_power = cycling_lap_power_w(prev_lap)
            cur_power = cycling_lap_power_w(lap)
            if prev_power and cur_power and cur_power < prev_power * 0.92:
                phases.append("recovery")
                prev = "recovery"
                continue

        if is_recovery and (prev == "work" or duration <= 600):
            phases.append("recovery")
            prev = "recovery"
            continue

        if is_work and duration >= 45:
            phases.append("work")
            prev = "work"
            continue

        if idx == 0 and intensity < median * 0.95:
            phases.append("warmup")
            prev = "warmup"
            continue

        phases.append("steady")
        prev = "steady"

    first_work = next((i for i, p in enumerate(phases) if p == "work"), None)
    if first_work is not None:
        for i in range(first_work):
            if phases[i] == "steady":
                phases[i] = "warmup"

    last_work = max((i for i, p in enumerate(phases) if p == "work"), default=-1)
    if last_work >= 0:
        for i in range(last_work + 1, len(phases)):
            if phases[i] in ("steady", "warmup"):
                phases[i] = "cooldown"

    return phases


def _avg(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return float(statistics.mean(clean))


def _similar_durations(durations: list[float], tolerance: float = 0.18) -> bool:
    if len(durations) < 2:
        return True
    med = statistics.median(durations)
    if med <= 0:
        return False
    return all(abs(d - med) / med <= tolerance for d in durations)


def _similar_distances(distances: list[float], tolerance: float = 0.15) -> bool:
    if len(distances) < 2:
        return True
    med = statistics.median(distances)
    if med <= 0:
        return False
    return all(abs(d - med) / med <= tolerance for d in distances)


def _merge_by_phase(laps: list[dict], phases: list[str], sport: str) -> list[dict]:
    merged: list[dict] = []
    for idx, (lap, phase) in enumerate(zip(laps, phases)):
        if merged and merged[-1]["phase"] == phase:
            block = merged[-1]
        else:
            block = {"phase": phase, "lap_indices": [], "lap_splits": []}
            merged.append(block)
        block["lap_indices"].append(idx)
        block["lap_splits"].append(str(lap.get("split")))

    for block in merged:
        block_laps = [laps[i] for i in block["lap_indices"]]
        durations = [_lap_duration(l) for l in block_laps]
        if sport == "swimming":
            distances_m = [l.get("distance_m") for l in block_laps if not l.get("is_rest")]
            block["distance_m"] = sum(d or 0 for d in distances_m)
        else:
            block["distance_km"] = sum(l.get("distance_km") or 0 for l in block_laps)

        block["duration_s"] = sum(d or 0 for d in durations)
        block["avg_hr"] = _avg([l.get("avg_hr") for l in block_laps])
        if sport == "cycling":
            block["avg_power_w"] = _avg([cycling_lap_power_w(l) for l in block_laps])
            block["avg_speed_kmh"] = _avg([l.get("avg_speed_kmh") for l in block_laps])
        if sport == "running":
            block["avg_pace_s_km"] = _avg([l.get("avg_pace_s_km") for l in block_laps])

    return merged


def _block_to_segment(block: dict, sport: str) -> dict:
    phase = block["phase"]
    seg: dict[str, Any] = {
        "phase": phase,
        "lap_splits": block["lap_splits"],
        "duration_s": round(block["duration_s"]) if block.get("duration_s") else None,
    }
    if block.get("distance_km") is not None:
        seg["distance_km"] = round(block["distance_km"], 2)
    if block.get("avg_hr"):
        seg["avg_hr"] = round(block["avg_hr"])
    if sport == "running" and block.get("avg_pace_s_km"):
        seg["avg_pace_s_km"] = round(block["avg_pace_s_km"])
        seg["label"] = (
            f"{phase.title()} - {format_pace_short(block['avg_pace_s_km'])} "
            f"- splits {block['lap_splits'][0]}-{block['lap_splits'][-1]}"
        )
    elif sport == "cycling" and block.get("avg_power_w"):
        seg["avg_power_w"] = round(block["avg_power_w"])
        seg["label"] = (
            f"{phase.title()} - ~{round(block['avg_power_w'])}W - "
            f"{format_duration_short(block.get('duration_s'))}"
        )
    else:
        seg["label"] = phase.title()
    return seg


def _extract_interval_set(merged: list[dict], sport: str) -> dict | None:
    work_blocks = [
        b for b in merged if b["phase"] == "work" and (b.get("duration_s") or 0) <= 3600
    ]
    if len(work_blocks) < 2:
        return None

    work_per_rep_durations = []
    for block in work_blocks:
        if len(block["lap_indices"]) == 1:
            work_per_rep_durations.append(block["duration_s"])
        else:
            work_per_rep_durations.append(block["duration_s"] / max(len(block["lap_indices"]), 1))

    if not _similar_durations(work_per_rep_durations):
        return None

    rest_blocks = [b for b in merged if b["phase"] == "recovery"]
    rest_durations = [b["duration_s"] for b in rest_blocks if b.get("duration_s")]
    rest_duration_s = _avg(rest_durations) if rest_durations else None

    reps = len(work_blocks)
    work_duration_s = statistics.median(work_per_rep_durations)

    interval: dict[str, Any] = {
        "phase": "intervals",
        "reps": reps,
        "work_duration_s": round(work_duration_s),
        "basis": "time",
        "label": f"{reps}×{format_duration_short(work_duration_s)}",
    }
    if rest_duration_s:
        interval["rest_duration_s"] = round(rest_duration_s)
        interval["label"] += f" - {format_duration_short(rest_duration_s)} rest"

    if sport == "cycling":
        interval["avg_power_w"] = round(_avg([b.get("avg_power_w") for b in work_blocks]) or 0) or None
        interval["avg_hr"] = round(_avg([b.get("avg_hr") for b in work_blocks]) or 0) or None
        if interval.get("avg_power_w"):
            interval["label"] += f" - ~{interval['avg_power_w']}W"
    if sport == "running":
        interval["avg_pace_s_km"] = _avg([b.get("avg_pace_s_km") for b in work_blocks])
        if interval.get("avg_pace_s_km"):
            interval["label"] += f" - {format_pace_short(interval['avg_pace_s_km'])}"

    interval["lap_splits"] = [split for b in work_blocks for split in b["lap_splits"]]
    return interval


def detect_segments(laps: list[dict], sport: str, activity_row=None) -> list[dict]:
    if not laps:
        return []

    if sport == "swimming":
        return _detect_swim_segments(laps)

    if sport == "running":
        return _detect_running_segments(laps, activity_row)

    if sport == "cycling":
        phases = classify_cycling_phases(laps, activity_row)
    else:
        phases = _classify_laps(laps, sport)
    merged = _merge_by_phase(laps, phases, sport)

    interval_set = _extract_interval_set(merged, sport)
    if interval_set:
        segments: list[dict] = []
        for block in merged:
            if block["phase"] == "warmup":
                segments.append(_block_to_segment(block, sport))
        segments.append(interval_set)
        for block in merged:
            if block["phase"] == "cooldown":
                segments.append(_block_to_segment(block, sport))
        return segments

    return [_block_to_segment(block, sport) for block in merged]


def _detect_swim_segments(laps: list[dict]) -> list[dict]:
    segments: list[dict] = []
    current_work: list[dict] = []

    def flush_work():
        if not current_work:
            return
        segments.append(
            {
                "phase": "work",
                "basis": "distance",
                "reps": len(current_work),
                "rep_distance_m": _avg([l.get("distance_m") for l in current_work]),
                "avg_pace_s_100m": _avg([l.get("avg_pace_s_100m") for l in current_work]),
                "lap_splits": [str(l.get("split")) for l in current_work],
                "label": f"{len(current_work)}×{int(_avg([l.get('distance_m') for l in current_work]) or 0)}m",
            }
        )
        current_work.clear()

    for lap in laps:
        if lap.get("is_rest"):
            flush_work()
            segments.append(
                {
                    "phase": "recovery",
                    "duration_s": round(lap.get("time_s") or 0),
                    "lap_splits": [str(lap.get("split"))],
                    "label": f"Rest · {format_duration_short(lap.get('time_s'))}",
                }
            )
            continue
        if lap.get("distance_m") and lap["distance_m"] <= 50:
            current_work.append(lap)
        else:
            flush_work()
            segments.append(
                {
                    "phase": "steady",
                    "distance_m": lap.get("distance_m"),
                    "duration_s": round(lap.get("time_s") or 0),
                    "lap_splits": [str(lap.get("split"))],
                    "label": "Steady swim block",
                }
            )
    flush_work()
    return segments


def format_duration_short(seconds: float | None) -> str | None:
    if not seconds:
        return None
    seconds = int(round(seconds))
    if seconds >= 3600:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"
    m, s = divmod(seconds, 60)
    if m >= 1:
        return f"{m}:{s:02d}"
    return f"{s}s"


def format_pace_short(seconds_per_km: float | None) -> str | None:
    if not seconds_per_km:
        return None
    seconds_per_km = int(round(seconds_per_km))
    return f"{seconds_per_km // 60}:{seconds_per_km % 60:02d}/km"


def describe_segments(segments: list[dict], sport: str) -> str | None:
    if not segments:
        return None
    labels = [s.get("label") for s in segments if s.get("label") and s.get("phase") != "partial"]
    return " | ".join(labels) if labels else None


def format_segments_for_log(segments: list[dict]) -> str:
    if not segments:
        return "(none)"
    lines = []
    for seg in segments:
        lines.append(f"  - {seg.get('label') or seg.get('phase')}")
    return "\n".join(lines)
