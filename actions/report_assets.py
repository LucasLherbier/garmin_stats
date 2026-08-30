"""Load GCS assets (GPX, TCX, FIT) for HTML activity reports."""

from __future__ import annotations

from datetime import date

import pandas as pd

from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.power_curve import power_profile_from_fit, power_profile_from_telemetry
from actions.report_map import gpx_track_points
from utils.utils_gcp import bucket, check_gcs_path_exists


def load_report_assets(activity_id: int, start_time_local, sport: str):
    power_profile = None
    hr_series = None
    track_points = None
    telemetry_df = None

    if not bucket:
        return power_profile, hr_series, track_points, telemetry_df

    if start_time_local:
        month = str(start_time_local)[:7]
    else:
        month = date.today().strftime("%Y-%m")
    base = f"data/raw/{month}/{activity_id}"

    gpx_path = f"{base}/{activity_id}.gpx"
    tcx_path = f"{base}/{activity_id}.tcx"
    fit_path = f"{base}/{activity_id}.fit"

    try:
        if check_gcs_path_exists(gpx_path):
            gpx_content = bucket.blob(gpx_path).download_as_bytes()
            track_points = gpx_track_points(gpx_content)

        if check_gcs_path_exists(tcx_path):
            tcx_content = bucket.blob(tcx_path).download_as_bytes()
            df_tcx = parse_tcx_to_dataframe(tcx_content)
            cols = [
                c
                for c in ("Time", "HeartRate", "Cadence", "Speed", "Watts", "Altitude", "Distance")
                if c in df_tcx.columns
            ]
            if cols:
                telemetry_df = df_tcx[cols].copy()
            if "HeartRate" in df_tcx.columns:
                hr_series = df_tcx["HeartRate"]
            if sport == "cycling":
                if check_gcs_path_exists(fit_path):
                    fit_content = bucket.blob(fit_path).download_as_bytes()
                    power_profile = power_profile_from_fit(fit_content)
                elif "Watts" in df_tcx.columns:
                    power_profile = power_profile_from_telemetry(df_tcx["Time"], df_tcx["Watts"])
    except Exception:
        pass

    return power_profile, hr_series, track_points, telemetry_df
