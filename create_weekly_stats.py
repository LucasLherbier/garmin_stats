import pandas as pd

def aggregate_activities(df, granularity='weekly'):
    """
    df: DataFrame with all activities (daily granularity)
    granularity: 'weekly', 'monthly', or 'yearly'
    Returns: Aggregated DataFrame with the specified granularity
    """

    # Ensure 'startTimeLocal' is a datetime column
    df['startTimeLocal'] = pd.to_datetime(df['startTimeLocal'])

    # Group by activity type and time period
    if granularity == 'weekly':
        # Extract year and week number
        df['Week'] = df['startTimeLocal'].dt.to_period('W').astype(str)
        groupby_col = 'Week'
    elif granularity == 'monthly':
        # Extract year and month
        df['Month'] = df['startTimeLocal'].dt.to_period('M').astype(str)
        groupby_col = 'Month'
    elif granularity == 'yearly':
        # Extract year
        df['Year'] = df['startTimeLocal'].dt.to_period('Y').astype(str)
        groupby_col = 'Year'
    else:
        raise ValueError("granularity must be 'weekly', 'monthly', or 'yearly'")

    # Group by time period and activity type
    grouped = df.groupby([groupby_col, 'activityType']).agg({
        # Sum
        'duration': 'sum',
        'elapsedDuration': 'sum',
        'movingDuration': 'sum',
        'distance': 'sum',
        'calories': 'sum',
        'waterEstimated': 'sum',
        'elevationGain': 'sum',
        'elevationLoss': 'sum',
        'moderateIntensityMinutes': 'sum',
        'vigorousIntensityMinutes': 'sum',
        'steps': 'sum',
        'differenceBodyBattery': 'sum',
        'totalNumberOfStrokes': 'sum',
        # Mean
        'averageHR': 'mean',
        'averageTemperature': 'mean',
        'averageSpeed': 'mean',
        'averageRunCadence': 'mean',
        'averageStrokeDistance': 'mean',
        'averageSwimCadence': 'mean',
        # Max
        'maxHR': 'max',
        'maxTemperature': 'max',
        'maxElevation': 'max',
        'maxSpeed': 'max',
        'maxRunCadence': 'max',
        'maxSwimCadence': 'max',
        # Min
        'minHR': 'min',
        'minTemperature': 'min',
        'minElevation': 'min',
    }).reset_index()

    # Rename columns for clarity
    grouped = grouped.rename(columns={
        groupby_col: 'TimePeriod',
        'activityType': 'activityTypeGrouped'
    })

    # Reorder columns for readability
    cols = [
        'TimePeriod', 'activityTypeGrouped',
        'duration', 'elapsedDuration', 'movingDuration', 'distance', 'calories',
        'waterEstimated', 'elevationGain', 'elevationLoss', 'moderateIntensityMinutes',
        'vigorousIntensityMinutes', 'steps', 'differenceBodyBattery', 'totalNumberOfStrokes',
        'averageHR', 'averageTemperature', 'averageSpeed', 'averageRunCadence',
        'averageStrokeDistance', 'averageSwimCadence',
        'maxHR', 'maxTemperature', 'maxElevation', 'maxSpeed', 'maxRunCadence', 'maxSwimCadence',
        'minHR', 'minTemperature', 'minElevation'
    ]
    grouped = grouped[cols]

    return grouped

# Assuming df is your daily activity DataFrame
def main(df):
        weekly_df = aggregate_activities(df, granularity='weekly')
        monthly_df = aggregate_activities(df, granularity='monthly')
        yearly_df = aggregate_activities(df, granularity='yearly')
        print("Weekly Aggregated Data:")
        print(weekly_df.head())