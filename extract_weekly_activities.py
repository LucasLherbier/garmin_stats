import os
import logging
import pandas as pd
import sqlite3
from connect_to_garmin import connect_to_garmin
from preprocess_activities import main_preprocess
from datetime import datetime, timedelta
import argparse
from time import sleep
import garmin_cookies
from utils_gcp import (
    bucket, check_gcs_path_exists, read_csv_from_gcs, 
    upload_to_gcs, log_to_bigquery
)
import sys
import io

# Configure logging
console_formatter = logging.Formatter('%(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(console_handler)

script_dir = os.path.dirname(os.path.abspath(__file__))

def extract_and_process_activity(activity_id, client, base_path):
    """
    Called only if the activity doesn't exist on GCS.
    Extracts metadata and uploads all formats (GPX, TCX, CSV) to the bucket.
    """
    
    logger.debug(f"Processing activity ID: {activity_id}")
    
    try:
        # 1. Extract metadata from SummaryDTO
        activity_details = client.get_activity(activity_id)
        summary = activity_details.get("summaryDTO", {})
        fields = [
            "activityId", "startTimeLocal", "duration", "elapsedDuration", 
            "movingDuration", "distance", "calories", "averageHR", "maxHR", "minHR", 
            "averageTemperature", "maxTemperature", "minTemperature", "waterEstimated", 
            "elevationGain", "elevationLoss", "maxElevation", "minElevation", "averageSpeed", 
            "maxSpeed", "averageRunCadence", "maxRunCadence", "totalNumberOfStrokes", 
            "averageStrokeDistance", "averageSwolf", "averageSwimCadence", "maxSwimCadence", 
            "trainingEffect", "trainingEffectLabel", "moderateIntensityMinutes", 
            "vigorousIntensityMinutes", "steps", "differenceBodyBattery"
        ]
        
        # Build the metadata dictionary
        activity_data = {field: summary.get(field) for field in fields}
        activity_data.update({
            "activityType": activity_details.get("activityTypeDTO", {}).get("typeKey"),
            "locationName": activity_details.get("locationName"),
            "activityId": activity_details.get("activityId"),
            "activityName": activity_details.get("activityName")
        })

        # 2. Download and Upload Raw Formats (GPX, TCX, CSV)
        # Mapping Garmin formats to GCS extensions and MIME types
        formats_to_process = [
            (client.ActivityDownloadFormat.GPX, ".gpx", 'application/gpx+xml'),
            (client.ActivityDownloadFormat.TCX, ".tcx", 'application/vnd.garmin.tcx+xml'),
            (client.ActivityDownloadFormat.CSV, ".csv", 'text/csv')
        ]

        for fmt, ext, ctype in formats_to_process:
            try:
                # API Call to download the file
                data = client.download_activity(activity_id, dl_fmt=fmt)
                gcs_path = f"{base_path}/{activity_id}{ext}"
                
                # Unified upload and log
                upload_to_gcs(data, gcs_path, activity_id, ctype)
                
            except Exception as e:
                # Some activities (like Gym/Yoga) won't have GPX/TCX files
                logger.warning(f"Format {ext} not available for activity {activity_id}: {e}")

        # 3. Upload Summary Data as a single CSV info file
        gcs_info_path = f"{base_path}/{activity_id}_information.csv"
        df_info = pd.DataFrame([activity_data])
        upload_to_gcs(df_info, gcs_info_path, activity_id)
        
        return activity_data
    except Exception as e:
        logger.error(f"Failed to process activity {activity_id}: {e}")
        # Log failure to BigQuery
        log_to_bigquery(activity_id, f"{activity_id}_information.csv", f"{base_path}/{activity_id}_information.csv", "FAILED")
        raise e


def extract_weekly_activities(client, last_week_date, execution_date):
    """
    Optimized for GCP: Fetches and stores activities in GCS.
    Skips info file creation if it already exists.
    """
    try:
        logger.info(f"Fetching activities {last_week_date} to {execution_date}")
        activities = client.get_activities_by_date(last_week_date, execution_date)
        
        if not activities:
            logger.info("No activities found for this period.")
            return None

        activities_data = []
        processed_ids = set()

        for activity in activities:
            activity_id = activity.get("activityId")
            if activity_id in processed_ids:
                continue
            
            # Format month from activity timestamp
            start_time = activity.get("startTimeLocal")
            activity_month = pd.to_datetime(start_time).strftime("%Y-%m")
            
            # GCP Paths
            base_path = f"data/raw/{activity_month}/{activity_id}"
            gcs_info_path = f"{base_path}/{activity_id}_information.csv"

            # Skip if file already exists in GCS
            if check_gcs_path_exists(gcs_info_path):
                logger.info(f"- {activity_id} already exists in GCS. Skipping.")
                df_cached = read_csv_from_gcs(gcs_info_path)
                activities_data.extend(df_cached.to_dict('records'))
            else: 
                activity_info = extract_and_process_activity(activity_id, client, base_path)
                activities_data.append(activity_info)
            
            processed_ids.add(activity_id)
            
        if activities_data:
            df_weekly = pd.DataFrame(activities_data)
            summary_month = datetime.strptime(last_week_date, "%Y-%m-%d").strftime("%Y-%m")
            gcs_weekly_path = f"data/raw/{summary_month}/{last_week_date}_raw.csv"
            upload_to_gcs(df_weekly, gcs_weekly_path,f"{last_week_date}_raw")
            return df_weekly


    except Exception as error:
        logger.error(f"Global extraction failure: {error}")
    
    return None

def process_date_range(start_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.now()

    # Connect to Garmin once
    client = garmin_cookies.main()
    logger.info(f"Client {client}")
    if not client:
        logger.error("Failed to connect to Garmin Connect. Check your credentials.")
        return
    
    while start_date.weekday() != 0:
        start_date -= timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        execution_date = current_date + timedelta(days=6)
        last_week_date_str = current_date.strftime("%Y-%m-%d")
        execution_date_str = execution_date.strftime("%Y-%m-%d")

        logger.info(f"\nProcessing week: {last_week_date_str} (Mon) to {execution_date_str} (Sun)")

        try:
            df = extract_weekly_activities(client, last_week_date_str, execution_date_str)
            if df is not None and not df.empty:
                main_preprocess(last_week_date_str, df)
            else:
                logger.info(f"No activities to process for week ending {execution_date_str}")
        except Exception as e:
            logger.error(f"Error processing week ending {execution_date_str}: {e}")

        current_date += timedelta(days=7)

if __name__ == "__main__":
    # Check if GCS bucket is working
    try:
        if not bucket or not bucket.exists():
            logger.error("GCS bucket is not configured or inaccessible. Stopping.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error verifying GCS bucket: {e}")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Extract Garmin activities starting from a date')
    parser.add_argument('--start_date', help='Start date (format: YYYY-MM-DD)', required=True)
    args = parser.parse_args()
    process_date_range(args.start_date)

