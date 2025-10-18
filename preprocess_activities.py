import os
import pandas as pd
from datetime import timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))

def load_and_clean_data(df):
    """Load and clean data from a raw DataFrame."""
    numeric_cols = [
        'averageHR', 'maxHR', 'minHR', 'distance', 'calories', 'averageTemperature',
        'maxTemperature', 'minTemperature', 'waterEstimated', 'elevationGain',
        'elevationLoss', 'maxElevation', 'minElevation', 'averageSpeed', 'maxSpeed',
        'averageRunCadence', 'maxRunCadence', 'totalNumberOfStrokes', 'averageStrokeDistance',
        'averageSwolf', 'averageSwimCadence', 'maxSwimCadence', 'trainingEffect',
        'moderateIntensityMinutes', 'vigorousIntensityMinutes', 'steps', 'differenceBodyBattery'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.').str.replace('--', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df['distance'] = df['distance'] / 1000  # Convert distance to kilometers
    if 'startTimeLocal' in df.columns:
        df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])
        df['Day'] = df['startTimeLocal'].dt.date
        df['Week'] = df['startTimeLocal'].apply(lambda x: (x - timedelta(days=x.dayofweek))).dt.date
        df['Month'] = df['startTimeLocal'].to_numpy().astype('datetime64[M]')
    if 'duration' in df.columns:
        df['durationFormatted'] = df['duration'].apply(
            lambda x: f"{int(x // 3600):02d}:{int((x % 3600) // 60):02d}:{int(x % 60):02d}"
        )
    return df

def split_biking_musculation_activities_2023(df):
    """Split activities containing 'Bike Indoor & Musculation' into two separate activities."""
    if 'activityName' not in df.columns:
        return df
    mask = df['activityName'].str.contains('&')
    if not mask.any():
        return df
    df['duration_seconds'] = df['duration']
    split_rows = df[mask].copy()
    new_rows = pd.concat([
        split_rows.assign(
            activityType='virtual_cycling',
            activityName='Bike Indoor',
            distance=30,
            calories=split_rows['calories'] // 2,
            duration=split_rows['duration_seconds'] / 2
        ),
        split_rows.assign(
            activityType='gym_fitness',
            activityName='Muscular Reinforcement',
            distance=30,
            calories=split_rows['calories'] // 2,
            duration=split_rows['duration_seconds'] / 2
        )
    ])
    df = pd.concat([df[~mask], new_rows]).reset_index(drop=True)
    return df

def harmonize_zwift_activities(df):
    """Harmonize heart rate values for Zwift activities."""
    if not all(col in df.columns for col in ['startTimeLocal', 'activityName', 'averageHR', 'maxHR']):
        return df
    unique_days = df['Day'].unique()
    for day in unique_days:
        max_avg_hr = df.loc[(df['Day'] == day) & (df['activityName'] == "Cardio Zwift"), 'averageHR'].max()
        max_max_hr = df.loc[(df['Day'] == day) & (df['activityName'] == "Cardio Zwift"), 'maxHR'].max()
        df.loc[(df['Day'] == day) & (df['activityName'].str.startswith('Zwift', na=False)), 'averageHR'] = max_avg_hr
        df.loc[(df['Day'] == day) & (df['activityName'].str.startswith('Zwift', na=False)), 'maxHR'] = max_max_hr
    df = df.loc[df['activityName'] != "Cardio Zwift"]
    return df

def standardize_activity_types(df):
    """Standardize activity types for better categorization."""
    if 'activityType' not in df.columns:
        return df

    activity_mapping = {
        'cycling': 'cycling',
        'biking': 'cycling',
        'virtual_ride': 'cycling',
        'running': 'running',
        'swimming': 'swimming',
        'rowing': 'rowing',
        'walking': 'hiking',
        'hiking': 'hiking',
        'strength_training': 'musculation',
        'backcountry_skiing': 'backcountry_skiing',
        'cross_country_skiing_ws': 'cross_country_skiing',
        'skate_skiing_ws': 'cross_country_skiing',
        'resort_skiing': 'skiing',
        'fitness_equipment': 'physical_reinforcement',
        'indoor_cardio': 'physical_reinforcement',
    }

    df['activityTypeGrouped'] = None  # Initialize the column

    for old, new in activity_mapping.items():
        df.loc[df['activityType'].str.contains(old, case=False, na=False), 'activityTypeGrouped'] = new

    # Handle gym activities
    df.loc[df['activityType'].str.contains('gym', case=False, na=False), 'activityTypeGrouped'] = 'gym_fitness'

    # Handle swimming distance
    df.loc[(df['activityType'].str.contains('swim', case=False, na=False)) & (df['distance'] > 100), 'distance'] /= 1000

    return df

def assign_periods(row):
    """Assign training periods and off-season status."""
    training_race_periods = [
        {'start': '2022-05-02', 'end': '2022-07-15', 'distance': 'Olympic', 'race': 'Magog 2022'},
        {'start': '2022-05-02', 'end': '2022-09-09', 'distance': 'Olympic', 'race': 'Esprint Montréal 2022'},
        {'start': '2023-01-06', 'end': '2023-07-14', 'distance': 'Olympic', 'race': 'Magog 2023'},
        {'start': '2023-01-06', 'end': '2023-08-19', 'distance': '70.3', 'race': 'Mont Tremblant 2023'},
        {'start': '2023-01-06', 'end': '2023-09-09', 'distance': 'Sprint', 'race': 'Esprint Montréal 2023'},
        {'start': '2023-01-06', 'end': '2024-06-21', 'distance': 'Olympic', 'race': 'Mont Tremblant 2024'},
        {'start': '2023-12-04', 'end': '2024-07-13', 'distance': '140.6', 'race': 'Vitoria Gasteiz 2024'},
        {'start': '2024-12-30', 'end': '2025-09-06', 'distance': '70.3', 'race': 'Santa Cruz 2025'},
        {'start': '2024-12-30', 'end': '2025-09-20', 'distance': '70.3', 'race': 'Cervia 2025'}
    ]
    off_season_false_periods = [
        {'start': '2022-05-02', 'end': '2022-09-10'},
        {'start': '2023-01-06', 'end': '2023-09-10'},
        {'start': '2023-12-04', 'end': '2024-07-14'},
        {'start': '2024-12-30', 'end': '2025-09-21'}
    ]
    date = row['startTimeLocal']
    races = []
    off_season = True
    for period in training_race_periods:
        if pd.to_datetime(period['start']) <= date <= pd.to_datetime(period['end']):
            races.append(period['race'])
    for period in off_season_false_periods:
        if pd.to_datetime(period['start']) <= date <= pd.to_datetime(period['end']):
            off_season = False
    return pd.Series({'trainingRace': races, 'offSeason': off_season})

def save_processed_data(conn, df, last_week_date):
    """Save processed data to a CSV file and database."""
    os.makedirs("data/processed", exist_ok=True)
    output_columns = [
        'activityId', 'activityName', 'activityType', 'activityTypeGrouped',
        'startTimeLocal', 'Day', 'Week', 'Month', 'duration', 'durationFormatted',
        'distance', 'calories', 'averageHR', 'maxHR', 'minHR', 'averageTemperature',
        'maxTemperature', 'minTemperature', 'waterEstimated', 'elevationGain',
        'elevationLoss', 'maxElevation', 'minElevation', 'averageSpeed', 'maxSpeed',
        'averageRunCadence', 'maxRunCadence', 'totalNumberOfStrokes', 'averageStrokeDistance',
        'averageSwolf', 'averageSwimCadence', 'maxSwimCadence', 'trainingEffect',
        'trainingEffectLabel', 'moderateIntensityMinutes', 'vigorousIntensityMinutes',
        'steps', 'locationName', 'differenceBodyBattery', 'trainingRace', 'offSeason'
    ]
    for col in output_columns:
        if col not in df.columns:
            df[col] = None
    # Create an explicit copy of the DataFrame with the selected columns
    new_df = df[output_columns].copy()
    
    # Save the CSV with list format for trainingRace
    output_file = os.path.join(script_dir, f"data/processed/activities_processed_{last_week_date}.csv")
    new_df.to_csv(output_file, decimal='.', sep=',', index=True)
    
    # Create another DataFrame for SQL storage with joined string format for trainingRace
    sql_df = new_df.copy()
    sql_df.loc[:, 'trainingRace'] = sql_df['trainingRace'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
    
    # Save to SQL database
    if conn is not None:
        # Check if the activities table exists
        table_exists = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='activities'", conn).shape[0] > 0
        
        if table_exists:
            # Check for existing activities to avoid duplicates
            existing_ids = pd.read_sql("SELECT activityId FROM activities", conn)["activityId"].tolist()
            
            # Filter out activities that already exist in the database
            new_activities = sql_df[~sql_df['activityId'].isin(existing_ids)]
            
            if not new_activities.empty:
                new_activities.to_sql("activities", conn, if_exists="append", index=False)
                print(f"\nAdded {len(new_activities)} new activities to the database.")
            else:
                print("\nNo new activities to add to the database.")
        else:
            # Create the table if it doesn't exist
            sql_df.to_sql("activities", conn, if_exists="replace", index=False)
            print(f"\nCreated activities table with {len(sql_df)} initial records.")
            
    print(f"Processed data saved to CSV.")
    return new_df

def main_preprocess(conn, last_week_date, df_weekly_raw):
    """Main preprocessing function."""
    df = load_and_clean_data(df_weekly_raw)
    df = split_biking_musculation_activities_2023(df)
    df = harmonize_zwift_activities(df)
    df = standardize_activity_types(df)
    df[['trainingRace', 'offSeason']] = df.apply(assign_periods, axis=1)
    processed_file = save_processed_data(conn, df, last_week_date)
    return processed_file
