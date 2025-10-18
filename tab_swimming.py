import streamlit as st
import pandas as pd
from datetime import timedelta
from sql_queries import get_latest_activity_query, get_metrics_for_period_query
import plotly.express as px

def format_duration(seconds):
    if seconds is None:
        return "N/A"
    return str(timedelta(seconds=seconds)).split(".")[0]

def show(conn):
    st.subheader("Swimming Metrics")

    # Latest Week Metrics
    latest_week_metrics = pd.read_sql(
        get_metrics_for_period_query("swimming", "Week", "2025-09-08"),
        conn
    )
    if not latest_week_metrics.empty:
        week_duration = latest_week_metrics['total_movingDuration'].iloc[0]
        week_distance = latest_week_metrics['total_distance'].iloc[0]
    else:
        week_duration = None
        week_distance = 0.0

    if week_duration is not None:
        st.metric("Latest Week Effective Effort Time", format_duration(week_duration))
    if week_distance is not None:
        st.metric("Latest Week Distance (km)", f"{week_distance:.2f}")

    # Latest Month Metrics
    latest_month_metrics = pd.read_sql(
        get_metrics_for_period_query("swimming", "Month", "2025-09-01"),
        conn
    )
    if not latest_month_metrics.empty:
        month_duration = latest_month_metrics['total_movingDuration'].iloc[0]
        month_distance = latest_month_metrics['total_distance'].iloc[0]
    else:
        month_duration = None
        month_distance = 0.0

    if month_duration is not None:
        st.metric("Latest Month Effective Effort Time", format_duration(month_duration))
    if month_distance is not None:
        st.metric("Latest Month Distance (km)", f"{month_distance:.2f}")

    # Graph
    st.subheader("Swimming Distance Over Time")
    swimming_data = pd.read_sql(
        "SELECT Week, SUM(distance) AS distance FROM activities WHERE activityTypeGrouped = 'swimming' GROUP BY Week",
        conn
    )
    fig = px.line(swimming_data, x="Week", y="distance", title="Swimming Distance by Week")
    st.plotly_chart(fig)

    # Latest Activity
    st.subheader("Latest Swimming Activity")
    latest_activity = pd.read_sql(get_latest_activity_query("swimming"), conn)
    st.dataframe(latest_activity)