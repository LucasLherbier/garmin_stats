# Workout summaries pipeline

Garmin **lap CSVs** (in GCS) are parsed into structured rows in BigQuery table **`workout_summaries`**. That data feeds race-prep coaching (Phase B) and debugging via CLI.

**Single orchestration module:** `utils/pipeline/workout_summaries/process.py`  
All parse, scope, skip-existing, and upload logic lives there. Callers only invoke its public functions.

| Caller | Function |
|--------|----------|
| `scripts/backfill_workout_summaries.py` | `process_workout_summaries(...)` — CLI flags (`--since`, `--force`, `--dry-run`, …) |
| `utils/pipeline/extract_weekly_activities.py` (after preprocess) | `process_workout_summaries_incremental(activity_ids)` — skip existing, upload |

---

## Scope

Only activities whose **local start date** falls in `WORKOUT_SUMMARY_RACE_PERIODS` (`utils/pipeline/workout_summaries/constants.py`):

| Start | End | Race |
|-------|-----|------|
| 2024-12-30 | 2025-09-07 | Santa Cruz 2025 |
| 2024-12-30 | 2025-09-21 | Cervia 2025 |
| 2025-09-29 | 2025-12-07 | California International Marathon 2025 |
| 2025-12-29 | 2026-03-28 | Oceanside 2026 |
| 2026-05-18 | 2026-09-13 | Nice 2026 |

Sports: **running**, **cycling**, **swimming** (`SUPPORTED_SPORTS`).

This is a **subset** of `TRAINING_RACE_PERIODS` in `preprocess_activities.py` (historical races are not summarized).

**Parser version:** `PARSER_VERSION` in `constants.py` (currently **1.8**). Bump when lap/phase/structure logic changes, then backfill with `--force`.

---

## Data flow

```text
GCS  data/raw/{YYYY-MM}/{activityId}/{activityId}.csv
  + BQ activities (metadata, trainingRace, …)
        │
        ▼
  process.py  →  parse_laps → lap_analysis → segments → structure_summary
        │
        ▼
  BQ workout_summaries
```

**Prerequisites per activity**

1. Lap CSV exists in GCS (from weekly extract).
2. Row exists in `activities` (from preprocess).

Incremental runs after each weekly extract: extract → preprocess → `process_workout_summaries_incremental`.

---

## Module layout

| Module | Role |
|--------|------|
| `parse_laps.py` | Normalize lap CSV; filter junk laps; run moving pace; bike NP/power/speed/HR |
| `lap_analysis.py` | Per-lap JSON table (Phase, Pace%/NP%/Spd%, vsPrev, HR%, …) |
| `segments.py` | Merge phases into work/rest blocks; interval heuristics |
| `structure_summary.py` | One-line main workout pattern for coach headline |
| `process.py` | BQ fetch, GCS read, row build, upload, incremental entry point |

---

## BigQuery: `workout_summaries`

One row per activity (when processed).

| Field | Role |
|-------|------|
| `activityId`, `startTimeLocal`, `Week`, `month_key`, `sport`, `activityName` | Identity |
| `duration`, `distance`, `averageHR`, `elevationGain`, `trainingRace`, … | Activity scalars (from `activities`) |
| `laps` | Normalized lap JSON (source of truth for raw lap fields) |
| `lap_analysis` | Full per-split table for deep coach / debug |
| `segments` | Merged work/rest/warmup/cooldown blocks |
| `structure_summary` | Short main-structure line (heuristic) |
| `summary_text` | Garmin-style one-liner + `\| structure_summary` |
| `workout_type`, `workout_type_source` | From training effect label |
| `parser_version`, `parse_status`, `parsed_at`, `csv_path` | Versioning & quality |
| `lap_count` | Number of normalized laps |

**`parse_status` values**

| Status | Meaning |
|--------|---------|
| `ok` | Parsed and stored |
| `no_csv` | Lap CSV missing in GCS |
| `empty_csv` | CSV present but unusable |
| `unsupported_sport` | Not swim/bike/run |

Example checks:

```sql
SELECT activityId, sport, parser_version, structure_summary, parse_status
FROM `garmin_stats.workout_summaries`
ORDER BY startTimeLocal DESC
LIMIT 20;

SELECT lap_analysis
FROM `garmin_stats.workout_summaries`
WHERE activityId = 23829351216;
```

---

## CLI (backfill / manual)

From repo root (GCS + BigQuery credentials required):

```powershell
cd c:\Users\llherbier\Downloads\Projects\garmin_stats

# Debug one or two activities (no upload)
python scripts/backfill_workout_summaries.py --activity-ids 23813971033 23829351216 --dry-run --verbose --force

# Race-scoped date range (re-upload only with --force)
python scripts/backfill_workout_summaries.py --since 2024-12-30 --force

# Incremental behavior (default): skip IDs already in workout_summaries
python scripts/backfill_workout_summaries.py --since 2026-01-01
```

| Flag | Effect |
|------|--------|
| `--activity-ids` | Limit to these Garmin IDs (still race-period scoped in SQL) |
| `--since` / `--until` | Date filter on `startTimeLocal` |
| `--last-year` | `--since` = 365 days ago |
| `--force` | Delete existing rows for processed IDs, re-parse, re-upload |
| `--dry-run` | Parse only; no BQ upload |
| `--verbose` | Log lap table, segments, structure line per activity |

**When to use what**

| Situation | Action |
|-----------|--------|
| Normal weekly extract | Automatic `process_workout_summaries_incremental` |
| New race period / missed weeks | `backfill_workout_summaries.py --since …` |
| Parser upgrade (`PARSER_VERSION`) | Full or partial backfill with `--force` |

Debug helper: `scripts/compare_lap_csv.py` — raw CSV vs normalized laps for one activity.

---

## Coach integration (Phase B) — memory for 150+ workouts

Phase B is **not required to be RAG on day one**. The table is already a **compressed memory** of every scoped workout.

### What fits in context vs what does not

| Layer | Typical size | Use in LLM |
|-------|----------------|------------|
| **Prep index** — date, sport, distance, duration, HR, `structure_summary` | ~150 lines × ~1 line | **Whole selected race prep block** (150+ activities is fine) |
| **Block detail** — `segments` | Medium | Last **1–2 weeks**, or user-selected activity |
| **Split detail** — `lap_analysis` | Large per workout | **One activity** (expanders, “deep dive”, or follow-up question) |

Do **not** put all `lap_analysis` JSON for 150 activities in one prompt; that is what blows context limits.

### Recommended pattern (tiered context)

1. **Always:** SQL bundle for the **selected race window** — lightweight columns + `structure_summary` for every row with `parse_status = 'ok'`. That is your longitudinal “what I did this prep.”
2. **Weekly coach pass:** Same query filtered to **last 7 days** (or calendar week), plus `segments` for those rows only.
3. **Drill-down:** On demand, load `lap_analysis` for a single `activityId` from BigQuery.
4. **Optional later — RAG:** If prep grows very large or you ask free-form questions (“sessions like my Zwift 3×20”), embed **`structure_summary` + `summary_text`** (and maybe segment labels), store vectors in BQ or a small index, retrieve **top-k** by similarity + date/sport filters. Use retrieved rows plus recent week detail in the prompt.
5. **Optional later — coach memory table:** After each weekly narrative, store a short **weekly rollup** in BQ; the next prompt reads **chain of weekly notes** + **prep index** instead of re-summarizing 150 workouts from scratch every time.

So: **7 activities** is a good default for *deep* weekly feedback; **150+** is handled by the **prep index** (and optionally RAG or weekly rollups), not by stuffing every lap table into one call.

### Race tab (implemented)

- **Queries:** `get_workout_summaries_prep_index_query`, `get_workout_summaries_recent_query` in `utils/sql_queries.py`
- **LLM:** `actions/race_coach.py` — full prep index + recent segment blocks in the prompt (Google Gemini)
- **UI:** Race tab → **Prep coach**; expand sessions for lap tables; **Generate weekly coach feedback**

Env: `GEMINI_API_KEY` (`.env` or Streamlit secrets on Render). Default model: **`gemini-3.1-flash-lite`** (`actions/race_coach.py` → `COACH_GEMINI_MODEL`; override with `GEMINI_MODEL`). Optional `GEMINI_MODEL_FALLBACKS` (comma-separated) only if you want retries on other models.

---

## Known limitations

- Structure detection is heuristic (outdoor rides may read as “mixed efforts” rather than perfect 3×20).
- Swim phases are less tuned than run/bike.
- Re-parse after parser changes requires `--force` backfill; incremental skips existing IDs.
- `structure_summary` must exist in the BigQuery table schema (add column before first upload if migrating).
