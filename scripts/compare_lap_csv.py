"""Compare raw GCS lap CSV vs normalized laps for one activity."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import pandas as pd
from google.cloud import bigquery

from utils.pipeline.workout_summaries.parse_laps import normalize_laps_from_csv
from utils.utils_gcp import read_csv_from_gcs, check_gcs_path_exists, GCP_DATASET_ID, bq_client

ACTIVITY_ID = 23813971033


def main():
    q = f"""
    SELECT activityId, startTimeLocal, activityTypeGrouped, duration, distance, averageHR, averageSpeed
    FROM `{GCP_DATASET_ID}.activities`
    WHERE activityId = {ACTIVITY_ID}
    """
    act = bq_client.query(q).to_dataframe().iloc[0]
    month = pd.to_datetime(act["startTimeLocal"]).strftime("%Y-%m")
    path = f"data/raw/{month}/{ACTIVITY_ID}/{ACTIVITY_ID}.csv"
    print("Activity row:")
    print(act.to_string())
    print(f"\nGCS: {path} exists={check_gcs_path_exists(path)}")

    raw = read_csv_from_gcs(path)
    print(f"\nRaw CSV rows: {len(raw)}")
    print("Columns:", list(raw.columns))
    print("\n--- Raw CSV (first 8 rows) ---")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(raw.head(8).to_string())
    print("\n--- Raw CSV splits 9-12 ---")
    print(raw.iloc[8:12].to_string())

    laps, sport = normalize_laps_from_csv(raw, "running")
    print(f"\nNormalized: sport={sport} laps={len(laps)}")
    for lap in laps[:8]:
        print(lap)
    print("...")
    for lap in laps[8:12]:
        print(lap)

    duration_sum = sum(l.get("moving_time_s") or l.get("time_s") or 0 for l in laps)
    dist_sum = sum(l.get("distance_km") or 0 for l in laps)
    print(f"\nSum lap duration (s): {duration_sum:.0f} vs activity duration {act['duration']:.0f}")
    print(f"Sum lap distance (km): {dist_sum:.2f} vs activity distance {act['distance']:.2f}")
    pace_from_act = act["duration"] / act["distance"] if act["distance"] else None
    print(f"Activity implied pace: {pace_from_act:.0f} s/km ({pace_from_act//60:.0f}:{pace_from_act%60:02.0f}/km)" if pace_from_act else "")


if __name__ == "__main__":
    main()
