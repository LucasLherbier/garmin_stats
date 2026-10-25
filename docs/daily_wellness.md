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

GitHub Actions uses **`GARMINTOKENS`** (one line of JSON from `export_garmin_tokens.py`, starting with `{"di_token":`). CI does **not** use `USER_EMAIL` / `USER_PASSWORD` for login.

After each successful weekly sync, CI **writes the refreshed token blob back** to `GARMINTOKENS` (needs **`GH_SECRETS_PAT`**: fine-grained PAT on this repo with **Actions secrets → Read and write**, or classic PAT with `repo` scope). That keeps the secret current when Garmin rotates access/refresh tokens during the run.

**One-time bootstrap:** set both `GARMINTOKENS` and `GH_SECRETS_PAT`. Avoid re-pasting `GARMINTOKENS` from your laptop on a schedule — that can invalidate the CI session. Re-export locally only when OAuth is fully dead and CI cannot log in.

**Option A** — local password login works:

```powershell
pip install -r requirements.txt
python scripts/export_garmin_tokens.py
```

**Option B** — SSO returns 429 (browser login):

```powershell
pip install playwright requests requests-oauthlib
python -m playwright install chromium
python scripts/garmin_browser_auth.py
```

Paste the printed line into **Settings → Secrets → Actions → GARMINTOKENS**, add **GH_SECRETS_PAT**, then re-run **Weekly Garmin Sync**.

## Example query

```sql
SELECT day, sleep_score, hrv_last_night_avg, hrv_status, total_calories, total_duration_sec
FROM `garmin_stats.daily_wellness`
ORDER BY day DESC
LIMIT 14;
```
