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

# Configure logging
class WeekProcessingFormatter(logging.Formatter):
    def format(self, record):
        base_format = super().format(record)
        if "Processing week:" in record.msg:
            return "\n" + base_format
        return base_format

file_formatter = WeekProcessingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(message)s')

# Setup log file
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.isdir(data_dir):
    os.makedirs(data_dir)

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/garmin_extraction.log')
if os.path.exists(log_file):
    try:
        os.remove(log_file)
    except Exception as e:
        print(f"Warning: Could not delete existing log file: {e}")

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class SuccessFilter(logging.Filter):
    def filter(self, record):
        return "Successfully processed data for week ending" in record.msg

console_handler.addFilter(SuccessFilter())

script_dir = os.path.dirname(os.path.abspath(__file__))

def extract_weekly_activities(client, last_week_date, execution_date):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    month_date = datetime.strptime(last_week_date, "%Y-%m-%d").strftime("%Y-%m")
    month_output_dir = os.path.join(script_dir, "data", "raw", month_date)
    os.makedirs(month_output_dir, exist_ok=True)

    try:
        processed_activities = set()
        logger.info(f"Fetching activities {last_week_date} to {execution_date}")
        activities = client.get_activities_by_date(last_week_date, execution_date)
        if not activities:
            logger.info("No activities found for this period.")
            return None

        columns = [
            "activityId", "activityName", "activityType", "startTimeLocal", "duration", "elapsedDuration",
            "movingDuration", "distance", "calories", "averageHR", "maxHR", "minHR",
            "averageTemperature", "maxTemperature", "minTemperature", "waterEstimated",
            "elevationGain", "elevationLoss", "maxElevation", "minElevation", "averageSpeed",
            "maxSpeed", "averageRunCadence", "maxRunCadence", "totalNumberOfStrokes",
            "averageStrokeDistance", "averageSwolf", "averageSwimCadence", "maxSwimCadence",
            "trainingEffect", "trainingEffectLabel", "moderateIntensityMinutes",
            "vigorousIntensityMinutes", "steps", "locationName", "differenceBodyBattery"
        ]
        activities_data = []

        for activity in activities:
            activity_id = activity.get("activityId")
            activity_month = datetime.strptime(activity.get("startTimeLocal"), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m")
            activity_output_dir = os.path.join(script_dir, "data", "raw", activity_month, str(activity_id))
            if os.path.isdir(activity_output_dir):
                logger.info(f"Data already exists for Activity ID {str(activity_id)} in folder {activity_month}")
                return pd.read_csv(os.path.join(activity_output_dir, f"{str(activity_id)}.csv"))
            if activity_id in processed_activities:
                continue
            processed_activities.add(activity_id)
            try:
                logger.debug(f"Processing activity ID: {activity_id}")
                activity_details = client.get_activity(activity_id)
                summary = activity_details.get("summaryDTO", {})
                activity_data = {
                    "activityId": activity_details.get("activityId"),
                    "activityName": activity_details.get("activityName"),
                    "activityType": activity_details.get("activityTypeDTO", {}).get("typeKey"),
                    "startTimeLocal": summary.get("startTimeLocal"),
                    "duration": summary.get("duration"),
                    "elapsedDuration": summary.get("elapsedDuration"),
                    "movingDuration": summary.get("movingDuration"),
                    "distance": summary.get("distance"),
                    "calories": summary.get("calories"),
                    "averageHR": summary.get("averageHR"),
                    "maxHR": summary.get("maxHR"),
                    "minHR": summary.get("minHR"),
                    "averageTemperature": summary.get("averageTemperature"),
                    "maxTemperature": summary.get("maxTemperature"),
                    "minTemperature": summary.get("minTemperature"),
                    "waterEstimated": summary.get("waterEstimated"),
                    "elevationGain": summary.get("elevationGain"),
                    "elevationLoss": summary.get("elevationLoss"),
                    "maxElevation": summary.get("maxElevation"),
                    "minElevation": summary.get("minElevation"),
                    "averageSpeed": summary.get("averageSpeed"),
                    "maxSpeed": summary.get("maxSpeed"),
                    "averageRunCadence": summary.get("averageRunCadence"),
                    "maxRunCadence": summary.get("maxRunCadence"),
                    "totalNumberOfStrokes": summary.get("totalNumberOfStrokes"),
                    "averageStrokeDistance": summary.get("averageStrokeDistance"),
                    "averageSwolf": summary.get("averageSwolf"),
                    "averageSwimCadence": summary.get("averageSwimCadence"),
                    "maxSwimCadence": summary.get("maxSwimCadence"),
                    "trainingEffect": summary.get("trainingEffect"),
                    "trainingEffectLabel": summary.get("trainingEffectLabel"),
                    "moderateIntensityMinutes": summary.get("moderateIntensityMinutes"),
                    "vigorousIntensityMinutes": summary.get("vigorousIntensityMinutes"),
                    "steps": summary.get("steps"),
                    "locationName": activity_details.get("locationName"),
                    "differenceBodyBattery": summary.get("differenceBodyBattery"),
                }
                activities_data.append(activity_data)

                os.makedirs(activity_output_dir, exist_ok=True)

                # Download and save GPX, TCX, CSV
                formats = [
                    (client.ActivityDownloadFormat.GPX, ".gpx"),
                    (client.ActivityDownloadFormat.TCX, ".tcx"),
                    (client.ActivityDownloadFormat.CSV, ".csv")
                ]
                all_saved = True
                for fmt, ext in formats:
                    try:
                        data = client.download_activity(activity_id, dl_fmt=fmt)
                        output_file = os.path.join(activity_output_dir, f"{str(activity_id)}{ext}")
                        with open(output_file, "wb") as fb:
                            fb.write(data)
                    except Exception as e:
                        logger.error(f"Failed to save {ext} for activity {activity_id}: {e}")
                        all_saved = False

                logger.info(f"Activity {activity_id} - Last extracted: {datetime.now()} - All formats saved: {all_saved}")

                output_file = os.path.join(script_dir, "data", "raw", activity_month, f"{activity_id}_info.csv")
                if not os.path.exists(output_file):
                    pd.DataFrame([activity_data]).to_csv(output_file, index=False)
            except Exception as error:
                logger.error(f"Failed to process activity {activity_id}: {error}")
                continue

        if activities_data:
            df_weekly = pd.DataFrame(activities_data)
            output_file = os.path.join(script_dir, "data", "raw", activity_month, f"activity_{activity_id}.csv")
            weekly_file = os.path.join(script_dir, "data", "raw", activity_month, f"raw_{last_week_date}.csv")
            df_weekly.to_csv(weekly_file, index=False)
            logger.debug(f"Weekly activities exported to {weekly_file} in month folder {month_date}")
            return df_weekly
        return None

    except Exception as error:
        logger.error(f"Failed to fetch activities: {error}")
        return None

def process_date_range(conn, start_date, end_date=None):
    command = f"python extract_historical_activities.py {start_date}"
    if end_date:
        command += f" --end_date {end_date}"
    logger.info(f"Executing command: {command}")

    if start_date == "2022-05-09":
        logger.info("Initial historical load detected. Clearing database...")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS activities")
        conn.commit()
        logger.info("Database cleared. Starting fresh load from 2022-05-09")

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    # Connect to Garmin once
    client = garmin_cookies.main()
    logger.info(f"Client {client}")
    if not client:
        logger.error("Failed to connect to Garmin Connect. Check your credentials.")
        conn.close()
        return
    
    while start_date.weekday() != 0:
        start_date -= timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        execution_date = current_date + timedelta(days=6)
        last_week_date_str = current_date.strftime("%Y-%m-%d")
        execution_date_str = execution_date.strftime("%Y-%m-%d")

        logger.info(f"Processing week: {last_week_date_str} (Mon) to {execution_date_str} (Sun)")

        try:
            processed_dir = os.path.join(script_dir, "data", "processed", last_week_date_str)
            os.makedirs(processed_dir, exist_ok=True)
            processed_file = os.path.join(processed_dir, f"activities_processed_{last_week_date_str}.csv")
            if os.path.exists(processed_file):
                os.remove(processed_file)
                logger.debug(f"Removed existing processed file for {last_week_date_str}")

            df_weekly_raw = extract_weekly_activities(client, last_week_date_str, execution_date_str)
            if df_weekly_raw is not None:
                df_weekly_raw['startTimeLocal'] = pd.to_datetime(df_weekly_raw['startTimeLocal'])
                mask = (df_weekly_raw['startTimeLocal'].dt.date >= current_date.date()) & \
                      (df_weekly_raw['startTimeLocal'].dt.date <= execution_date.date())
                df_weekly_raw = df_weekly_raw[mask]
                if not df_weekly_raw.empty:
                    df_weekly_preprocessed = main_preprocess(conn, last_week_date_str, df_weekly_raw)
                    if df_weekly_preprocessed is not None:
                        logger.info(f"Successfully processed data for week ending {execution_date_str}")
                    else:
                        logger.warning(f"Data processing failed for week ending {execution_date_str}")
                else:
                    logger.info(f"No activities found within Mon-Sun range for week ending {execution_date_str}")
            else:
                logger.info(f"No activities found for week ending {execution_date_str}")
        except Exception as e:
            logger.error(f"Error processing week ending {execution_date_str}: {str(e)}")

        current_date += timedelta(days=7)

if __name__ == "__main__":
    conn = sqlite3.connect("activities.db")
    parser = argparse.ArgumentParser(description='Extract Garmin activities for a date range')
    parser.add_argument('--start_date', help='Start date (format: YYYY-MM-DD)')
    parser.add_argument('--end_date', help='End date (format: YYYY-MM-DD). If not provided, current date will be used.', default=None)
    args = parser.parse_args()
    print(args.start_date)
    print('ok')
    process_date_range(conn, args.start_date, args.end_date)
    conn.close()
    logger.info("Database connection closed")
