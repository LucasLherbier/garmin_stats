import os
import logging
import pandas as pd
from connect_to_garmin import connect_to_garmin
from preprocess_activities import main_preprocess
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Function to get all activities and save each as a separate file 
def extract_weekly_activities(client, last_week_date, running_date):
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Create the output directory relative to the script's location
    output_dir = os.path.join(script_dir, "data", "raw", last_week_date)
    os.makedirs(output_dir, exist_ok=True)
    try:
        processed_activities = set()
        logger.info(f"Fetching activities {last_week_date} to {running_date}")
        activities = client.get_activities_by_date(last_week_date, running_date)
        if not activities:
            logger.info("No more activities found.")
            return None
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
        df_weekly = pd.DataFrame(columns=columns)
        for activity in activities:
            activity_id = activity.get("activityId")
            print(activity_id)
            if activity_id in processed_activities:
                continue
            processed_activities.add(activity_id)
            try:
                logger.info(f"Processing activity ID: {activity_id}")
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
                df = pd.DataFrame([activity_data])
                df_weekly = pd.concat([df_weekly, df], ignore_index=True)
                output_file = os.path.join(output_dir, f"activity_{activity_id}.csv")
                df.to_csv(output_file, index=False)
                logger.info(f"Exported activity details to: {output_file}")
            except Exception as error:
                logger.error(f"Failed to process activity {activity_id}: {error}")
                continue
    except Exception as error:
        logger.error(f"Failed to fetch activities: {error}")
        return None
    logger.info(f"All activities exported to {output_dir}")
    weekly_dir = os.path.join(output_dir, f"activities_raw_{last_week_date}.csv")
    df_weekly.to_csv(weekly_dir, index=False)
    return df_weekly


def main(conn, running_date=None):
    # Define the date you want to check (format: YYYY-MM-DD)
    if running_date is None:
        raise ValueError("running_date must be provided as an argument")
    running_date = datetime.strptime(running_date, "%Y-%m-%d")
    last_week_date = (running_date - timedelta(days=7)).strftime("%Y-%m-%d")
    running_date = running_date.strftime("%Y-%m-%d")

    # Connect to Garmin
    client = connect_to_garmin()
    if not client:
        return "Failed to connect to Garmin Connect. Check your credentials."
    
    # # Get activities for the specific date
    df_weekly_raw =  extract_weekly_activities(client, last_week_date,  current_date)
    
    df_weekly_raw = pd.read_csv("data/raw/2025-09-04/weekly_activities.csv", delimiter=';')  # Use the correct delimiter
    df_weekly_preproccessed = main_preprocess(conn, last_week_date, df_weekly_raw)
    return 'Processing complete. Processed data saved to database and CSV.'

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Extract Garmin activities for a specific date')
    parser.add_argument('running_date', help='The date to extract activities for (format: YYYY-MM-DD)')
    args = parser.parse_args()
    main(conn=None, running_date=args.running_date)
