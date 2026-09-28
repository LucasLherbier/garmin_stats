# Daily wellness pipeline

One row per **calendar day** in BigQuery table **`daily_wellness`**: sleep, HRV, stress/body battery, and activity rollups from `activities`.

## Fields

| Column | Source |
|--------|--------|
| `day` | Calendar date (PK) |
| `sleep_score`, `sleep_*_sec` | Garmin `get_sleep_data` |
| `hrv_last_night_avg`, `hrv_status`, `hrv_weekly_avg` | Garmin `get_hrv_data` |
| `resting_hr`, `daily_steps`, `daily_calories` | Garmin `get_stats` |
| `body_battery_high`, `body_battery_low` | Garmin `get_body_battery` |
| `avg_stress` | Garmin `get_stress_data` |
| `activity_count`, `total_duration_sec`, `total_calories` | Rollup from `activities` |
| `swim_distance_km`, `bike_distance_km`, `run_distance_km`, `elevation_gain_m` | Rollup from `activities` |
| `extract_status`, `extract_errors`, `extracted_at` | Pipeline metadata |

Activity calories take precedence over Garmin daily calories when sessions exist that day.

## CLI

From repo root (Garmin + BigQuery credentials required):

```powershell
# Last 7 days (default — good for testing)
python scripts/backfill_daily_wellness.py

# Dry run
python scripts/backfill_daily_wellness.py --dry-run

# Full history from 2022-05-01 (chunked uploads, skips existing days)
python scripts/backfill_daily_wellness.py --full-backfill

# Custom range
python scripts/backfill_daily_wellness.py --since 2022-05-01 --until 2026-08-25
```

**API efficiency:** body battery and resting HR are fetched in **bulk range calls**. Sleep, HRV, and daily stats still require **one call per day** (~3 calls/day). Full backfill defaults to `--delay 1.0`, `--chunk-days 31`, and `--skip-existing`.

## Automation

- **Weekly GitHub Action** runs `backfill_daily_wellness.py` (last 7 days) after activity extract.
- **Weekly extract** also upserts daily wellness for each processed Mon–Sun window.

GitHub runners are often **IP rate-limited** on Garmin password login. The weekly Action logs in **once** and reuses that session for activities and wellness. Use a **GARMINTOKENS** repo secret (OAuth blob from a local login):

```powershell
python scripts/export_garmin_tokens.py
```

Copy the printed line into **Settings → Secrets → Actions → GARMINTOKENS**. Refresh when tokens expire (re-run the script after a successful local login).

**CI never uses password login** (GitHub runner IPs are rate-limited). If the workflow fails at Garmin login, the `GARMINTOKENS` secret is missing, expired, or was exported with the wrong `garminconnect` version — re-run `export_garmin_tokens.py` with `pip install -r requirements.txt` (pins `garminconnect==0.2.30`).

## Example query

```sql
SELECT day, sleep_score, hrv_last_night_avg, hrv_status, total_calories, total_duration_sec
FROM `garmin_stats.daily_wellness`
ORDER BY day DESC
LIMIT 14;
```
