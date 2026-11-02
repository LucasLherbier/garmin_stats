"""Per-lap facts for the AI summary — plumbing only (v5).

Design decision (Lucas, 2026-10-29): the summary is 100% AI. His
sessions are mostly watch AUTOLAPS (1 km) plus occasional manual
presses, so repetitions are smaller than a lap or straddle two laps —
no lap-level structure exists for Python to merge or validate, and
every attempt to gate the model on lap ranges produced false
rejections or let the original hallucination through. Python's job
is therefore only to compute honest per-lap NUMBERS and hand the
model the complete table:

- grade-adjusted pace per run lap (Minetti cost, climbs and descents
  decomposed — net grade misprices mixed laps),
- cadence normalized to steps/min (decided from the data: some
  exports give per-leg cadence ~84, others steps/min ~170),
- bike intensity per lap (NP, else avg power),
- micro-laps (a few seconds / metres) ANNOTATED as artifacts, not
  deleted — the model is told to ignore them for structure.

No blocks, no merge, no validation gate in this module anymore.
"""

from __future__ import annotations

import statistics
from typing import Any

# ---------------------------------------------------------------------------
# GAP (grade-adjusted pace) — Minetti et al. metabolic cost of running
# ---------------------------------------------------------------------------

def _minetti_cost(grade: float) -> float:
    """Energy cost of running (J/kg/m) at a decimal grade."""
    g = grade
    return 155.4 * g**5 - 30.4 * g**4 - 43.3 * g**3 + 46.3 * g**2 + 19.5 * g + 3.6


_FLAT_COST = _minetti_cost(0.0)


def gap_pace_s_km(
    pace_s_km: float | None,
    elev_gain_m: float | None,
    elev_loss_m: float | None,
    distance_km: float | None,
) -> float | None:
    """Grade-adjusted pace (equivalent flat pace, s/km).

    Climbs and descents are costed separately over their share of the
    lap: a lap that climbs 20 m then descends 20 m is NOT flat.
    """
    if pace_s_km is None or not distance_km:
        return None
    gain = float(elev_gain_m or 0)
    loss = float(elev_loss_m or 0)
    total_vertical = gain + loss
    if total_vertical <= 0:
        return round(float(pace_s_km), 1)
    dist_m = distance_km * 1000.0
    up_share = gain / total_vertical
    down_share = loss / total_vertical
    # Clamp to +/-45%: beyond that the degree-5 Minetti polynomial
    # diverges (steep trail laps) and the GAP becomes meaningless.
    up_grade = gain / (dist_m * up_share) if up_share > 0 else 0.0
    down_grade = -loss / (dist_m * down_share) if down_share > 0 else 0.0
    up_grade = max(-0.45, min(0.45, up_grade))
    down_grade = max(-0.45, min(0.45, down_grade))
    cost = up_share * _minetti_cost(up_grade) + down_share * _minetti_cost(down_grade)
    return round(float(pace_s_km) * cost / _FLAT_COST, 1)


# ---------------------------------------------------------------------------
# Lap enrichment
# ---------------------------------------------------------------------------

def _cadence_factor(laps: list[dict]) -> int:
    """2 when the export is per-leg cadence (~84), 1 when already spm."""
    vals = [float(l["avg_cadence"]) for l in laps if l.get("avg_cadence")]
    if not vals:
        return 1
    return 2 if statistics.median(vals) < 120 else 1


def enrich_run_laps(laps: list[dict]) -> list[dict]:
    """Copies of the run laps with gap_pace_s_km and cadence_spm added."""
    factor = _cadence_factor(laps)
    out: list[dict] = []
    for lap in laps:
        row = dict(lap)
        row["gap_pace_s_km"] = gap_pace_s_km(
            lap.get("avg_pace_s_km"),
            lap.get("elevation_gain_m"),
            lap.get("elevation_loss_m"),
            lap.get("distance_km"),
        )
        if lap.get("avg_cadence") is not None:
            row["cadence_spm"] = int(round(float(lap["avg_cadence"]) * factor))
        out.append(row)
    return out


def bike_lap_intensity(lap: dict) -> tuple[str, float | None]:
    """(metric, value): NP first, then avg power, else ('none', None).

    The repo's parse_laps produces 'normalized_power_w' (the v3 key);
    'np_w' is accepted for other lap sources."""
    if lap.get("normalized_power_w") is not None:
        return "np_w", float(lap["normalized_power_w"])
    if lap.get("np_w") is not None:
        return "np_w", float(lap["np_w"])
    if lap.get("avg_power_w") is not None:
        return "power_w", float(lap["avg_power_w"])
    return "none", None


def _is_artifact(lap: dict, sport_key: str) -> bool:
    """Micro-laps: a few seconds and a few metres (button/GPS glitches)."""
    time_s = lap.get("time_s") or 0
    if sport_key == "swimming":
        dist_m = lap.get("distance_m") or 0
        return time_s < 15 and dist_m < 25
    dist_km = lap.get("distance_km") or 0
    return time_s < 15 and dist_km < 0.05


def display_laps(sport: str, laps: list[dict]) -> list[dict]:
    """The lap rows handed to the model: enriched, annotated, complete."""
    sport_key = (sport or "").lower()
    if sport_key == "running":
        working = enrich_run_laps(laps)
    else:
        working = [dict(l) for l in laps]
    out: list[dict] = []
    for i, lap in enumerate(working, start=1):
        row: dict[str, Any] = {"n": i, "artifact": _is_artifact(lap, sport_key)}
        if sport_key == "swimming":
            row["distance_m"] = lap.get("distance_m")
            row["time_s"] = lap.get("time_s")
            row["rest"] = bool(lap.get("is_rest"))
        else:
            row["distance_km"] = lap.get("distance_km")
            row["time_s"] = lap.get("time_s")
            row["moving_time_s"] = lap.get("moving_time_s")
        if lap.get("avg_hr") is not None:
            row["avg_hr"] = lap.get("avg_hr")
        if sport_key == "running":
            row["pace_s_km"] = lap.get("avg_pace_s_km")
            row["gap_pace_s_km"] = lap.get("gap_pace_s_km")
            if lap.get("cadence_spm") is not None:
                row["cadence_spm"] = lap.get("cadence_spm")
            row["elev_gain_m"] = lap.get("elevation_gain_m")
            row["elev_loss_m"] = lap.get("elevation_loss_m")
        elif sport_key == "cycling":
            metric, value = bike_lap_intensity(lap)
            if value is not None:
                row["power_w"] = value
                row["power_metric"] = metric
            dist = float(lap.get("distance_km") or 0)
            time_s = float(lap.get("time_s") or 0)
            if dist > 0 and time_s > 0:
                row["speed_kmh"] = round(dist / (time_s / 3600.0), 1)
            row["elev_gain_m"] = lap.get("elevation_gain_m")
            row["elev_loss_m"] = lap.get("elevation_loss_m")
        out.append(row)
    return out


def _activity_header(sport: str, activity_row: Any, laps: list[dict]) -> dict:
    def get(*names):
        for name in names:
            if isinstance(activity_row, dict):
                if activity_row.get(name) is not None:
                    return activity_row[name]
            else:
                val = getattr(activity_row, name, None)
                if val is not None:
                    return val
        return None

    moving = get("movingDuration", "moving_duration_s", "moving_duration")
    if moving is None:
        moving = sum(
            float(l.get("moving_time_s") or l.get("time_s") or 0) for l in laps
        ) or None
    return {
        "name": get("activityName", "name"),
        "sport": sport,
        "distance_km": get("distance"),
        "duration_s": get("duration"),
        "moving_duration_s": moving,
        "elevation_gain_m": get("elevationGain", "elevation_gain"),
        "avg_hr": get("averageHR", "avg_hr"),
        "avg_power_w": get("averagePower", "avg_power_w"),
        "np_w": get("normPower", "np_w"),
        "trainer": get("trainer"),
    }


def build_facts_payload(
    sport: str, activity_row: Any, laps: list[dict]
) -> dict:
    """Everything the prompt needs: header + the full enriched laps."""
    rows = display_laps(sport, laps)
    return {
        "sport": (sport or "").lower(),
        "activity": _activity_header(sport, activity_row, laps),
        "laps": rows,
        "artifact_laps": sum(1 for r in rows if r["artifact"]),
    }
