import streamlit as st
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import pandas as pd
import sql_queries as sql

from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.display_pace_bar_plot import plot_running_bar  # This may be replaced with a cycling pace plot if needed
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut


def duration_by_period(df, period):
    agg = df.groupby(period, as_index=False)["duration"].sum()
    r = agg.loc[agg["duration"].idxmax()]
    return r["duration"], r[period]


def longest_period_metric(df, metric, period):
    """Return max total metric for a period, period value, and specified row columns."""
    agg = df.groupby(period, as_index=False)[metric].sum()
    row = agg.loc[agg[metric].idxmax()]
    matching_rows_df = df[df[period] == row[period]]
    matching_activity_ids = matching_rows_df['activityId'].tolist()
    return row[metric], row[period], matching_activity_ids


def longest_single_activity(df, metric):
    """Return max(metric) and its date, safely."""
    if df.empty or df[metric].dropna().empty:
        return None, None

    row = df.loc[df[metric].idxmax()]
    date = row["startTimeLocal"]
    return row[metric], (date.date() if pd.notna(date) else None)

def sport_main_metrics_row(sport_name, df, metric_name):
    st.subheader(sport_name)

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

    cols[0].metric(
        f"Longest Day {metric_name}",        
        ut.format_duration(day_val) if metric_name=="duration" else f"{day_val:.2f} km",
        str(day_period),
    )
    cols[1].metric(
        f"Longest Week {metric_name}",
        ut.format_duration_no_days(week_val) if metric_name=="duration" else f"{week_val:.2f} km",
        week_period,
    )
    cols[2].metric(
        f"Longest Month {metric_name}",
        ut.format_duration_no_days(month_val) if metric_name=="duration" else f"{month_val:.2f} km",
        month_period,
    )
    cols[3].metric(
        f"Longest Year {metric_name}",
        ut.format_duration_no_days(year_val) if metric_name=="duration" else f"{year_val:.2f} km",
        year_period,
    )

    st.markdown("---")
    df_output, df_key = pd.DataFrame(), pd.DataFrame()
    for key, value in info_dic.items():
        df_key = df[df['activityId'].isin(value)]
        df_key['period'] = key
        df_output = pd.concat([df_output, df_key], ignore_index=True)
    # Return rows for final summary table
    return df_output


def sport_bottom_metrics(sport_name, df):
    # Compute metrics
    speed, speed_date = longest_single_activity(df, "averageSpeed")
    elev, elev_date = longest_single_activity(df, "elevationGain")
    hr, hr_date = longest_single_activity(df, "averageHR")
    cal, cal_date = longest_single_activity(df, "calories")
    temp, temp_date = longest_single_activity(df, "averageTemperature")

    # Create 6 columns: first for title, next 5 for metrics
    cols = st.columns(6)

    # Display the title in the first column, centered vertically and horizontally
    logo, sport = sport_name.split(' ')
    title_html = f"""
    <div style="
        display: flex;
        flex-direction: column;     /* stack logo and text vertically */
        justify-content: center;    /* vertical centering */
        align-items: center;        /* horizontal centering */
        height: 100%;               /* take full column height */
        font-weight: bold;
        text-align: center;
    ">  
        <span style="font-size: 50px; line-height: 1;">{logo}</span><br>       
        <span style="font-size: 18px; line-height: 1;">{sport}</span>
    </div>
    """
        
    cols[0].markdown(title_html, unsafe_allow_html=True)

    # Display metrics in remaining columns
    cols[1].metric("Fastest Speed", f"{speed:.1f} km/h", str(speed_date))
    cols[2].metric("Max Elevation", f"{elev:.0f} m", str(elev_date))
    cols[3].metric("Max Avg HR", f"{hr:.0f}", str(hr_date))
    cols[4].metric("Max Calories", f"{cal:.0f}", str(cal_date))
    cols[5].metric(
        "Max Avg Temp",
        f"{temp:.1f}°C" if temp is not None else "N/A",
        str(temp_date) if temp_date is not None else ""
    )

    st.markdown("---")


def show(conn):
    st.title("🏅 Training Records")

    df_stats = pd.read_sql(sql.activities_stats(), conn)
    df_stats["startTimeLocal"] = pd.to_datetime(df_stats["startTimeLocal"], errors="coerce")

    # Sport filtering
    sports = {
        "🏃 Running": df_stats[df_stats["activityTypeGrouped"] == "running"],
        "🚴 Cycling": df_stats[df_stats["activityTypeGrouped"] == "cycling"],
        "🏊 Swimming": df_stats[df_stats["activityTypeGrouped"] == "swimming"],
    }

    # -----------------------------
    #  TOP BUTTONS
    # -----------------------------
    st.subheader("Metrics Displayed")

    # Initialisation de la session state si nécessaire
    if 'metric_choice' not in st.session_state:
        st.session_state.metric_choice = "duration"
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(
            "⏱ Duration",
            use_container_width=True,
            type="primary" if st.session_state.get("metric_choice") == "duration" else "secondary"
        ):
            st.session_state.metric_choice = "duration"
            st.rerun()

    with col2:
        if st.button(
            "📏 Distance",
            use_container_width=True,
            type="primary" if st.session_state.get("metric_choice") == "distance" else "secondary"
        ):
            st.session_state.metric_choice = "distance"
            st.rerun()
    # -----------------------------
    #  PER SPORT MAIN METRICS
    # -----------------------------
    summary_df = pd.DataFrame()

    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            df_subset = sport_main_metrics_row(
                sport_name, df_sport, st.session_state.metric_choice
            )
            # Optionally, you can add metric and period as columns to the subset
            summary_df = pd.concat([summary_df, df_subset], ignore_index=True)


    if not summary_df.empty:
        summary_df["Label"] = (
            "Longest " + summary_df["period"].str.title() +
            " " + summary_df["activityTypeGrouped"].str.replace("🏃 |🚴 |🏊 ", "", regex=True)
        )
        summary_df["duration"] = summary_df["duration"].apply(ut.format_duration_no_days)

        # Define column configurations
        column_configuration = {
            "Label": st.column_config.TextColumn("Label", width="medium"),
            "activityId": st.column_config.TextColumn("Activity ID", width="small"),
            "activityName": st.column_config.TextColumn("Activity Name", width="medium"),
            "locationName": st.column_config.TextColumn("Location", width="medium"),
            "trainingRace": st.column_config.TextColumn("Training/Race", width="small"),
            "Day": st.column_config.TextColumn("Day", width="small"),
            "Week": st.column_config.TextColumn("Week", width="small"),
            "Month": st.column_config.TextColumn("Month", width="small"),
            "Year": st.column_config.TextColumn("Year", width="small"),
            "distance": st.column_config.NumberColumn("Distance (km)", width="small"),
            "duration": st.column_config.TextColumn("Duration", width="small", ),
            "averageHR": st.column_config.NumberColumn("Avg HR", width="small"),
            "averageSpeed": st.column_config.NumberColumn("Avg Speed (km/h)", width="small"),
            "elevationGain": st.column_config.NumberColumn("Elevation Gain (m)", width="small"),
            "calories": st.column_config.NumberColumn("Calories", width="small"),
            "averageTemperature": st.column_config.NumberColumn("Avg Temperature", width="small"),
            "waterEstimated": st.column_config.NumberColumn("Water Estimated", width="small"),
            "activityTypeGrouped": st.column_config.TextColumn("Type", width="small"),
        }

        # Map DataFrame columns to display names
        display_columns = {
            "Label":"Label",
            "Day": "Day",
            "distance": "Distance (km)",
            "duration": "Duration",
            "averageHR": "Avg HR",
            "averageSpeed": "Avg Speed (km/h)",
            "elevationGain": "Elevation Gain (m)",
            "calories": "Calories",
            "averageTemperature": "Avg Temperature",
            "waterEstimated": "Water Estimated",
            "activityId": "Activity ID",
            "locationName": "Location",
            "activityTypeGrouped": "Type",
            "trainingRace": "Training/Race",

        }

        # Display paginated table
        paginated_df, selected_row = ut.paginated_table(
            df=summary_df.sort_values("Label", ascending=True),
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="summary"
        )

    st.markdown("---")

    # -----------------------------
    # Bottom Metrics by Sport
    # -----------------------------
    st.header("🔥 Best Random Metrics")

    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            sport_bottom_metrics(sport_name, df_sport)