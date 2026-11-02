"""AI workout summary — 100% AI reading (v5), generated once at sync.

Design (Lucas's call, 2026-10-29, after three review rounds): his
sessions are mostly watch autolaps (1 km) plus occasional manual
presses, so repetitions are smaller than a lap or straddle two laps.
There is no lap-level structure for Python to propose, hydrate or
validate — every gate built on lap ranges either rejected good
readings on arithmetic or let the original "11x1 km" hallucination
through on autolap data. So:

- Python is plumbing: per-lap numbers (GAP, cadence, power) computed
  in activity_facts, the activity header (the Garmin title often
  states the planned session), the athlete profile, the block
  context. No structure decisions.
- The model reads the FULL lap table with a prompt that teaches the
  autolap reality and returns {label, summary_md, flags, confidence}.
  The label follows a frozen format specified in the prompt.
- Storage stays the single workout_summaries table. A successful
  generation writes source='llm_splits' (distinct from the legacy
  'llm' one-liner rows and from the short-lived 'llm_validated').
  On failure NOTHING is written over the existing label: the caller
  falls back to the current heuristic path and only ai_status is
  recorded, which the retry pass (ai_retry.py) picks up later.

Designed to live in utils/pipeline/workout_summaries/.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, timedelta
from typing import Any

from utils.gemini_client import (
    generate_text,
    generate_text_with_fallbacks,
    get_api_key,
)

try:  # installed in the repo package
    from utils.pipeline.workout_summaries.activity_facts import build_facts_payload
    from utils.pipeline.workout_summaries.athlete_profile import profile_text
except ImportError:  # standalone kit layout (files side by side)
    from activity_facts import build_facts_payload
    from athlete_profile import profile_text

logger = logging.getLogger(__name__)

PROMPT_VERSION = 7
MAX_AI_ATTEMPTS = 3  # per activity; the retry pass stops after this
SOURCE = "llm_splits"
SUMMARY_LANG = os.environ.get("AI_SUMMARY_LANG", "fr")

SYSTEM_PROMPT = (
    "You are an expert endurance coach for a triathlete. You read one "
    "training session from its complete split data and say what the "
    "session actually was. You never invent numbers that are not in "
    "the data you are given."
)

SUMMARY_PROMPT = """### Athlete profile
__PROFILE__

### Recent training context
__CONTEXT__

### Activity
__HEADER__

### Lap table (computed by Python — trust these numbers)
__LAPS_TABLE__

### How the laps work — read this before anything else
- These laps are the WATCH's laps: mostly automatic laps (typically every 1 km on a run, 5 km on a ride) plus occasional manual button presses. They are NOT the workout's repetitions.
- Repetitions are often SMALLER than a lap (a 3-minute rep at 4:00/km covers ~0.75 km) or straddle two laps (a manual press mid-rep creates two adjacent laps at a similar speed). Never expect one lap = one rep, and never count laps to count reps.
- Read the RHYTHM instead: oscillation of pace/power and heart rate across consecutive laps, blocks of similar laps, ramps, collapses. A sawtooth heart rate over alternating faster/slower kilometres IS an interval session even when no single lap matches a rep.
- Laps marked ARTIFACT (a few seconds, a few metres) are button presses or GPS glitches: ignore them for structure; they still count in the totals.
- Lap times are TIMER times (the watch's chrono, pauses included). The header gives the session's timer and moving totals: where they diverge, the athlete stopped (traffic lights, breaks). Do not read a slow lap as low effort before checking it for a stop.
- Some laps show a second time, "mov m:ss": that lap's MOVING time. When it is much shorter than the lap's timer time, the athlete stopped inside that lap — judge the lap's effort from its moving time and intensity, not from the timer time.

### The activity name
- A structured-workout title (Garmin) often states the planned session: "6x3min", "3x6min", "2x20' threshold". Treat it as a hypothesis to CHECK against the laps, never as a fact.
- You may take the session's FORMAT from the title only when the laps are compatible with it (rhythm, intensities, total duration). In that case confidence is at most "medium": the format comes from the title, not from measurement.
- If the laps contradict the title, trust the laps.
- Generic titles — "Running", "Course à pied", a place name + a sport — carry no information: ignore them completely.

### Numbers you may use
- Numbers read in the header or the lap table, and SIMPLE aggregates over consecutive laps (a block's total distance, its mean pace/power/heart rate), written with "~" when they are aggregates rather than read values.
- Never a modelled or inferred number: no rep pace, rep distance or recovery duration that the laps cannot measure — in autolap they usually cannot (see worked example 3).

### What to read, per sport
- Run: grade-adjusted pace (GAP) first — raw pace lies on hills — with heart rate LEVEL and TREND. A stretch whose pace holds while heart rate collapses by 30+ bpm is controlled float / recovery running, NOT work, however fast it looks. A stretch at a similar GAP whose heart rate stays HIGH — near the session's other work blocks and well above its float stretches — is work. Judge heart rate RELATIVELY, inside this session and against the profile: there is no universal bpm threshold, and a heart rate glued to the cadence is a sensor artifact to flag (cadence_lock_suspected), not an effort to describe. Say when GAP and raw pace diverge (climbs, descents).
- Bike: power first (NP, else average power), then heart rate, then speed. Power steady within a few watts lap after lap means a trainer/ERG session or very controlled outdoor work. Judge blocks against the athlete's IM power reference. On a steady endurance ride there is no structure to find: say so.
- Swim: distances and repetition patterns — sets of 50/100/200 m, REST rows between sets are recoveries, not swimming.

### Output — ONE JSON object, no prose around it
{
  "label": "the one-line label, format below",
  "summary_md": "the written summary, format below",
  "flags": ["..."],
  "confidence": "high|medium|low"
}

### The label — ONE line, this frozen format (English abbreviations whatever the summary language)
- Segments joined by " + ". Run: "4.0km WU", steady blocks "8.0km @ 4:03/km" or with a rounded duration when the block is time-shaped "20' @ 3:42/km", intervals "6x3' @ 3:20/km R'2"" (reps x work duration @ pace, R' + recovery in minutes + "), a lone easy run "12.0km EF", "2.0km CD". When a run block's GAP differs from its raw pace by 8 s/km or more, write it as "@ 4:06/km (GAP 4:35/km)".
- Bike: segments in watts when power exists ("45' @ 217W"), else heart rate ("45' ~152 Avg HR"), else speed ("45' @ 36.1 km/h"). A steady endurance ride is ONE segment: "92.4km @ 185W".
- Swim: "0.4km WU + 8x100m + 0.2km CD" style, or "1.2km sets" when the set pattern is unclear.
- The label names the session's REAL pattern as read from the splits and the title (6x3', 2x45', 3x6', progressive...), rounded to what the data supports — never a tidier pattern than the one that happened.
- When the format comes from the TITLE and the laps cannot measure the reps (autolap), do NOT write a rep pace or a recovery: write the format, then the distance and mean pace of the laps that contain the series: "6x3' in 7.0km @ 4:21/km" (see worked example 3).
- Confidence "low" forbids any format in the label: the label is then the raw session only — run: total distance and mean pace, e.g. "12.4km @ 4:48/km"; bike: total distance and mean intensity, e.g. "92.4km @ 185W" (or mean heart rate / speed when power is absent); swim: total distance only, e.g. "1.9km" — and the flags include structure_unreadable.

### summary_md
3-5 sentences plus up to 3 short bullet points, in __LANG__. Name the session type and its real pattern, give the key numbers (read values and "~" aggregates only, per the numbers rule), place the session in its recent block when context is provided, and state any data-quality flag in plain words. If the splits genuinely do not reveal a structure (autolap mush, missing sensors), write what CAN be said — volume, intensity distribution, heart-rate behaviour — and set confidence to low or medium instead of forcing a pattern.

The worked examples below calibrate the READING. Their numbers belong to those sessions only — never reuse them in another session's output.

### flags — only when the data shows it, definitions are strict
- cadence_lock_suspected: on several consecutive run laps, heart rate sits within +/-5 bpm of the cadence AND clearly above the heart rate of other laps at the same GAP in the same session (the watch read the step rate instead of the heart).
- hr_implausible: heart rate impossible or stuck (0, above a plausible maximum, or frozen at one value across very different efforts).
- float_too_fast: a stretch that reads as float/recovery by position is run at work intensity — pace near the work blocks' pace WITHOUT the heart-rate collapse that defines a float.
- structure_unreadable: no session pattern can be supported by the laps (required when confidence is "low").
- missing_power / missing_hr: the sensor the sport is read with is absent.
- stop_detected: the header's timer and moving totals diverge materially, or a lap's mov time is much shorter than its timer time.

### Worked example 1 — long run, 30.02 km, 2:11:18, D+ 73 m (1 km laps)
Key laps: km 1-4 at 5:13, 5:03, 4:56, 4:50/km, HR 130-135 (progressive warm-up). Km 5 is a transition kilometre (4:07, HR rising through 148). Km 6-12 hold ~3:55-4:02/km except the km 11 climb; on km 6-10 the heart rate reads 165-172 — the same range as the cadence (~168-172 steps/min) — km 11 is a +21 m climb (GAP 4:19), km 12 back at 168. Km 13-20 at 4:23-4:42/km with HR COLLAPSED to 121-150 and falling — same speed family, completely different effort. Km 21-28 at 3:57-4:17/km, HR only 129-143 — the honest heart rate at this pace, and the contrast with km 6-10 is what exposes the first block's reading. Km 29-30 easy at 4:49-4:52.
Correct reading: 4 km progressive warm-up + ~8 km at ~4:00/km + 8 km of FLOAT at ~4:35/km (km 13 is already float: pace 4:23 but HR falls 170 -> 150 -> 127) + ~8 km at ~4:02/km + 2 km cool-down. An alternation long run — NOT "11x1.0 km intervals": the efforts are 8 km blocks, not 1 km reps. Flag: cadence_lock_suspected on the first work block (HR within a few bpm of cadence on km 6-10, and far above the 129-143 the same GAP produces on km 21-28).
Expected output: {"label": "4.0km WU + 8.0km @ 4:03/km + 8.0km @ 4:34/km + 8.0km @ 4:04/km + 2.0km CD", "flags": ["cadence_lock_suspected"], "confidence": "high", "summary_md": "Sortie longue à alternances : 4 km progressifs, puis deux blocs de ~8 km à ~4'00/km séparés par 8 km de float à ~4'35/km. Le float est bien contrôlé (FC effondrée de 170 à ~125) malgré une allure rapide. Donnée à surveiller : sur le premier bloc, la FC (165-172) colle à la cadence, probable cadence lock — le second bloc au même rythme lit 129-143."}

### Worked example 2 — bike, 73.28 km, 2:04:33, D+ 409 m, 35.3 km/h (manual laps + micro-lap artifacts)
Key laps: 10:01 at 178W (warm-up), then ~7 minutes of short openers (30 s-1:30 at 179-279W, heart rate still low — lag, not effort), then 29:55 + 15:07 at 217-218W, 4:30 + 2:56 at 191W around 2-7 s ARTIFACT laps, then 30:11 at 217W and 15:01 at 224W, 10:00 cool-down at 178W. Heart rate drifts +~10 bpm between the two long blocks at equal power.
Correct reading: warm-up with openers + 2x45' at Ironman power (~218W, metronomic — the two laps of each block are one continuous effort split by a manual press) + ~7'30 recovery at 191W + cool-down.
Expected output: {"label": "8.8km WU + 45' @ 217W + 7' @ 191W + 45' @ 219W + 6.1km CD", "flags": [], "confidence": "high", "summary_md": "Séance spécifique Ironman : 2x45' à ~218W, puissance métronomique (217/218 puis 217/224), séparés par ~7'30 à 191W, après un échauffement avec des relances courtes. La dérive cardiaque entre les deux blocs (+~10 bpm à puissance égale) est le point de vigilance sur la durée."}

### Worked example 3 — intervals on 100% autolap (the common case here)
Activity named "6x3min", run, 11.0 km total, 1 km autolaps only. After 2 km of warm-up, the next 7.0 km alternate ~4:05-4:15 and ~4:30-4:45/km (mean 4:21/km) with heart rate sawing between ~150 and ~172, then 2 km easy. No lap is a rep — each 3' rep (~0.75 km) is split across two kilometres, so the rep pace and the recoveries are NOT measurable from these laps, and writing them would be inventing numbers. Correct reading: the title's format is compatible — the sawtooth fits, and the 7.0 km stretch (~30 min at ~4:21/km) is long enough to hold 6x3' plus recoveries — so the label takes the format from the title and the measurable aggregate for the series — its distance and mean pace. Confidence medium, per the title rule.
Expected output: {"label": "2.0km WU + 6x3' in 7.0km @ 4:21/km + 2.0km CD", "flags": [], "confidence": "medium", "summary_md": "Séance 6x3' en autolap intégral : les répétitions ne coïncident pas avec les tours kilométriques, leur allure n'est pas mesurable ici. La scie cardiaque (150-172) et l'alternance des allures sur les 7,0 km centraux (~4:21/km en moyenne) sont compatibles avec le format du titre, sans permettre de le vérifier rep par rep."}
"""

# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _fmt_time_s(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    s = int(round(float(seconds)))
    if s >= 3600:
        return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    return f"{s // 60}:{s % 60:02d}"


def _fmt_pace_s_km(pace: float | None) -> str:
    if pace is None:
        return "—"
    s = int(round(float(pace)))
    return f"{s // 60}:{s % 60:02d}/km"


def _mov_part(lap: dict) -> str | None:
    """'mov m:ss' when the lap's moving time is materially shorter
    than its timer time — the only way a stop is observable per lap."""
    t = lap.get("time_s")
    m = lap.get("moving_time_s")
    if t and m and float(t) - float(m) >= 10:
        return f"mov {_fmt_time_s(m)}"
    return None


def format_laps_table(payload: dict) -> str:
    sport = payload.get("sport")
    lines: list[str] = []
    for lap in payload.get("laps") or []:
        n = lap["n"]
        tag = " ARTIFACT" if lap.get("artifact") else ""
        mov = _mov_part(lap)
        if sport == "swimming":
            if lap.get("rest"):
                lines.append(f"{n} | REST | {_fmt_time_s(lap.get('time_s'))}{tag}")
            else:
                line = (
                    f"{n} | {lap.get('distance_m')} m | {_fmt_time_s(lap.get('time_s'))}"
                    f" | HR {lap.get('avg_hr') or '—'}{tag}"
                )
                if mov:
                    line += f" | {mov}"
                lines.append(line)
        elif sport == "cycling":
            parts = [
                str(n),
                f"{lap.get('distance_km')} km",
                _fmt_time_s(lap.get("time_s")),
            ]
            if mov:
                parts.append(mov)
            if lap.get("power_w") is not None:
                parts.append(f"{int(round(lap['power_w']))}W")
            parts.append(f"HR {lap.get('avg_hr') or '—'}")
            if lap.get("speed_kmh") is not None:
                parts.append(f"{lap['speed_kmh']} km/h")
            if lap.get("elev_gain_m") or lap.get("elev_loss_m"):
                parts.append(f"+{lap.get('elev_gain_m') or 0}/-{lap.get('elev_loss_m') or 0} m")
            lines.append(" | ".join(parts) + tag)
        else:  # running
            parts = [
                str(n),
                f"{lap.get('distance_km')} km",
                _fmt_time_s(lap.get("time_s")),
            ]
            if mov:
                parts.append(mov)
            parts += [
                f"pace {_fmt_pace_s_km(lap.get('pace_s_km'))}",
                f"GAP {_fmt_pace_s_km(lap.get('gap_pace_s_km'))}",
                f"HR {lap.get('avg_hr') or '—'}",
            ]
            if lap.get("cadence_spm") is not None:
                parts.append(f"cad {lap['cadence_spm']}")
            if lap.get("elev_gain_m") or lap.get("elev_loss_m"):
                parts.append(f"+{lap.get('elev_gain_m') or 0}/-{lap.get('elev_loss_m') or 0} m")
            lines.append(" | ".join(parts) + tag)
    return "\n".join(lines)


def format_header(payload: dict) -> str:
    a = payload.get("activity") or {}
    lines = [
        f"Name: {a.get('name') or '(unnamed)'}",
        f"Sport: {a.get('sport')}",
        f"Distance: {a.get('distance_km')} km",
        f"Timer: {_fmt_time_s(a.get('duration_s'))} | Moving: {_fmt_time_s(a.get('moving_duration_s'))}",
    ]
    if a.get("elevation_gain_m") is not None:
        lines.append(f"Elevation gain: {a['elevation_gain_m']} m")
    if a.get("avg_hr") is not None:
        lines.append(f"Avg HR: {a['avg_hr']}")
    if a.get("np_w") is not None:
        lines.append(f"NP: {a['np_w']} W")
    elif a.get("avg_power_w") is not None:
        lines.append(f"Avg power: {a['avg_power_w']} W")
    if a.get("trainer"):
        lines.append("Trainer ride (indoor).")
    if payload.get("artifact_laps"):
        lines.append(f"Artifact laps in the table: {payload['artifact_laps']}")
    return "\n".join(lines)


def build_summary_prompt(payload: dict, block_context: dict | None = None) -> str:
    context_text = (
        json.dumps(block_context, ensure_ascii=False, indent=1)
        if block_context
        else "(not provided)"
    )
    return (
        SUMMARY_PROMPT.replace("__PROFILE__", profile_text())
        .replace("__CONTEXT__", context_text)
        .replace("__HEADER__", format_header(payload))
        .replace("__LAPS_TABLE__", format_laps_table(payload))
        .replace("__LANG__", SUMMARY_LANG)
    )


def build_block_context(
    activity_date: date,
    sport: str,
    recent_activities: list[dict],
    race_periods: list[dict] | None = None,
) -> dict:
    """Volumes 7/28 days + target race, from already-fetched rows.

    recent_activities rows: {date, sport, distance_km, duration_s}
    (same sport as the activity, BEFORE its date). race_periods rows:
    {start, end, race} like constants.WORKOUT_SUMMARY_RACE_PERIODS.
    Pure function — the caller does the fetching.
    """
    sport_key = (sport or "").lower()
    vol7 = vol28 = 0.0
    n7 = n28 = 0
    for row in recent_activities or []:
        if (row.get("sport") or "").lower() != sport_key:
            continue
        row_date = row.get("date")
        if row_date is None or row_date >= activity_date:
            continue
        dist = float(row.get("distance_km") or 0)
        if activity_date - row_date <= timedelta(days=7):
            vol7 += dist
            n7 += 1
        if activity_date - row_date <= timedelta(days=28):
            vol28 += dist
            n28 += 1
    context: dict[str, Any] = {
        "sport": sport_key,
        "volume_7d_km": round(vol7, 1),
        "sessions_7d": n7,
        "volume_28d_km": round(vol28, 1),
        "sessions_28d": n28,
    }
    for period in race_periods or []:
        try:
            start = date.fromisoformat(str(period["start"]))
            end = date.fromisoformat(str(period["end"]))
        except (KeyError, ValueError):
            continue
        if start <= activity_date <= end:
            context["target_race"] = period.get("race")
            context["weeks_to_race"] = round((end - activity_date).days / 7, 1)
            break
    return context


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def parse_ai_response(text: str) -> dict | None:
    """Extract the JSON object; light sanity (shape, not structure)."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    label = str(data.get("label") or "").strip()
    summary_md = str(data.get("summary_md") or "").strip()
    if not label or not summary_md or len(label) > 250:
        return None
    return {
        "label": label,
        "summary_md": summary_md,
        "flags": [str(f) for f in (data.get("flags") or [])],
        "confidence": str(data.get("confidence") or "medium"),
    }


def _generate(prompt: str) -> tuple[str, str]:
    """Gemini call honoring GEMINI_SUMMARY_MODEL; JSON mode when the
    client supports it (gemini_client_json_mode.patch), generous
    output budget (reasoning can count against max_output_tokens)."""
    preferred = os.environ.get("GEMINI_SUMMARY_MODEL") or None
    if preferred:
        for kwargs in ({"response_mime_type": "application/json"}, {}):
            try:
                text = generate_text(
                    prompt,
                    system_instruction=SYSTEM_PROMPT,
                    model=preferred,
                    max_output_tokens=4096,
                    temperature=0.3,
                    **kwargs,
                )
                return text, preferred
            except TypeError:
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "GEMINI_SUMMARY_MODEL %s failed (%s); using fallbacks chain",
                    preferred,
                    exc,
                )
                break
    for kwargs in ({"response_mime_type": "application/json"}, {}):
        try:
            return generate_text_with_fallbacks(
                prompt,
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4096,
                temperature=0.3,
                **kwargs,
            )
        except TypeError:
            continue
    raise RuntimeError("Gemini call failed (no compatible signature)")


def generate_ai_summary(
    sport: str,
    activity_row: Any,
    laps: list[dict],
    block_context: dict | None = None,
) -> dict:
    """One AI reading of the session, or a failure status.

    Success: {label, summary_md, flags, confidence, source:
    'llm_splits', ai_status: 'ok', model}. Failure: {label: None,
    summary_md: None, ai_status: no_laps|no_key|api_error|parse_error}
    — the caller then keeps the existing heuristic label and records
    only ai_status (see ai_fields + ai_retry.py).
    """
    payload = build_facts_payload(sport, activity_row, laps)
    sport_key = (sport or "").lower()

    def failure(status: str) -> dict:
        return {
            "label": None,
            "summary_md": None,
            "flags": [],
            "confidence": None,
            "source": None,
            "ai_status": status,
            "sport": sport_key,
            "model": None,
            "facts": payload,
        }

    if not laps:
        return failure("no_laps")
    if not get_api_key():
        return failure("no_key")
    prompt = build_summary_prompt(payload, block_context)
    try:
        text, model = _generate(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI summary generation failed: %s", exc)
        return failure("api_error")
    parsed = parse_ai_response(text)
    if parsed is None:
        logger.warning("AI summary reply did not parse as JSON")
        return failure("parse_error")
    parsed["source"] = SOURCE
    parsed["ai_status"] = "ok"
    parsed["sport"] = sport_key
    parsed["model"] = model
    parsed["facts"] = payload
    return parsed


def ai_fields(result: dict) -> dict:
    """Columns to merge into the workout_summaries row.

    On success the label replaces structure_summary (source
    'llm_splits'). On failure the structure keys are ABSENT on
    purpose: base_row.update(fields) then writes nothing over the
    label, and the caller keeps the heuristic label.

    EVERY row carries the full ai_* key set (empty strings on
    failure, never None): the first upload then creates summary_md,
    ai_flags, ai_confidence, ai_model, ai_status and ai_attempts even
    if every generation in the batch failed — the race_coach SQL
    patch can rely on the columns existing after ANY first upload,
    not only after a lucky successful one.

    ai_attempts here is just the first-failure marker (1). The count
    lives in the stored row: the retry pass (ai_retry.py) increments
    it by UPDATE for rows that fail again, and the candidate query
    caps at MAX_AI_ATTEMPTS.
    """
    if result.get("ai_status") == "ok":
        return {
            "summary_md": result.get("summary_md"),
            "structure_summary": result.get("label"),
            "structure_summary_source": SOURCE,
            "ai_flags": json.dumps(result.get("flags") or []),
            "ai_confidence": result.get("confidence") or "",
            "ai_model": result.get("model") or "",
            "ai_status": "ok",
            "ai_prompt_version": PROMPT_VERSION,
            "ai_attempts": 0,
        }
    return {
        "summary_md": "",
        "ai_flags": "[]",
        "ai_confidence": "",
        "ai_model": "",
        "ai_status": result.get("ai_status"),
        "ai_prompt_version": PROMPT_VERSION,
        "ai_attempts": 1,
    }


RETRYABLE_STATUSES = {"no_key", "api_error", "parse_error"}


def ai_needs_retry(status: str | None, stored_prompt_version: int | None = None) -> bool:
    """Transient failures are always retryable. (No validator anymore,
    so no prompt-version condition: a parse_error at the same prompt
    version can succeed on a later attempt.)"""
    return status in RETRYABLE_STATUSES
