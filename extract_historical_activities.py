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
import sys

# Create formatters
class WeekProcessingFormatter(logging.Formatter):
    def format(self, record):
        # Add newline before timestamp when starting a new week
        base_format = super().format(record)
        if "Processing week:" in record.msg:
            return "\n" + base_format
        return base_format

file_formatter = WeekProcessingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(message)s')

# Setup log file
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/garmin_extraction.log')

# Delete existing log file if it exists
if os.path.exists(log_file):
    try:
        os.remove(log_file)
    except Exception as e:
        print(f"Warning: Could not delete existing log file: {e}")

# Create file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Create a filter for console output
class SuccessFilter(logging.Filter):
    def filter(self, record):
        return "Successfully processed data for week ending" in record.msg

console_handler.addFilter(SuccessFilter())

console_handler.addFilter(SuccessFilter())

script_dir = os.path.dirname(os.path.abspath(__file__))

def extract_weekly_activities(client, last_week_date, running_date):
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Extract month from the date for folder organization
    month_date = datetime.strptime(last_week_date, "%Y-%m-%d").strftime("%Y-%m")
    
    # Create the output directory relative to the script's location, organized by month
    output_dir = os.path.join(script_dir, "data", "raw", month_date)
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if raw data already exists for this week
    weekly_file = os.path.join(output_dir, f"activities_raw_{last_week_date}.csv")
    if os.path.exists(weekly_file):
        logger.info(f"Raw data already exists for {last_week_date} to {running_date}")
        # Load existing data and return it
        return pd.read_csv(weekly_file)

    try:
        processed_activities = set()
        logger.info(f"Fetching activities {last_week_date} to {running_date}")
        activities = client.get_activities_by_date(last_week_date, running_date)
        if not activities:
            logger.info("No activities found for this period.")
            return None
            
        # Define columns for reference
        columns = [
            "activityId", "activityName", "activityType",
            "startTimeLocal", "duration", "elapsedDuration", "movingDuration",
            "distance", "calories", "averageHR", "maxHR", "minHR",
            "averageTemperature", "maxTemperature", "minTemperature",
            "waterEstimated", "elevationGain", "elevationLoss", "maxElevation", "minElevation",
            "averageSpeed", "maxSpeed", "averageRunCadence", "maxRunCadence",
            "totalNumberOfStrokes", "averageStrokeDistance", "averageSwolf", "averageSwimCadence", "maxSwimCadence",
            "trainingEffect", "trainingEffectLabel", "moderateIntensityMinutes", "vigorousIntensityMinutes",
            "steps", "locationName", "differenceBodyBattery"
        ]
        activities_data = []
        
        for activity in activities:
            activity_id = activity.get("activityId")
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
                
                # Get activity date for organizing in correct month folder
                activity_date = datetime.strptime(summary.get("startTimeLocal"), "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m")
                activity_output_dir = os.path.join(script_dir, "data", "raw", activity_date)
                os.makedirs(activity_output_dir, exist_ok=True)
                
                # Save individual activity file in its corresponding month folder
                output_file = os.path.join(activity_output_dir, f"activity_{activity_id}.csv")
                if not os.path.exists(output_file):
                    pd.DataFrame([activity_data]).to_csv(output_file, index=False)
                    logger.debug(f"Exported activity details to: {output_file}")
            except Exception as error:
                logger.error(f"Failed to process activity {activity_id}: {error}")
                continue
                
        if activities_data:
            # Create weekly DataFrame from collected data
            df_weekly = pd.DataFrame(activities_data)
            weekly_file = os.path.join(output_dir, f"activities_raw_{last_week_date}.csv")
            df_weekly.to_csv(weekly_file, index=False)
            logger.debug(f"Weekly activities exported to {weekly_file} in month folder {month_date}")
            return df_weekly
        return None
            
    except Exception as error:
        logger.error(f"Failed to fetch activities: {error}")
        return None

def process_date_range(conn, start_date, end_date=None):
    """
    Process activities for a range of dates, with a single Garmin connection
    """
    # Log the command being executed
    command = f"python extract_historical_activities.py {start_date}"
    if end_date:
        command += f" --end_date {end_date}"
    logger.info(f"Executing command: {command}")
    
    # If start date is 2022-05-09, clear the entire database first
    if start_date == "2022-05-09":
        logger.info("Initial historical load detected. Clearing database...")
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS activities")
        conn.commit()
        logger.info("Database cleared. Starting fresh load from 2022-05-09")
    
    # Connect to Garmin once
    # client = connect_to_garmin()
    client = garmin_cookies.main()
    logger.info(f"Client {client}")
    if not client:
        logger.error("Failed to connect to Garmin Connect. Check your credentials.")
        conn.close()
        return

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    # Adjust start_date to previous Monday if it's not a Monday
    while start_date.weekday() != 0:  # 0 is Monday
        start_date -= timedelta(days=1)

    current_date = start_date
    while current_date <= end_date:
        # Set running_date to Sunday (end of week)
        running_date = current_date + timedelta(days=6)
        # Set last_week_date to Monday (start of week)
        last_week_date = current_date
        
        # Format dates as strings
        running_date_str = running_date.strftime("%Y-%m-%d")
        last_week_date_str = last_week_date.strftime("%Y-%m-%d")
        
        logger.info(f"Processing week: {last_week_date_str} (Mon) to {running_date_str} (Sun)")
        
        try:
            # Clean up processed folder for this date if it exists
            month_date = last_week_date.strftime("%Y-%m")
            processed_dir = os.path.join(script_dir, "data", "processed", month_date)
            os.makedirs(processed_dir, exist_ok=True)
            processed_file = os.path.join(processed_dir, f"activities_processed_{last_week_date_str}.csv")
            if os.path.exists(processed_file):
                os.remove(processed_file)
                logger.debug(f"Removed existing processed file for {last_week_date_str}")

            # Get raw data (either from API or existing file)
            df_weekly_raw = extract_weekly_activities(client, last_week_date_str, running_date_str)
            if df_weekly_raw is not None:
                # Filter activities to ensure they are within the Monday-Sunday range
                df_weekly_raw['startTimeLocal'] = pd.to_datetime(df_weekly_raw['startTimeLocal'])
                mask = (df_weekly_raw['startTimeLocal'].dt.date >= last_week_date.date()) & \
                      (df_weekly_raw['startTimeLocal'].dt.date <= running_date.date())
                df_weekly_raw = df_weekly_raw[mask]

                if not df_weekly_raw.empty:
                    # Always reprocess the data
                    df_weekly_preprocessed = main_preprocess(conn, last_week_date_str, df_weekly_raw)
                    if df_weekly_preprocessed is not None:
                        logger.info(f"Successfully processed data for week ending {running_date_str}")
                    else:
                        logger.warning(f"Data processing failed for week ending {running_date_str}")
                else:
                    logger.info(f"No activities found within Mon-Sun range for week ending {running_date_str}")
            else:
                logger.info(f"No activities found for week ending {running_date_str}")
        except Exception as e:
            logger.error(f"Error processing week ending {running_date_str}: {str(e)}")
        
        # Move to next Monday
        current_date += timedelta(days=7)
        
    
if __name__ == "__main__":
    # Connect to SQLite DB
    conn = sqlite3.connect("activities.db")
    
    parser = argparse.ArgumentParser(description='Extract Garmin activities for a date range')
    parser.add_argument('start_date', help='Start date (format: YYYY-MM-DD)')
    parser.add_argument('--end_date', help='End date (format: YYYY-MM-DD). If not provided, current date will be used.', default=None)
    
    args = parser.parse_args()
    process_date_range(conn, args.start_date, args.end_date)
    # Close database connection
    conn.close()
    logger.info("Database connection closed")