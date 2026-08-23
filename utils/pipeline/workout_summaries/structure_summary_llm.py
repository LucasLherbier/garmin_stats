"""LLM-generated workout structure from raw lap splits (no heuristic bias)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from utils.gemini_client import generate_text_with_fallbacks, get_api_key
from utils.pipeline.workout_summaries.parse_laps import activity_scalar, format_duration
from utils.pipeline.workout_summaries.split_merge import blocks_for_llm, merge_splits_to_blocks
from utils.pipeline.workout_summaries.structure_summary import build_main_structure_summary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_CYCLING = """You format a pre-merged workout block list into ONE metrics-only classification line.

Splits are already merged and repeated work patterns collapsed (e.g. kind=intervals with reps=2 means 2x5', not 5'+5').

### BLOCK KINDS:
- `wu`: warm-up → `Xkm WU`
- `work`: sustained block → prefer `rounded_time` + `@ pace` (e.g. `20' @ 3:42/km`), else `Xkm @ pace`
- `intervals`: already detected repeats → `Nx[work_rounded or distance] @ pace [rest_label]`
  Example: reps=2, work_rounded=5', rest_label=R'2" → `2x5' @ 3:23/km R'2"`
- `rest`: standalone recovery between main blocks — usually omit unless needed
- `cd`: cool-down → `Xkm CD`
- `easy`: unstructured easy riding — use distance or duration

### RULES:
- Use `+` between phases. Keep WU and CD when present.
- Use block fields as-is: rounded_time, work_rounded, rest_label, avg_pace, distance_km.
- NEVER invent reps or rest — trust kind=intervals.
- NEVER use vague words ("Tempo Block", "Fast", "Repetitions", "with Recovery").
- ASCII `x` for reps. One line only.

Format:
**Workout Classification**: [metrics-only structure]

Example: `6.6km WU + 20' @ 3:42/km + 2x5' @ 3:23/km R'2" + 2.8km CD`
"""

SYSTEM_PROMPT_RUNNING = """You format a pre-merged RUN workout block list into ONE metrics-only classification line.

Blocks are merged in Python; repeats are collapsed (kind=intervals with reps=3 → `3x…`, not listed three times).

### ATHLETE PACE CONTEXT (approximate, for labeling only):
- 10K pace ~3:25/km | Half ~3:35/km | Marathon ~3:55–4:00/km
- Threshold / tempo ~3:40–4:20/km
- Endurance fundamental (EF) / easy ~4:45–5:20/km

### BLOCK KINDS:
- `wu`: warm-up — ONLY easy/EF pace (≥4:45/km), before harder work. Never label threshold/tempo pace as WU.
- `work`: sustained block at threshold or faster → prefer TIME or DISTANCE + `@ pace`
- `intervals`: repeats → `Nx[distance_label OR work_rounded] @ pace [rest_label]`
- `cd`: cool-down — easy pace after work
- `easy`: whole run at EF pace with no harder main set → `Xkm EF` or `X' EF` (NOT `Xkm WU`)

### DISTANCE vs TIME (pick the most natural):
- Prefer `distance_label` when present (800m, 1km, 1600m, …).
- Prefer `work_rounded` / `rounded_time` for time-based reps (3', 5', 6', …).
- Cross-check `duration_s`, `distance_km`, and pace — e.g. ~3' @ 3:24/km ≈ 800m; ~6' @ 3:37/km ≈ 1600m.
- For intervals, use the distance if it matches a standard rep (800m, 1km, 1.6km); otherwise use rounded time.

### RULES:
- Use `+` between phases. Include WU/CD only when blocks exist and pace fits.
- NEVER label an entire steady run at threshold pace as WU.
- NEVER use vague words ("Tempo Block", "Fast Reps", "with Recovery").
- NEVER invent reps or rest — trust kind=intervals.
- ASCII `x` for reps. One line only.

Format:
**Workout Classification**: [metrics-only structure]

Examples:
- `5.45km WU + 3' @ 3:24/km + 6' @ 3:37/km + 3x2.44km @ 3:36/km R'2" + 2.49km CD`
- `10.0km EF` (steady easy run, no harder main set)
- `3.3km WU + 2x15' @ 3:45/km R'5" + 3.8km CD`
"""


def system_prompt_for_sport(sport: str) -> str:
    if (sport or "").lower() == "running":
        return SYSTEM_PROMPT_RUNNING
    return SYSTEM_PROMPT_CYCLING


def _compact_dict(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def build_structure_prompt(activity_row: Any, laps: list[dict], *, sport: str | None = None) -> str:
    """User message: merged blocks JSON (split merge + repeat detection done in Python)."""
    name = activity_row.get("activityName") if hasattr(activity_row, "get") else None
    duration = activity_scalar(activity_row, "duration")
    distance = activity_scalar(activity_row, "distance")
    hr = activity_scalar(activity_row, "averageHR")
    elev = activity_scalar(activity_row, "elevationGain")

    context: dict[str, Any] = {}
    if sport:
        context["sport"] = sport.lower()
    if name:
        context["activity_name"] = str(name).strip()
    if duration:
        context["total_duration"] = format_duration(duration)
        context["total_duration_s"] = int(round(float(duration)))
    if distance:
        context["total_distance_km"] = round(float(distance), 2)
    if hr:
        context["activity_avg_hr"] = int(round(float(hr)))
    if elev:
        context["total_elevation_gain_m"] = int(round(float(elev)))

    merged = merge_splits_to_blocks(laps, activity_row, sport=sport)
    payload = {
        "activity": _compact_dict(context),
        "blocks": blocks_for_llm(merged),
    }
    return (
        "Merged workout blocks (splits already combined; repeats collapsed):\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )


def merge_blocks_for_activity(activity_row: Any, laps: list[dict], *, sport: str | None = None) -> list[dict[str, Any]]:
    """Public helper for tests — returns merged/collapsed blocks."""
    return merge_splits_to_blocks(laps, activity_row, sport=sport)


def extract_workout_classification(text: str) -> str:
    match = re.search(
        r"\*\*Workout Classification\*\*:\s*(.+?)(?:\n|\*\*|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        line = match.group(1).strip()
    else:
        line = text.strip().splitlines()[0].strip()
        line = re.sub(r'^["\']+|["\']+$', "", line)
    if len(line) > 200:
        line = line[:197] + "..."
    return line


def build_structure_summary_llm(
    sport: str,
    activity_row: Any,
    lap_analysis: list[dict],
    segments: list[dict] | None = None,
    *,
    laps: list[dict] | None = None,
    phases: list[str] | None = None,
    fallback: bool = True,
) -> tuple[str | None, str]:
    """Return (structure_summary, source) where source is 'llm' or 'heuristic'."""
    heuristic = build_main_structure_summary(
        segments or [], sport, activity_row, laps, phases
    )

    split_rows = laps or []
    if not get_api_key() or not split_rows:
        reason = "no API key" if not get_api_key() else "no laps"
        logger.debug("structure_summary heuristic (%s)", reason)
        return heuristic, "heuristic"

    prompt = build_structure_prompt(activity_row, split_rows, sport=sport)
    try:
        text, _model = generate_text_with_fallbacks(
            prompt,
            system_instruction=system_prompt_for_sport(sport),
            max_output_tokens=256,
            temperature=0.2,
        )
        return extract_workout_classification(text), "llm"
    except Exception as exc:
        logger.warning("LLM structure summary failed, using heuristic: %s", exc)
        if fallback:
            return heuristic, "heuristic"
        raise
