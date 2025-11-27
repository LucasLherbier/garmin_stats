# actions/parse_tcx.py
import pandas as pd
import xml.etree.ElementTree as ET
import numpy as np

def parse_tcx_to_dataframe(tcx_file_path):
    tree = ET.parse(tcx_file_path)
    root = tree.getroot()

    ns = {
        'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
    }

    # Liste pour stocker les données de chaque Trackpoint
    times = []
    latitudes = []
    longitudes = []
    altitudes = []
    distances = []
    heart_rates = []
    speeds = []
    cadences = []
    watts = []

    # Liste pour stocker les données des Laps (splits)
    laps = []

    # Récupérer les Laps (splits)
    for lap in root.findall('.//ns:Lap', ns):
        lap_data = {}

        # Récupérer StartTime
        start_time_elem = lap.find('ns:StartTime', ns)
        lap_data['StartTime'] = start_time_elem.text if start_time_elem is not None else None

        # Récupérer TotalTimeSeconds
        total_time_elem = lap.find('ns:TotalTimeSeconds', ns)
        lap_data['TotalTimeSeconds'] = float(total_time_elem.text) if total_time_elem is not None else np.nan

        # Récupérer DistanceMeters
        distance_elem = lap.find('ns:DistanceMeters', ns)
        lap_data['DistanceMeters'] = float(distance_elem.text) if distance_elem is not None else np.nan

        # Récupérer AverageHeartRateBpm
        avg_hr_elem = lap.find('.//ns:AverageHeartRateBpm/ns:Value', ns)
        lap_data['AvgHeartRate'] = int(avg_hr_elem.text) if avg_hr_elem is not None else np.nan

        # Récupérer MaximumHeartRateBpm
        max_hr_elem = lap.find('.//ns:MaximumHeartRateBpm/ns:Value', ns)
        lap_data['MaxHeartRate'] = int(max_hr_elem.text) if max_hr_elem is not None else np.nan

        laps.append(lap_data)

    # Récupérer les Trackpoints
    for trackpoint in root.findall('.//ns:Trackpoint', ns):
        # Récupérer Time
        time_elem = trackpoint.find('ns:Time', ns)
        times.append(time_elem.text if time_elem is not None else None)

        # Récupérer Position (Latitude et Longitude)
        position_elem = trackpoint.find('ns:Position', ns)
        if position_elem is not None:
            lat_elem = position_elem.find('ns:LatitudeDegrees', ns)
            lon_elem = position_elem.find('ns:LongitudeDegrees', ns)
            latitudes.append(float(lat_elem.text) if lat_elem is not None else np.nan)
            longitudes.append(float(lon_elem.text) if lon_elem is not None else np.nan)
        else:
            latitudes.append(np.nan)
            longitudes.append(np.nan)

        # Récupérer AltitudeMeters
        altitude_elem = trackpoint.find('ns:AltitudeMeters', ns)
        altitudes.append(float(altitude_elem.text) if altitude_elem is not None else np.nan)

        # Récupérer DistanceMeters
        distance_elem = trackpoint.find('ns:DistanceMeters', ns)
        distances.append(float(distance_elem.text) if distance_elem is not None else np.nan)

        # Récupérer HeartRateBpm
        heart_rate_elem = trackpoint.find('.//ns:HeartRateBpm/ns:Value', ns)
        heart_rates.append(int(heart_rate_elem.text) if heart_rate_elem is not None else np.nan)

        # Récupérer les Extensions (Speed, Cadence, Watts)
        extensions_elem = trackpoint.find('.//ns3:TPX', ns)
        if extensions_elem is not None:
            speed_elem = extensions_elem.find('ns3:Speed', ns)
            speeds.append(float(speed_elem.text) if speed_elem is not None else np.nan)

            cadence_elem = extensions_elem.find('ns3:RunCadence', ns)
            cadences.append(int(cadence_elem.text) if cadence_elem is not None else np.nan)

            watt_elem = extensions_elem.find('ns3:Watts', ns)
            watts.append(int(watt_elem.text) if watt_elem is not None else np.nan)
        else:
            speeds.append(np.nan)
            cadences.append(np.nan)
            watts.append(np.nan)

    # Créer un DataFrame pour les Trackpoints
    df = pd.DataFrame({
        'Time': times,
        'Latitude': latitudes,
        'Longitude': longitudes,
        'Altitude': altitudes,
        'Distance': distances,
        'HeartRate': heart_rates,
        'Speed': speeds,
        'Cadence': cadences,
        'Watts': watts
    })

    # Convertir le temps en datetime
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')

    # Remplacer les vitesses nulles par NaN
    df.loc[df['Speed'] == 0, 'Speed'] = np.nan
    df['Pace'] = pd.to_timedelta(
        1000 / df['Speed'],
        unit='s',
        errors='coerce'  # This will set invalid values (e.g., division by zero) to NaT
    ) 

    df['Pace_seconds'] = df['Pace'].dt.total_seconds()
    # Create a new column for formatted Pace (mm:ss or "No Data")
    df['Pace_formatted'] = df['Pace'].apply(
        lambda x: f"{int(x.total_seconds() // 60):02d}:{int(x.total_seconds() % 60):02d}"
                if pd.notna(x) else "No Data"
    )
    return df


def parse_swimming_csv(csv_file_path):
    """
    Parse a swimming CSV export into a DataFrame with useful numeric and time columns.
    """
    # Read CSV
    df = pd.read_csv(csv_file_path, dtype=str)  # Read all as string to avoid mis-parsing

    # Convert numeric columns
    numeric_cols = ['Lengths','Distance','Avg SWOLF','Avg HR','Max HR','Total Strokes','Avg Strokes','Calories']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace('--', np.nan), errors='coerce')

    # Parse Time column (hh:mm:ss.xxx or mm:ss.xxx)
    def parse_time_str(t):
        try:
            if pd.isna(t):
                return pd.NaT
            parts = str(t).split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return pd.Timedelta(minutes=minutes, seconds=seconds)
            elif len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return pd.Timedelta(hours=hours, minutes=minutes, seconds=seconds)
            else:
                return pd.NaT
        except:
            return pd.NaT

    if 'Time' in df.columns:
        df['TimeDelta'] = df['Time'].apply(parse_time_str)
        df['Time_seconds'] = df['TimeDelta'].dt.total_seconds()

    # Parse Avg Pace and Best Pace (mm:ss)
    def parse_pace_str(p):
        try:
            if pd.isna(p) or str(p).strip() == '--':
                return np.nan
            parts = str(p).split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            return np.nan
        except:
            return np.nan

    for col in ['Avg Pace','Best Pace']:
        if col in df.columns:
            df[col + '_seconds'] = df[col].apply(parse_pace_str)

    # Fill missing numeric values with 0 where appropriate
    fill_zero_cols = ['Lengths', 'Distance', 'Total Strokes', 'Avg Strokes', 'Calories']
    for col in fill_zero_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Optional: create a "Rest" flag
    df['IsRest'] = df['Split'].astype(str).str.upper().str.contains("REST")

    return df