"""Single source of truth for the athlete profile used by AI prompts.

Phase 1 injects this into the summary prompt; phase 2 (chat tab) will
read the same profile. Override with ATHLETE_PROFILE_JSON (a JSON
object merged over the defaults) or ATHLETE_PROFILE_FILE (path to a
JSON file). Defaults are Lucas's known references (2026-10-29) — the
values that used to be hardcoded separately in several prompts.
"""

from __future__ import annotations

import json
import os

DEFAULT_PROFILE: dict = {
    "identity": "Triathlete (IRONMAN / 70.3), marathon PB 2:45 (CIM 2025)",
    "run_paces": {
        "10k": "3:25/km",
        "half_marathon": "3:35/km",
        "marathon": "3:55-4:00/km",
        "threshold_tempo": "3:40-4:20/km",
        "easy_ef": "4:45-5:20/km",
    },
    "bike": {
        "im_power_w": 218,
        "weight_kg": 77,
    },
    "notes": (
        "Reference paces are flat, sea-level equivalents — always "
        "compare GAP pace, not raw pace, on hilly sessions."
    ),
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursive merge: overriding run_paces.marathon must not wipe
    the other paces."""
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_profile() -> dict:
    profile = dict(DEFAULT_PROFILE)
    raw = os.environ.get("ATHLETE_PROFILE_JSON")
    if raw:
        try:
            profile = _deep_merge(profile, json.loads(raw))
        except json.JSONDecodeError:
            pass
    path = os.environ.get("ATHLETE_PROFILE_FILE")
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                profile = _deep_merge(profile, json.load(fh))
        except (OSError, json.JSONDecodeError):
            pass
    return profile


def profile_text(profile: dict | None = None) -> str:
    p = profile or load_profile()
    lines = [f"Athlete: {p.get('identity')}"]
    paces = p.get("run_paces") or {}
    if paces:
        lines.append(
            "Run reference paces: "
            + ", ".join(f"{k} {v}" for k, v in paces.items())
        )
    bike = p.get("bike") or {}
    if bike.get("im_power_w"):
        # Only what the summaries use. weight_kg stays in the profile
        # for phase 2 (W/kg, nutrition) but is not sent here.
        lines.append(f"Bike: IM target power ~{bike['im_power_w']} W")
    if p.get("notes"):
        lines.append(str(p["notes"]))
    return "\n".join(lines)
