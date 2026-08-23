"""Merge consecutive splits into blocks and detect repeated work patterns (e.g. 2x5')."""

from __future__ import annotations

import statistics
from typing import Any

from utils.pipeline.workout_summaries.parse_laps import format_duration, format_pace

ROUND_DURATION_S = [60, 90, 120, 180, 240, 300, 360, 480, 600, 720, 900, 1200, 1500, 1800, 2400, 3600]
ROUND_DISTANCE_M = [400, 600, 800, 1000, 1200, 1600, 2000, 2400, 3000, 5000]
ROUND_TOLERANCE_S = 15
DISTANCE_TOLERANCE_PCT = 0.07
SAME_PACE_PCT = 5.0
REST_PACE_PCT = 30.0
WORK_BLOCKS_MATCH_S = 20
WORK_PACE_MATCH_PCT = 6.0

# Running pace zones (seconds/km) — used for block kind, not athlete-specific zones.
EF_PACE_S_KM = 285  # 4:45/km — endurance fundamental / easy
THRESHOLD_PACE_S_KM = 260  # 4:20/km — faster than this is VO2/interval territory


def _lap_duration_s(lap: dict) -> int:
    raw = lap.get("moving_time_s") or lap.get("time_s")
    return int(round(float(raw))) if raw is not None else 0


def _lap_pace_s_km(lap: dict) -> float | None:
    pace = lap.get("avg_pace_s_km")
    return float(pace) if pace is not None else None


def _pace_delta_pct(curr: float, prev: float) -> float:
    return (curr - prev) / prev * 100.0


def _same_pace(curr: float, prev: float) -> bool:
    return abs(_pace_delta_pct(curr, prev)) < SAME_PACE_PCT


def _is_rest_vs_prev(lap: dict, prev: dict) -> bool:
    curr_pace = _lap_pace_s_km(lap)
    prev_pace = _lap_pace_s_km(prev)
    if curr_pace is None or prev_pace is None or prev_pace <= 0:
        return False
    return _pace_delta_pct(curr_pace, prev_pace) >= REST_PACE_PCT


def _activity_avg_pace_s_km(laps: list[dict], activity_row: Any = None) -> float | None:
    if activity_row is not None:
        duration = activity_row.get("duration")
        distance = activity_row.get("distance")
        if duration and distance and float(distance) > 0:
            return float(duration) / float(distance)
    paces = [_lap_pace_s_km(lap) for lap in laps]
    clean = [p for p in paces if p is not None]
    return float(statistics.mean(clean)) if clean else None


def _is_work_pace(pace_s_km: float | None, activity_avg: float | None) -> bool:
    if pace_s_km is None or activity_avg is None or activity_avg <= 0:
        return False
    return pace_s_km < activity_avg * 0.93


def rounded_distance_label(distance_km: float) -> str | None:
    """Match standard track/road rep distances (800m, 1km, 1600m, …)."""
    if distance_km <= 0:
        return None
    dist_m = distance_km * 1000.0
    best: tuple[int, float] | None = None
    for target in ROUND_DISTANCE_M:
        err = abs(dist_m - target) / target
        if err <= DISTANCE_TOLERANCE_PCT and (best is None or err < best[1]):
            best = (target, err)
    if best is None:
        return None
    target_m = best[0]
    if target_m >= 1000 and target_m % 1000 == 0:
        return f"{target_m // 1000}km"
    if target_m >= 1000:
        return f"{target_m}m"
    return f"{target_m}m"


def rounded_time_label(duration_s: int) -> str | None:
    if duration_s <= 0:
        return None
    best: tuple[int, int] | None = None
    for target in ROUND_DURATION_S:
        diff = abs(duration_s - target)
        if diff <= ROUND_TOLERANCE_S and (best is None or diff < best[1]):
            best = (target, diff)
    if best is None:
        return None
    target = best[0]
    if target < 120:
        return f"{target}s"
    return f"{target // 60}'"


def rest_label(duration_s: int) -> str:
    rounded = rounded_time_label(duration_s)
    if rounded and rounded.endswith("'"):
        mins = int(rounded[:-1])
        return f"R'{mins}\""
    if duration_s >= 60:
        return f"R'{duration_s // 60}\""
    return f"R'{duration_s}s"


def _weighted_pace_s_km(laps: list[dict]) -> float | None:
    num = 0.0
    den = 0.0
    for lap in laps:
        pace = _lap_pace_s_km(lap)
        dist = lap.get("distance_km")
        dur = _lap_duration_s(lap)
        weight = float(dist) if dist else (dur / _lap_pace_s_km(lap) if pace else 0)
        if pace and weight > 0:
            num += pace * weight
            den += weight
    return num / den if den > 0 else None


def _block_from_laps(laps: list[dict], split_start: int, split_end: int) -> dict[str, Any]:
    duration_s = sum(_lap_duration_s(lap) for lap in laps)
    distance_km = sum(float(lap.get("distance_km") or 0) for lap in laps)
    pace_s_km = _weighted_pace_s_km(laps)
    hrs = [lap.get("avg_hr") for lap in laps if lap.get("avg_hr") is not None]
    avg_hr = int(round(statistics.mean(hrs))) if hrs else None
    block: dict[str, Any] = {
        "splits": f"{split_start}-{split_end}" if split_start != split_end else str(split_start),
        "duration_s": duration_s,
        "duration": format_duration(duration_s),
    }
    if distance_km > 0:
        block["distance_km"] = round(distance_km, 2)
        dist_label = rounded_distance_label(distance_km)
        if dist_label:
            block["distance_label"] = dist_label
    if pace_s_km is not None:
        block["avg_pace"] = format_pace(pace_s_km)
        block["avg_pace_s_km"] = round(pace_s_km, 1)
    if avg_hr is not None:
        block["avg_hr"] = avg_hr
    rounded = rounded_time_label(duration_s)
    if rounded:
        block["rounded_time"] = rounded
    return block


def _classify_running_block(
    block: dict[str, Any],
    *,
    is_first: bool,
    is_last: bool,
) -> str:
    """Running-specific: WU/CD only at easy (EF) pace; moderate pace is work."""
    pace = block.get("avg_pace_s_km")
    dist = float(block.get("distance_km") or 0)

    if pace is not None and pace < EF_PACE_S_KM:
        return "work"

    if is_first and dist >= 0.8:
        return "wu"
    if is_last and dist >= 0.5:
        return "cd"
    if block.get("duration_s", 0) <= 180 and pace and pace > EF_PACE_S_KM:
        return "rest"
    return "easy"


def _refine_running_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fix mis-labeled WU when the whole run is easy or block is at threshold pace."""
    if not blocks:
        return blocks

    has_hard = any(
        b.get("kind") in {"work", "intervals"}
        or (b.get("avg_pace_s_km") is not None and b["avg_pace_s_km"] < EF_PACE_S_KM)
        for b in blocks
    )

    if not has_hard:
        for block in blocks:
            if block.get("kind") in {"wu", "cd"}:
                block["kind"] = "easy"
        return blocks

    for block in blocks:
        pace = block.get("avg_pace_s_km")
        if block.get("kind") == "wu" and pace is not None and pace < EF_PACE_S_KM:
            block["kind"] = "work"

    return blocks


def _classify_block(block: dict[str, Any], activity_avg_pace: float | None, *, is_first: bool, is_last: bool) -> str:
    pace = block.get("avg_pace_s_km")
    if _is_work_pace(pace, activity_avg_pace):
        return "work"
    if is_first and block.get("distance_km", 0) >= 1.0:
        return "wu"
    if is_last and block.get("distance_km", 0) >= 0.5:
        return "cd"
    if block.get("duration_s", 0) <= 180 and pace and activity_avg_pace and pace > activity_avg_pace * 1.1:
        return "rest"
    return "easy"


def merge_splits_to_blocks(
    laps: list[dict],
    activity_row: Any = None,
    *,
    sport: str | None = None,
) -> list[dict[str, Any]]:
    """Merge consecutive same-pace splits; break on rest spikes."""
    if not laps:
        return []

    sport_key = (sport or "").lower()
    activity_avg = _activity_avg_pace_s_km(laps, activity_row)
    raw_blocks: list[tuple[list[dict], int, int]] = []
    start_idx = 0
    i = 0

    while i < len(laps):
        chunk = [laps[i]]
        split_start = i + 1
        j = i + 1
        while j < len(laps):
            prev, curr = laps[j - 1], laps[j]
            if _is_rest_vs_prev(curr, prev):
                break
            prev_pace = _lap_pace_s_km(prev)
            curr_pace = _lap_pace_s_km(curr)
            if prev_pace is not None and curr_pace is not None:
                if _same_pace(curr_pace, prev_pace):
                    chunk.append(curr)
                    j += 1
                    continue
                if _is_work_pace(prev_pace, activity_avg) and _is_work_pace(curr_pace, activity_avg):
                    break
            if not _is_work_pace(curr_pace, activity_avg) and not _is_work_pace(prev_pace, activity_avg):
                chunk.append(curr)
                j += 1
                continue
            break
        raw_blocks.append((chunk, split_start, j))
        i = j

    blocks: list[dict[str, Any]] = []
    for idx, (chunk, split_start, end_idx) in enumerate(raw_blocks):
        block = _block_from_laps(chunk, split_start, end_idx)
        if sport_key == "running":
            kind = _classify_running_block(block, is_first=idx == 0, is_last=idx == len(raw_blocks) - 1)
        else:
            kind = _classify_block(
                block,
                activity_avg,
                is_first=idx == 0,
                is_last=idx == len(raw_blocks) - 1,
            )
        block["kind"] = kind
        if kind == "rest":
            block["rest_label"] = rest_label(block["duration_s"])
        blocks.append(block)

    blocks = collapse_repeated_work_blocks(blocks)
    if sport_key == "running":
        blocks = _refine_running_blocks(blocks)
    return blocks


def _work_blocks_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if abs(a.get("duration_s", 0) - b.get("duration_s", 0)) > WORK_BLOCKS_MATCH_S:
        a_round = a.get("rounded_time")
        b_round = b.get("rounded_time")
        if not a_round or a_round != b_round:
            return False
    pace_a = a.get("avg_pace_s_km")
    pace_b = b.get("avg_pace_s_km")
    if pace_a and pace_b and pace_a > 0:
        if abs(_pace_delta_pct(pace_b, pace_a)) > WORK_PACE_MATCH_PCT:
            return False
    return True


def collapse_repeated_work_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse work + rest + work + ... into Nx patterns when work blocks match."""
    if len(blocks) < 3:
        return blocks

    out: list[dict[str, Any]] = []
    i = 0
    while i < len(blocks):
        if blocks[i].get("kind") != "work":
            out.append(blocks[i])
            i += 1
            continue

        reps = 1
        j = i
        work_tpl = blocks[i]
        rest_tpl: dict[str, Any] | None = None

        while j + 2 < len(blocks):
            mid = blocks[j + 1]
            nxt = blocks[j + 2]
            if mid.get("kind") not in {"rest", "easy"}:
                break
            if nxt.get("kind") != "work":
                break
            if not _work_blocks_match(work_tpl, nxt):
                break
            reps += 1
            if rest_tpl is None:
                rest_tpl = mid
            j += 2

        if reps >= 2:
            interval: dict[str, Any] = {
                "kind": "intervals",
                "reps": reps,
                "work_duration_s": work_tpl["duration_s"],
                "splits": f"{work_tpl['splits']} (x{reps})",
            }
            if work_tpl.get("rounded_time"):
                interval["work_rounded"] = work_tpl["rounded_time"]
            if work_tpl.get("distance_km"):
                interval["work_distance_km"] = work_tpl["distance_km"]
            if work_tpl.get("distance_label"):
                interval["work_distance_label"] = work_tpl["distance_label"]
            if work_tpl.get("avg_pace"):
                interval["avg_pace"] = work_tpl["avg_pace"]
            if work_tpl.get("avg_hr"):
                interval["avg_hr"] = work_tpl["avg_hr"]
            if rest_tpl:
                interval["rest_duration_s"] = rest_tpl["duration_s"]
                interval["rest_label"] = rest_tpl.get("rest_label") or rest_label(rest_tpl["duration_s"])
            out.append(interval)
            i = j + 1
        else:
            out.append(blocks[i])
            i += 1

    return out


def blocks_for_llm(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip internal fields before sending to LLM."""
    cleaned = []
    for block in blocks:
        row = {k: v for k, v in block.items() if k not in {"avg_pace_s_km"}}
        cleaned.append(row)
    return cleaned
