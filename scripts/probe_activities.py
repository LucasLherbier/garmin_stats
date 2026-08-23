"""Temporary probe script for test activity IDs."""
import pandas as pd
from utils.utils_gcp import check_gcs_path_exists, read_csv_from_gcs, bq_client, GCP_DATASET_ID

ids = [23815970417, 23813971033]

if bq_client:
    table = f"`{GCP_DATASET_ID}.activities`"
    q = f"""
    SELECT activityId, startTimeLocal, activityTypeGrouped, activityName, duration, distance,
           averageHR, averageTemperature, elevationGain, trainingEffectLabel, trainingRace
    FROM {table}
    WHERE activityId IN ({','.join(map(str, ids))})
    """
    df = bq_client.query(q).to_dataframe()
    print("BQ activities:")
    print(df.to_string())
else:
    print("No BQ client")
    df = pd.DataFrame()

for aid in ids:
    if not df.empty and int(aid) in df["activityId"].astype(int).values:
        row = df[df["activityId"].astype(int) == int(aid)].iloc[0]
        month = pd.to_datetime(row["startTimeLocal"]).strftime("%Y-%m")
        path = f"data/raw/{month}/{aid}/{aid}.csv"
        print(f"\n{aid} path={path} exists={check_gcs_path_exists(path)}")
        if check_gcs_path_exists(path):
            csv = read_csv_from_gcs(path)
            print("columns:", list(csv.columns))
            print(csv.head(5).to_string())
