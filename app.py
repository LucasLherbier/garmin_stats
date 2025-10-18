import streamlit as st
import pandas as pd
import sqlite3
from datetime import timedelta
from sql_queries import (
    get_metrics_for_period_query,
    get_top_metrics_query,
    get_activity_metrics_query,
    get_custom_metrics_query,
    get_running_distance_by_timerange_query,
)
import tab_swimming
import tab_biking
import tab_running
import tab_race
import plotly.express as px
import os 
import xml.etree.ElementTree as ET
import folium
from streamlit_folium import st_folium

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "activities.db")
conn = sqlite3.connect(db_path)

# --- Helper Functions ---
def format_duration(seconds):
    if seconds is None:
        return "N/A"
    return str(timedelta(seconds=seconds)).split(".")[0]

def display_gpx_map(gpx_file_path):
    # Parse the GPX file
    namespace = {'default': 'http://www.topografix.com/GPX/1/1', 'ns3': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}
    tree = ET.parse(gpx_file_path)
    root = tree.getroot()

    # Extract track points
    track_points = []
    for trk in root.findall('default:trk', namespace):
        for trkseg in trk.findall('default:trkseg', namespace):
            for trkpt in trkseg.findall('default:trkpt', namespace):
                lat = float(trkpt.attrib['lat'])
                lon = float(trkpt.attrib['lon'])
                track_points.append((lat, lon))

    # Create a Streamlit app
    st.title("GPX Track Viewer")

    # Create a map centered around the first track point
    if track_points:
        m = folium.Map(location=track_points[0], zoom_start=15)

        # Add track points to the map
        folium.PolyLine(track_points, color="blue", weight=2.5, opacity=1).add_to(m)

        # Display the map in the Streamlit app
        st_folium(m, width=700, height=500)
    else:
        st.write("No track points found.")

# --- Main App ---
def main():
    # Connect to SQLite DB
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    st.title("Garmin Activity Dashboard")

    # Load data
    #df = pd.read_sql("SELECT * FROM activities", conn)

    # Sidebar filters
    st.sidebar.header("Filters")
    filter_type = st.sidebar.selectbox(
        "Filter by", ["week", "month", "year", "race"]
    )
    filter_value = st.sidebar.text_input(f"Enter {filter_type} (e.g., '2025-09-08' for week)")

    # Apply filter condition for SQL
    filter_condition = f"{filter_type} = '{filter_value}'" if filter_value else "1=1"

    # Sidebar tabs
    st.sidebar.header("Tabs")
    tab = st.sidebar.radio("Select Tab", ["Overview", "Swimming", "Biking", "Running", "Race"])

    if tab == "Overview":
        # --- Section 1: Top Metrics ---
        st.header("Top Metrics")

        display_gpx_map('activity_20553665052.gpx')

        col1, col2 = st.columns(2)
        top_metrics = pd.read_sql(
            get_top_metrics_query(filter_condition),
            conn
        )
        # Handle empty results
        total_duration = top_metrics['total_movingDuration'].iloc[0] if not top_metrics.empty else 0
        total_distance = top_metrics['total_distance'].iloc[0] if not top_metrics.empty else 0.0
        with col1:
            st.metric("Effective Effort Time", format_duration(total_duration))
        with col2:
            st.metric("Total Distance (km)", f"{total_distance:.2f}")

        # --- Section 2: Metrics by Activity Type ---
        st.header("Metrics by Activity Type")
        activity_metrics = pd.read_sql(
            get_activity_metrics_query(filter_condition),
            conn
        )
        # Filter out 'physical_reinforcement'
        activity_metrics = activity_metrics[activity_metrics['activityTypeGrouped'] != 'physical_reinforcement']
        # Display metrics in the same row
        cols = st.columns(len(activity_metrics))
        for i, (_, row) in enumerate(activity_metrics.iterrows()):
            with cols[i]:
                distance = row['total_distance'] if row['total_distance'] is not None else 0.0
                st.metric(f"{row['activityTypeGrouped']} Distance (km)", f"{distance:.2f}")

        # --- Section 3: Graphs ---
        st.header("Distance by Activity Type (Graphs)")
        # Split into 3 side-by-side graphs
        cols = st.columns(3)
        for i, (_, row) in enumerate(activity_metrics.iterrows()):
            with cols[i]:
                fig = px.bar(
                    row.to_frame().T,
                    x="activityTypeGrouped",
                    y="total_distance",
                    title=f"{row['activityTypeGrouped']} Distance",
                )
                st.plotly_chart(fig, use_container_width=True)

        # --- Section 4: Custom Metrics ---
        st.header("Custom Metrics by Activity Type")
        custom_columns = [
            "calories", "averageHR", "maxHR", "minHR", "averageSpeed", "maxSpeed",
            "averageRunCadence", "maxRunCadence", "totalNumberOfStrokes",
            "averageStrokeDistance", "averageSwolf", "averageSwimCadence",
            "maxSwimCadence", "trainingEffect", "moderateIntensityMinutes",
            "vigorousIntensityMinutes", "steps", "elevationGain", "elevationLoss",
            "maxElevation", "minElevation", "waterEstimated", "differenceBodyBattery"
        ]
        custom_column = st.selectbox("Select Column", custom_columns)
        aggregate_function = st.selectbox("Select Aggregate Function", ["SUM", "AVG", "MAX", "MIN"])
        custom_metrics = pd.read_sql(
            get_custom_metrics_query(filter_condition, custom_column, aggregate_function),
            conn
        )
        if not custom_metrics.empty:
            custom_metrics = custom_metrics[custom_metrics['activityTypeGrouped'] != 'physical_reinforcement']
            cols = st.columns(len(custom_metrics))
            for i, (_, row) in enumerate(custom_metrics.iterrows()):
                metric_value = row['metric_value'] if row['metric_value'] is not None else 0.0
                st.metric(
                    f"{row['activityTypeGrouped']} {custom_column} ({aggregate_function})",
                    f"{metric_value:.2f}",
                )
        else:
            st.warning("No data for the selected filter.")

    elif tab == "Swimming":
        tab_swimming.show(conn)
    elif tab == "Biking":
        tab_biking.show(conn)
    elif tab == "Running":
        # Time range selector for running distance chart (main panel)
        tab_running.show(conn)
    elif tab == "Race":
        # Time range selector for running distance chart (main panel)
        tab_race.show(conn)


if __name__ == "__main__":
    main()
