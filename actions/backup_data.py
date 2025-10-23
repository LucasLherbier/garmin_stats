import os
import subprocess
import argparse
from datetime import datetime

def create_data_folder():
    """Create the data folder if it doesn't exist."""
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Created 'data' folder.")
    else:
        print("'data' folder already exists.")

def backup_garmin_activities(start_date):
    """Backup Garmin activities from the specified start date."""
    try:
        # Run garmin-backup command and capture output
        result = subprocess.run(
            ["garmin-backup", "--count", "all"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        activities = result.stdout.splitlines()

        for activity in activities:
            # Parse activity date (adjust this based on actual output format)
            # Example: Assume activity line contains date in YYYY-MM-DD format
            # You may need to adjust parsing logic based on actual output
            try:
                activity_date_str = activity.split()[0]  # Adjust as needed
                activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
            except (IndexError, ValueError):
                print(f"Skipping malformed activity line: {activity}")
                continue

            if activity_date < start_date:
                continue  # Skip activities before start_date

            # Create subfolder for the activity date
            date_folder = os.path.join("data", activity_date_str)
            if not os.path.exists(date_folder):
                os.makedirs(date_folder)
                print(f"Created folder for {activity_date_str}")

            # Here, you would save the activity file to the folder
            # Example: subprocess.run(["cp", activity_file, date_folder])
            # Adjust based on how garmin-backup outputs files
            print(f"Backed up activity for {activity_date_str}")

    except subprocess.CalledProcessError as e:
        print(f"Error running garmin-backup: {e.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description="Backup Garmin activities from a specific date.")
    parser.add_argument("--start_date", type=str, required=True, help="Start date in YYYY-MM-DD format")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    create_data_folder()
    backup_garmin_activities(start_date)

if __name__ == "__main__":
    main()
