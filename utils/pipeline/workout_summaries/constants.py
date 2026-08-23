"""Scope and constants for workout summary parsing."""

PARSER_VERSION = "1.9"

SUPPORTED_SPORTS = {"swimming", "cycling", "running"}

# Race blocks for workout summary backfill (subset of TRAINING_RACE_PERIODS)
WORKOUT_SUMMARY_RACE_PERIODS = [
    {"start": "2024-12-30", "end": "2025-09-07", "distance": "70.3", "race": "Santa Cruz 2025"},
    {"start": "2024-12-30", "end": "2025-09-21", "distance": "70.3", "race": "Cervia 2025"},
    {"start": "2025-09-29", "end": "2025-12-07", "distance": "", "race": "California International Marathon 2025"},
    {"start": "2025-12-29", "end": "2026-03-28", "distance": "70.3", "race": "Oceanside 2026"},
    {"start": "2026-05-18", "end": "2026-09-13", "distance": "70.3", "race": "Nice 2026"},
]
