import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sql_queries import (
    get_latest_activity_query,
get_biking_distance_by_timerange_query,    get_weekly_metrics_with_delta_query,
    get_recent_activities_query
)
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

def show(conn, time_range='8_weeks'):
    st.subheader("Biking Metrics")

    # Latest Week Metrics with Delta
    weekly_metrics = pd.read_sql(
        get_weekly_metrics_with_delta_query("cycling"),
        conn,
        params=('cycling',)
    )

    col1, col2 = st.columns(2)
    with col1:
        if not weekly_metrics.empty:
            current_duration = weekly_metrics['current_duration'].iloc[0] or 0
            duration_delta = weekly_metrics['duration_delta'].iloc[0] or 0
            st.metric(
                "Latest Week Effective Effort Time",
                format_duration(current_duration),
                format_duration_delta(duration_delta)
            )
        else:
            st.metric("Latest Week Effective Effort Time", "N/A", "N/A")

    with col2:
        if not weekly_metrics.empty:
            current_distance = weekly_metrics['current_distance'].iloc[0] or 0.0
            distance_delta = weekly_metrics['distance_delta'].iloc[0] or 0.0
            st.metric(
                "Latest Week Distance (km)",
                f"{current_distance:.2f}",
                f"{distance_delta:+.2f}"
            )
        else:
            st.metric("Latest Week Distance (km)", "N/A", "N/A")

    # Time range selector for the Biking Distance Over Time graph
    time_range = st.selectbox(
        "Biking Distance Time Range",
        ["8_weeks", "6_months", "ytd", "race", "all"],
        format_func=lambda x: {
            "8_weeks": "Latest 8 Weeks",
            "6_months": "Last 6 Months",
            "ytd": "Year to Date",
            "race": "Race Period",
            "all": "All Time"
        }[x],
        key="biking_time_range"
    )

    # Fetch biking data
    biking_data = pd.read_sql(
        get_biking_distance_by_timerange_query(time_range),
        conn
    )

    if not biking_data.empty:
        st.subheader("Biking Distance Over Time")
        fig = px.line(
            biking_data,
            x="Week",
            y="total_distance",
            title=f"Biking Distance by Week ({time_range.replace('_', ' ').title()})"
        )
        st.plotly_chart(fig)
    else:
        st.warning(f"No data available for the selected time range: {time_range.replace('_', ' ')}")

    # Recent Activities Section (as a table)
    st.subheader("Last 2 Weeks Biking Activities")
    recent_activities = pd.read_sql(get_recent_activities_query("cycling"), conn)

    if not recent_activities.empty:
        recent_activities['startTimeLocal'] = pd.to_datetime(recent_activities['startTimeLocal'])
        recent_activities['Date'] = recent_activities['startTimeLocal'].dt.strftime('%Y-%m-%d')
        recent_activities['Time'] = recent_activities['startTimeLocal'].dt.strftime('%H:%M')
        recent_activities['Duration'] = recent_activities['duration'].apply(format_duration)
        recent_activities['Distance'] = recent_activities['distance'].round(2)

        display_columns = {
            'Date': 'Date',
            'Time': 'Time',
            'activityName': 'Activity',
            'Distance': 'Distance (km)',
            'Duration': 'Duration',
            'averageHR': 'Avg HR',
            'maxHR': 'Max HR',
            'trainingEffectLabel': 'Training Effect',
            'differenceBodyBattery': 'Body Battery Impact'
        }

        available_columns = {col: display_columns[col] for col in display_columns if col in recent_activities.columns}
        display_df = recent_activities[list(available_columns.keys())].rename(columns=available_columns)
        st.dataframe(display_df, hide_index=True)
    else:
        st.info("No biking activities found in the last 2 weeks.")
