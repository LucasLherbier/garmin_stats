import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import xml.etree.ElementTree as ET

from sql_queries import (
    get_weekly_metrics_with_delta_query,
    get_running_distance_by_timerange_query,
    get_recent_activities_query
)

from actions.display_map import display_gpx_map

import plotly.express as px

def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def format_duration_delta(seconds):
    if seconds is None:
        return "0:00:00"
    sign = "+" if seconds > 0 else ""
    return f"{sign}{format_duration(abs(seconds))}"

def safe_format(value, fmt="{:.2f}", default="N/A"):
    if value is None:
        return default
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return default

def show(conn):
    st.subheader("Running Metrics")

    # Fetch weekly metrics
    weekly_metrics = pd.read_sql(
        get_weekly_metrics_with_delta_query("running"),
        conn,
    )
    if not weekly_metrics.empty:
        metrics = [
            ("Effective Effort Time", weekly_metrics["current_duration"].iloc[0], weekly_metrics["duration_delta"].iloc[0], format_duration, format_duration_delta),
            ("Distance (km)", weekly_metrics["current_distance"].iloc[0], weekly_metrics["distance_delta"].iloc[0], lambda x: safe_format(x, "{:.2f}"), lambda x: safe_format(x, "{:+.2f}")),
            ("Avg HR", weekly_metrics["current_avg_hr"].iloc[0], weekly_metrics["avg_hr_delta"].iloc[0], lambda x: safe_format(x, "{:.0f}"), lambda x: safe_format(x, "{:+.0f}")),
            ("Avg Speed (km/h)", weekly_metrics["current_avg_speed"].iloc[0], weekly_metrics["avg_speed_delta"].iloc[0], lambda x: safe_format(x, "{:.2f}"), lambda x: safe_format(x, "{:+.2f}")),
            ("Elevation Gain (m)", weekly_metrics["current_total_elevation_gain"].iloc[0], weekly_metrics["current_avg_elevation_gain"].iloc[0], lambda x: safe_format(x, "{:.0f}"), lambda x: safe_format(x, "{:.0f}")),
            ("Calories", weekly_metrics["current_total_calories"].iloc[0], weekly_metrics["current_avg_calories"].iloc[0], lambda x: safe_format(x, "{:.0f}"), lambda x: safe_format(x, "{:.0f}")),
            ("Max HR", weekly_metrics["current_max_hr"].iloc[0], None, lambda x: safe_format(x, "{:.0f}"), None),
            ("Avg Cadence", weekly_metrics["current_avg_run_cadence"].iloc[0], weekly_metrics["avg_run_cadence_delta"].iloc[0], lambda x: safe_format(x, "{:.1f}"), lambda x: safe_format(x, "{:+.1f}")),
        ]

        # Display metrics in 4 columns per row
        for i in range(0, len(metrics), 4):
            cols = st.columns(4)
            for j, (name, current, delta, current_fmt, delta_fmt) in enumerate(metrics[i:i+4]):
                with cols[j]:
                    current_display = current_fmt(current)
                    if delta is not None:
                        delta_display = delta_fmt(delta)
                        st.metric(name, current_display, delta_display)
                    else:
                        st.metric(name, current_display)
    else:
        st.warning("No metrics available for the latest week.")

    st.subheader("Running Distance Over Time")
    time_range_metrics = st.selectbox(
        "Running Distance Time Range",
        ["8_weeks", "6_months", "ytd", "all"],
        format_func=lambda x: {"8_weeks": "Latest 8 Weeks", "6_months": "Last 6 Months", "ytd": "Year to Date", "all": "All Time"}[x],
        key="time_range_metrics"
    )

    running_data = pd.read_sql(get_running_distance_by_timerange_query(time_range_metrics), conn)
    if not running_data.empty:
        fig = px.area(running_data, x="Week", y="total_distance", title=f"Running Distance by Week ({time_range_metrics.replace('_', ' ').title()})", markers=True)
        fig.update_traces(textposition='top center', texttemplate='%{y:.2f}')
        st.plotly_chart(fig)
    else:
        st.warning(f"No data available for the selected time range: {time_range_metrics.replace('_', ' ')}")

    st.subheader("Recent Running Activities")


    # Fetch activities data based on the selected time range for activities
    running_table = pd.read_sql(get_recent_activities_query('running', time_range_metrics), conn)
    if not running_table.empty:
        # Pagination
        page_size = 10
        total_pages = (len(running_table) + page_size - 1) // page_size
        page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="page_number")
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = running_table.iloc[start_idx:end_idx]
        # Define column configurations
        column_configuration = {
            "Day": st.column_config.TextColumn("Day", width="small"),
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Activity Name": st.column_config.TextColumn("Activity Name", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Activity ID": st.column_config.TextColumn("Activity ID", width="small"),
            "Distance (km)": st.column_config.NumberColumn("Distance (km)", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="medium"),
            "Calories": st.column_config.NumberColumn("Calories", width="small"),
            "Avg HR": st.column_config.NumberColumn("Avg HR", width="small"),
            "Elevation Gain (m)": st.column_config.NumberColumn("Elevation Gain (m)", width="small"),
            "Avg Speed (km/h)": st.column_config.NumberColumn("Avg Speed (km/h)", width="small"),
            "Avg Cadence": st.column_config.NumberColumn("Avg Cadence", width="small"),
            "Elevation Loss (m)": st.column_config.NumberColumn("Elevation Loss (m)", width="small"),
            "Training Effect": st.column_config.TextColumn("Training Effect", width="small"),
            "Training Effect Label": st.column_config.TextColumn("Training Effect Label", width="medium"),
            "Max HR": st.column_config.NumberColumn("Max HR", width="small"),
            "Min HR": st.column_config.NumberColumn("Min HR", width="small"),
        }

        # Rename columns for display
        display_columns = {
            'Day': 'Day',
            'locationName': 'Location',
            'activityName': 'Activity Name',
            'activityTypeGrouped': 'Type',
            'activityId': 'Activity ID',
            'distance': 'Distance (km)',
            'duration': 'Duration',
            'calories': 'Calories',
            'averageHR': 'Avg HR',
            'elevationGain': 'Elevation Gain (m)',
            'averageSpeed': 'Avg Speed (km/h)',
            'averageRunCadence': 'Avg Cadence',
            'elevationLoss': 'Elevation Loss (m)',
            'trainingEffect': 'Training Effect',
            'trainingEffectLabel': 'Training Effect Label',
            'maxHR': 'Max HR',
            'minHR': 'Min HR',
        }

        available_columns = {col: display_columns[col] for col in display_columns if col in running_table.columns}

        display_df = paginated_df[list(available_columns.keys())].rename(columns=display_columns)

        # Display the dataframe with selection
        selected_rows = st.dataframe(
            display_df,
            column_config=column_configuration,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="running_dataframe"
        )

        # Check if a row is selected
        if selected_rows and len(selected_rows["selection"]["rows"]) > 0:
            selected_row_index = selected_rows["selection"]["rows"][0]
            selected_row_data = paginated_df.iloc[selected_row_index]
            selected_row_id = selected_row_data['activityId']
            st.write(f"Selected Activity ID: {selected_row_id}")

            # Display metrics in 5-per-row format
            st.subheader("Activity Metrics")

            # Create a list of metrics to display
            metrics = [
                ("Distance (km)", f"{selected_row_data.get('distance', 0):.2f}"),
                ("Duration", selected_row_data.get('duration', 0)),
                ("Avg HR", f"{selected_row_data.get('averageHR', 0):.0f}"),
                ("Elevation Gain (m)", f"{selected_row_data.get('elevationGain', 0):.0f}"),
                ("Calories", f"{selected_row_data.get('calories', 0):.0f}"),
                ("Avg Speed (km/h)", f"{selected_row_data.get('averageSpeed', 0):.2f}"),
                ("Avg Cadence", f"{selected_row_data.get('averageRunCadence', 0):.1f}"),
                ("Elevation Loss (m)", f"{selected_row_data.get('elevationLoss', 0):.0f}")
            ]

            # Display metrics in 5 columns per row
            for i in range(0, len(metrics), 4):
                cols = st.columns(4)
                for j, (name, value) in enumerate(metrics[i:i+4]):
                    with cols[j]:
                        st.metric(name, value)

            # Display GPX file if exists
            activity_month = datetime.strptime(str(selected_row_data["startTimeLocal"]), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m")
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            activity_output_dir = os.path.join(project_root, "data", "raw", activity_month, str(selected_row_id))
            gpx_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.gpx")
            if os.path.exists(gpx_file_path):
                display_gpx_map(gpx_file_path) 
                pass
            else:
                st.error("GPX file not found.")

    else:
        st.info("No running activities found.")