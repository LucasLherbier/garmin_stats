import streamlit as st
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import pandas as pd
import sql_queries as sql

from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.display_pace_bar_plot import plot_running_bar
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut
from actions import utils_ui as ui

def duration_by_period(df, period):
    if df.empty:
        return 0, "N/A"
    agg = df.groupby(period, as_index=False)["duration"].sum()
    if agg.empty:
        return 0, "N/A"
    r = agg.loc[agg["duration"].idxmax()]
    return r["duration"], r[period]

def longest_period_metric(df, metric, period):
    if df.empty:
        return 0, "N/A", []
    agg = df.groupby(period, as_index=False)[metric].sum()
    if agg.empty:
        return 0, "N/A", []
    row = agg.loc[agg[metric].idxmax()]
    matching_rows_df = df[df[period] == row[period]]
    matching_activity_ids = matching_rows_df['activityId'].tolist()
    return row[metric], row[period], matching_activity_ids

def longest_single_activity(df, metric):
    if df.empty or df[metric].dropna().empty:
        return None, None
    row = df.loc[df[metric].idxmax()]
    date = row["startTimeLocal"]
    return row[metric], (date.date() if pd.notna(date) else None)

def sport_main_metrics_row(sport_name, df, metric_name):
    st.markdown(f"### {sport_name}")

    # 1-day
    info_dic = {"Day":[], "Week":[], "Month":[], "Year":[]}
    day_val, day_period, info_dic['Day'] =  longest_period_metric(df, metric_name, "Day")
    # 2-week
    week_val, week_period, info_dic['Week'] =  longest_period_metric(df, metric_name, "Week")
    # 3-month
    month_val, month_period, _ =  longest_period_metric(df, metric_name, "Month")
    # 4-year
    year_val, year_period, _ =  longest_period_metric(df, metric_name, "Year")

    cols = st.columns(4)

    with cols[0]:
        ui.metric_card(
            f"Longest Day", 
            ut.format_duration(day_val) if metric_name=="duration" else f"{day_val:.2f} km",
            str(day_period),
            icon="☀️"
        )
    with cols[1]:
        ui.metric_card(
            f"Longest Week",
            ut.format_duration_no_days(week_val) if metric_name=="duration" else f"{week_val:.2f} km",
            str(week_period),
            icon="📅"
        )
    with cols[2]:
        ui.metric_card(
            f"Longest Month",
            ut.format_duration_no_days(month_val) if metric_name=="duration" else f"{month_val:.2f} km",
            str(month_period),
            icon="🗓️"
        )
    with cols[3]:
        ui.metric_card(
            f"Longest Year",
            ut.format_duration_no_days(year_val) if metric_name=="duration" else f"{year_val:.2f} km",
            str(year_period),
            icon="🏆"
        )

    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    
    df_output, df_key = pd.DataFrame(), pd.DataFrame()
    for key, value in info_dic.items():
        df_key = df[df['activityId'].isin(value)]
        df_key['period'] = key
        df_output = pd.concat([df_output, df_key], ignore_index=True)
    return df_output

def sport_bottom_metrics(sport_name, df):
    speed, speed_date = longest_single_activity(df, "averageSpeed")
    elev, elev_date = longest_single_activity(df, "elevationGain")
    hr, hr_date = longest_single_activity(df, "averageHR")
    cal, cal_date = longest_single_activity(df, "calories")
    temp, temp_date = longest_single_activity(df, "averageTemperature")

    logo, sport = sport_name.split(' ')
    
    st.markdown(f"#### {sport_name} Records")
    cols = st.columns(5)

    with cols[0]:
        ui.metric_card("Fastest Speed", f"{speed:.1f} km/h" if speed is not None else "N/A", str(speed_date) if speed_date else "", icon="⚡")
    with cols[1]:
        ui.metric_card("Max Elevation", f"{elev:.0f} m" if elev is not None else "N/A", str(elev_date) if elev_date else "", icon="⛰️")
    with cols[2]:
        ui.metric_card("Max Avg HR", f"{hr:.0f} bpm" if hr is not None else "N/A", str(hr_date) if hr_date else "", icon="❤️")
    with cols[3]:
        ui.metric_card("Max Calories", f"{cal:.0f} kcal" if cal is not None else "N/A", str(cal_date) if cal_date else "", icon="🔥")
    with cols[4]:
        ui.metric_card("Max Avg Temp", f"{temp:.1f}°C" if temp is not None else "N/A", str(temp_date) if temp_date else "", icon="🌡️")

    st.markdown("<hr>", unsafe_allow_html=True)

def show(conn):
    st.title("🏅 Training Records")
    st.markdown("My all-time best performances across different activities.")

    df_stats = conn(sql.activities_stats())
    df_stats["startTimeLocal"] = pd.to_datetime(df_stats["startTimeLocal"], errors="coerce")

    sports = {
        "🏃‍♂️ Run": df_stats[df_stats["activityTypeGrouped"] == "running"],
        "🚴‍♂️ Bike": df_stats[df_stats["activityTypeGrouped"] == "cycling"],
        "🏊‍♂️ Swim": df_stats[df_stats["activityTypeGrouped"] == "swimming"],
    }

    # --- Metric Selector ---
    st.write("### Choose Metric")
    if 'metric_choice' not in st.session_state:
        st.session_state.metric_choice = "duration"
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⏱ Duration", use_container_width=True, type="primary" if st.session_state.metric_choice == "duration" else "secondary"):
            st.session_state.metric_choice = "duration"
            st.rerun()
    with col2:
        if st.button("📏 Distance", use_container_width=True, type="primary" if st.session_state.metric_choice == "distance" else "secondary"):
            st.session_state.metric_choice = "distance"
            st.rerun()

    st.markdown("---")

    summary_df = pd.DataFrame()
    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            df_subset = sport_main_metrics_row(sport_name, df_sport, st.session_state.metric_choice)
            summary_df = pd.concat([summary_df, df_subset], ignore_index=True)

    if not summary_df.empty:
        sport_label_map = {"running": "Run", "cycling": "Bike", "swimming": "Swim"}
        summary_df["Label"] = (
            "Longest " + summary_df["period"].str.title() +
            " " + summary_df["activityTypeGrouped"].map(lambda x: sport_label_map.get(x, x.capitalize()))
        )
        summary_df["duration"] = summary_df["duration"].apply(ut.format_duration_no_days)

        column_configuration = {
            "Label": st.column_config.TextColumn("Label", width="medium"),
            "activityId": st.column_config.TextColumn("Activity ID", width="small"),
            "activityName": st.column_config.TextColumn("Activity Name", width="medium"),
            "locationName": st.column_config.TextColumn("Location", width="medium"),
            "distance": st.column_config.NumberColumn("Distance (km)", format="%.2f"),
            "duration": st.column_config.TextColumn("Duration"),
            "averageHR": st.column_config.NumberColumn("Avg HR"),
            "averageSpeed": st.column_config.NumberColumn("Avg Speed (km/h)", format="%.1f"),
            "elevationGain": st.column_config.NumberColumn("Elevation Gain (m)"),
            "calories": st.column_config.NumberColumn("Calories"),
        }

        display_columns = {
            "Label":"Label",
            "Day": "Day",
            "distance": "Distance (km)",
            "duration": "Duration",
            "averageHR": "Avg HR",
            "averageSpeed": "Avg Speed (km/h)",
            "elevationGain": "Elevation Gain (m)",
            "calories": "Calories",
            "activityName": "Name",
            "locationName": "Location",
        }

        paginated_df, selected_row = ut.paginated_table(
            df=summary_df.sort_values("Label", ascending=True),
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=5,
            session_key="summary_stats"
        )

    st.markdown("---")
    st.header("🔥 Best Random Metrics")

    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            sport_bottom_metrics(sport_name, df_sport)
