"""Build coach prompts and call the LLM for race-tab workout feedback."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import pandas as pd

from actions import utils as ut
from utils.pipeline.workout_summaries.lap_analysis import format_lap_table
from utils.pipeline.workout_summaries.segments import format_segments_for_log

# Single coach model for this app (override with GEMINI_MODEL in .env if needed).
COACH_GEMINI_MODEL = "gemini-3.1-flash-lite"


def coach_model() -> str:
    return (os.getenv("GEMINI_MODEL") or COACH_GEMINI_MODEL).strip() or COACH_GEMINI_MODEL


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _prep_full_detail_days() -> int:
    return int(os.getenv("GEMINI_PREP_FULL_DAYS", "35"))


def _max_prompt_chars() -> int:
    return int(os.getenv("GEMINI_MAX_PROMPT_CHARS", "28000"))


def _max_segment_chars() -> int:
    return int(os.getenv("GEMINI_MAX_SEGMENT_CHARS", "1200"))


def _models_for_api() -> list[str]:
    """One model by default; optional comma-separated GEMINI_MODEL_FALLBACKS."""
    primary = coach_model()
    raw = os.getenv("GEMINI_MODEL_FALLBACKS", "").strip()
    if not raw:
        return [primary]
    models = [m.strip() for m in raw.split(",") if m.strip()]
    ordered: list[str] = []
    seen: set[str] = set()
    for name in [primary, *models]:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "quota exceeded" in text


def _retry_delay_seconds(exc: BaseException) -> float:
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 1.0, 120.0)
    return 55.0


def _friendly_gemini_error(exc: BaseException) -> str:
    if _is_quota_error(exc):
        text = str(exc)
        lower = text.lower()
        models = ", ".join(_models_for_api())
        if "prepayment credits" in lower or "prepay" in lower:
            return (
                "Gemini API billing (429): prepaid credits for this project are depleted.\n"
                "• Add credits or fix billing: https://ai.studio/projects (project tied to your API key)\n"
                "• Docs: https://ai.google.dev/gemini-api/docs/billing#prepay\n"
                f"• Coach model: `{coach_model()}`\n"
                f"• Models tried: {models}"
            )
        return (
            "Gemini API quota exceeded (429).\n"
            "• Enable **Compact prep history** in the Race tab (smaller prompt).\n"
            "• Check rate limits and billing: https://ai.dev/rate-limit\n"
            f"• Coach model: `{coach_model()}` (set `GEMINI_MODEL` in `.env` to change).\n"
            f"• Models tried: {models}\n"
            f"• API detail: {text[:500]}"
        )
    return str(exc)

SYSTEM_PROMPT = """You are a personal triathlon coach reviewing Garmin workout summaries for race preparation (swim, bike, run).

Use the prep catalog for longitudinal context (the whole block). Focus your narrative on the recent week, but reference earlier patterns only when relevant (consistency, gaps, repeated session types).

Tone: direct, constructive, specific. No generic motivation fluff. Prefer short paragraphs and bullets.

When describing sessions, mirror compact structure lines like:
- Long Ride - sustained mixed efforts ~148 Avg HR - with additional intense hills
- 3×20min ~150 Avg HR

You receive heuristic structure_summary and segment blocks—not perfect labels. If outdoor rides look like "mixed efforts," interpret generously (terrain, unstructured endurance).

Cover: swim/bike/run balance vs recent load, key quality sessions, recovery/rest patterns, one or two actionable suggestions for next week. Do not invent workouts not supported by the data."""


def get_gemini_api_key() -> str | None:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key or None


def _parse_json_field(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _prep_row_line(row) -> str:
    day = pd.to_datetime(row["startTimeLocal"]).strftime("%Y-%m-%d")
    sport = row.get("sport") or "?"
    dist = row.get("distance")
    dist_s = f"{float(dist):.1f}km" if dist is not None and not pd.isna(dist) else "—"
    hr = row.get("averageHR")
    hr_s = f"{int(hr)} HR" if hr is not None and not pd.isna(hr) else ""
    structure = (row.get("structure_summary") or "").strip()
    if len(structure) > 120:
        structure = structure[:117] + "..."
    tail = structure or "(no structure line)"
    return f"{day} | {sport} | {dist_s} {hr_s} | {tail}"


def format_prep_index_lines(
    prep_df: pd.DataFrame,
    *,
    compact_prep: bool = True,
    reference_end: str,
    exclude_activity_ids: set[int] | None = None,
    full_detail_days: int | None = None,
) -> str:
    if prep_df.empty:
        return "(no workout summaries in this prep window)"
    full_days = full_detail_days if full_detail_days is not None else _prep_full_detail_days()
    ref = pd.to_datetime(reference_end)
    cutoff = ref - pd.Timedelta(days=full_days)

    ok = prep_df[prep_df["parse_status"] == "ok"].copy()
    ok["startTimeLocal"] = pd.to_datetime(ok["startTimeLocal"])
    ok = ok.sort_values("startTimeLocal")
    if exclude_activity_ids:
        ok = ok[~ok["activityId"].astype(int).isin(exclude_activity_ids)]

    recent_part = ok[ok["startTimeLocal"] >= cutoff]
    older_part = ok[ok["startTimeLocal"] < cutoff]

    lines: list[str] = []
    if compact_prep and not older_part.empty:
        lines.append(
            f"(Index: daily lines for {len(recent_part)} sessions in last {full_days}d; "
            f"{len(older_part)} older sessions as weekly rollup.)"
        )
        for _, row in recent_part.iterrows():
            lines.append(_prep_row_line(row))
        lines.append("")
        lines.append("Weekly rollup (older prep):")
        older_part = older_part.copy()
        older_part["week"] = older_part["startTimeLocal"].dt.to_period("W-SUN").astype(str)
        for week, grp in older_part.groupby("week", sort=True):
            counts = ", ".join(f"{k}×{int(v)}" for k, v in grp["sport"].value_counts().items())
            km = float(grp["distance"].fillna(0).sum())
            highlights = "; ".join(
                str(s)[:90]
                for s in grp["structure_summary"].dropna().head(2)
            )
            lines.append(f"{week}: {counts}, {km:.0f} km | {highlights or '—'}")
    else:
        for _, row in ok.iterrows():
            lines.append(_prep_row_line(row))

    skipped = prep_df[prep_df["parse_status"] != "ok"]
    if not skipped.empty:
        lines.append("")
        lines.append(
            f"({len(skipped)} activities without parsed laps: "
            f"{skipped['parse_status'].value_counts().to_dict()})"
        )
    return "\n".join(lines)


def format_recent_week_block(recent_df: pd.DataFrame, *, include_segments: bool = True) -> str:
    if recent_df.empty:
        return "(no parsed workouts in the lookback window)"
    max_seg = _max_segment_chars()
    blocks = []
    for _, row in recent_df.iterrows():
        day = pd.to_datetime(row["startTimeLocal"]).strftime("%Y-%m-%d")
        sport = row.get("sport") or "?"
        name = row.get("activityName") or ""
        dur = ut.format_duration(row.get("duration"))
        structure = (row.get("structure_summary") or row.get("summary_text") or "").strip()
        if len(structure) > 200:
            structure = structure[:197] + "..."
        blocks.append(f"### {day} | {sport} | {name} | {dur}\n{structure}")
        if include_segments:
            segments = _parse_json_field(row.get("segments"))
            if segments:
                seg_text = format_segments_for_log(segments)
                if len(seg_text) > max_seg:
                    seg_text = seg_text[: max_seg - 3] + "..."
                blocks.append(seg_text)
        blocks.append("")
    return "\n".join(blocks).strip()


def format_volume_context(race_metrics: pd.DataFrame) -> str:
    if race_metrics.empty:
        return ""
    r = race_metrics.iloc[0]
    return (
        f"Avg weekly duration: {ut.format_duration(r.get('average_duration_per_week'))}; "
        f"weekly avg km — swim {r.get('average_week_distance_swim') or 0:.1f}, "
        f"bike {r.get('average_week_distance_bike') or 0:.1f}, "
        f"run {r.get('average_week_distance_run') or 0:.1f}; "
        f"prep totals km — swim {r.get('total_distance_swim') or 0:.0f}, "
        f"bike {r.get('total_distance_bike') or 0:.0f}, "
        f"run {r.get('total_distance_run') or 0:.0f}."
    )


def build_coach_user_prompt(
    race_label: str,
    prep_start: str,
    prep_end: str,
    prep_index_text: str,
    recent_week_text: str,
    volume_text: str,
    lookback_days: int,
    prep_line_count: int,
) -> str:
    return f"""Target race: {race_label}
Prep window: {prep_start} to {prep_end} (exclusive end date, aligned with dashboard).

Volume snapshot (all activities in window, not only summarized workouts):
{volume_text or '(unavailable)'}

--- Full prep workout index ({prep_line_count} sessions with structure) ---
{prep_index_text}

--- Recent {lookback_days} days (structure + segment blocks) ---
{recent_week_text}

Write weekly coach feedback for this athlete."""


def _build_user_prompt(
    race_label: str,
    prep_start: str,
    prep_end: str,
    prep_df: pd.DataFrame,
    recent_df: pd.DataFrame,
    race_metrics: pd.DataFrame,
    lookback_days: int,
    compact_prep: bool,
    include_segments: bool,
    full_detail_days: int | None,
) -> str:
    exclude_ids = set()
    if not recent_df.empty and "activityId" in recent_df.columns:
        exclude_ids = {int(x) for x in recent_df["activityId"].tolist()}
    prep_line_count = int((prep_df["parse_status"] == "ok").sum()) if not prep_df.empty else 0
    prep_index_text = format_prep_index_lines(
        prep_df,
        compact_prep=compact_prep,
        reference_end=prep_end,
        exclude_activity_ids=exclude_ids,
        full_detail_days=full_detail_days,
    )
    return build_coach_user_prompt(
        race_label=race_label,
        prep_start=prep_start,
        prep_end=prep_end,
        prep_index_text=prep_index_text,
        recent_week_text=format_recent_week_block(
            recent_df, include_segments=include_segments
        ),
        volume_text=format_volume_context(race_metrics),
        lookback_days=lookback_days,
        prep_line_count=prep_line_count,
    )


def _call_gemini(client, user_prompt: str) -> str:
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=1536,
    )
    last_error: BaseException | None = None
    for model in _models_for_api():
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config,
                )
                text = response.text
                if not text:
                    raise RuntimeError("Gemini returned an empty response.")
                return text.strip()
            except Exception as exc:
                last_error = exc
                if _is_quota_error(exc) and attempt == 0:
                    time.sleep(_retry_delay_seconds(exc))
                    continue
                if _is_quota_error(exc):
                    break
                raise RuntimeError(_friendly_gemini_error(exc)) from exc
    raise RuntimeError(_friendly_gemini_error(last_error or RuntimeError("Gemini request failed")))


def generate_coach_narrative(
    race_label: str,
    prep_start: str,
    prep_end: str,
    prep_df: pd.DataFrame,
    recent_df: pd.DataFrame,
    race_metrics: pd.DataFrame,
    lookback_days: int = 7,
    compact_prep: bool | None = None,
    include_segments: bool = True,
) -> str:
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY in .env (local) or Streamlit secrets (Render)."
        )

    if compact_prep is None:
        compact_prep = _env_bool("GEMINI_COMPACT_PREP", True)

    try:
        from google import genai
    except ImportError as e:
        raise RuntimeError("Install google-genai: pip install google-genai") from e

    client = genai.Client(api_key=api_key)

    prompt_plans = [
        {"compact_prep": compact_prep, "include_segments": include_segments, "full_detail_days": None},
        {"compact_prep": True, "include_segments": False, "full_detail_days": 28},
        {"compact_prep": True, "include_segments": False, "full_detail_days": 14},
    ]

    seen_signatures: set[tuple] = set()
    last_error: BaseException | None = None
    for plan in prompt_plans:
        signature = (plan["compact_prep"], plan["include_segments"], plan["full_detail_days"])
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        user_prompt = _build_user_prompt(
            race_label=race_label,
            prep_start=prep_start,
            prep_end=prep_end,
            prep_df=prep_df,
            recent_df=recent_df,
            race_metrics=race_metrics,
            lookback_days=lookback_days,
            compact_prep=plan["compact_prep"],
            include_segments=plan["include_segments"],
            full_detail_days=plan["full_detail_days"],
        )
        if len(user_prompt) > _max_prompt_chars() and plan != prompt_plans[-1]:
            continue

        try:
            return _call_gemini(client, user_prompt)
        except RuntimeError as exc:
            last_error = exc
            if not _is_quota_error(exc.__cause__ or exc):
                raise
            continue

    raise RuntimeError(_friendly_gemini_error(last_error or RuntimeError("Gemini request failed")))


def lap_table_from_row(row: pd.Series) -> str:
    analysis = _parse_json_field(row.get("lap_analysis"))
    if not analysis:
        return "(no lap analysis)"
    return format_lap_table(analysis)


def segments_text_from_row(row: pd.Series) -> str | None:
    segments = _parse_json_field(row.get("segments"))
    if not segments:
        return None
    return format_segments_for_log(segments)
