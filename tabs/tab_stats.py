import streamlit as st
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import pandas as pd
from utils import sql_queries as sql

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
        return None, None, None
    row = df.loc[df[metric].idxmax()]
    date = row["startTimeLocal"]
    return row[metric], (date.date() if pd.notna(date) else None), row["activityId"]

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
    is_bike = "Bike" in sport_name
    dist_fmt = "{:.0f} km" if is_bike else "{:.2f} km"

    with cols[0]:
        ui.metric_card(
            f"Longest Day", 
            ut.format_duration(day_val) if metric_name=="duration" else dist_fmt.format(day_val),
            str(day_period),
            icon="☀️"
        )
    with cols[1]:
        ui.metric_card(
            f"Longest Week",
            ut.format_duration_no_days(week_val) if metric_name=="duration" else dist_fmt.format(week_val),
            str(week_period),
            icon="📅"
        )
    with cols[2]:
        ui.metric_card(
            f"Longest Month",
            ut.format_duration_no_days(month_val) if metric_name=="duration" else dist_fmt.format(month_val),
            str(month_period),
            icon="🗓️"
        )
    with cols[3]:
        ui.metric_card(
            f"Longest Year",
            ut.format_duration_no_days(year_val) if metric_name=="duration" else dist_fmt.format(year_val),
            str(year_period),
            icon="🏆"
        )

    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    
    df_list = []
    for key, value in info_dic.items():
        df_key = df[df['activityId'].isin(value)].copy()
        df_key['period'] = key
        df_list.append(df_key)

    df_output = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    return df_output

def sport_bottom_metrics(sport_name, df):
    speed, speed_date, speed_id = longest_single_activity(df, "averageSpeed")
    elev, elev_date, elev_id = longest_single_activity(df, "elevationGain")
    hr, hr_date, hr_id = longest_single_activity(df, "averageHR")
    cal, cal_date, cal_id = longest_single_activity(df, "calories")
    dist_val, dist_date, dist_id = longest_single_activity(df, "distance")
    dur_val, dur_date, dur_id = longest_single_activity(df, "duration")
    
    is_bike = "Bike" in sport_name
    is_run = "Run" in sport_name
    
    st.markdown(f"#### {sport_name} Records")
    
    # Consolidate into 7 columns for a single row
    cols = st.columns(7)

    with cols[0]:
        val = f"{speed:.0f} km/h" if is_bike else f"{speed:.1f} km/h"
        ui.metric_card("Fastest Speed", val if speed is not None else "N/A", str(speed_date) if speed_date else "", icon="⚡")
    
    with cols[1]:
        dist_fmt = "{:.0f} km" if is_bike else "{:.2f} km"
        ui.metric_card("Longest Distance", dist_fmt.format(dist_val) if dist_val is not None else "N/A", str(dist_date) if dist_date else "", icon="📏")

    with cols[2]:
        ui.metric_card("Longest Duration", ut.format_duration_no_days(dur_val) if dur_val is not None else "N/A", str(dur_date) if dur_date else "", icon="⏱️")

    with cols[3]:
        if is_run:
            if speed and speed > 0:
                pace_min = 60 / speed
                p_m, p_s = divmod(int(pace_min * 60), 60)
                pace_str = f"{p_m}:{p_s:02d} /km"
                ui.metric_card("Fastest Pace", pace_str, str(speed_date), icon="🏃‍♂️")
            else:
                ui.metric_card("Fastest Pace", "N/A", "", icon="🏃‍♂️")
        else:
            temp, temp_date, temp_id = longest_single_activity(df, "averageTemperature")
            ui.metric_card("Max Temp", f"{temp:.1f}°C" if temp is not None else "N/A", str(temp_date) if temp_date else "", icon="🌡️")

    with cols[4]:
        ui.metric_card("Max Elevation", f"{elev:.0f} m" if elev is not None else "N/A", str(elev_date) if elev_date else "", icon="⛰️")
    with cols[5]:
        ui.metric_card("Avg HR", f"{hr:.0f} bpm" if hr is not None else "N/A", str(hr_date) if hr_date else "", icon="❤️")
    with cols[6]:
        ui.metric_card("Calories", f"{cal:.0f} cal" if cal is not None else "N/A", str(cal_date) if cal_date else "", icon="🔥")

    st.markdown("<hr>", unsafe_allow_html=True)

def show_activity_detail(activity_id, df_stats, conn):
    activity_row = df_stats[df_stats["activityId"] == activity_id]
    if activity_row.empty:
        return
    
    row = activity_row.iloc[0]
    st.subheader(f"📊 Activity Detail: {row['activityName']}")
    
    m_cols = st.columns(4)
    m_cols[0].metric("Distance", f"{row['distance']:.2f} km")
    m_cols[1].metric("Duration", ut.format_duration_no_days(row['duration']))
    m_cols[2].metric("Avg HR", f"{row['averageHR']:.0f} bpm")
    m_cols[3].metric("Avg Speed", f"{row['averageSpeed']:.1f} km/h")

    # Map & Charts
    activity_month = pd.to_datetime(row["startTimeLocal"]).strftime("%Y-%m")
    selected_row_id = str(activity_id)
    gcs_base_path = f"data/raw/{activity_month}/{selected_row_id}"
    
    from utils.utils_gcp import check_gcs_path_exists, bucket, read_csv_from_gcs
    gpx_path = f"{gcs_base_path}/{selected_row_id}.gpx"
    if check_gcs_path_exists(gpx_path):
        gpx_content = bucket.blob(gpx_path).download_as_bytes()
        display_gpx_map(gpx_content) 

    tcx_path = f"{gcs_base_path}/{selected_row_id}.tcx"
    if check_gcs_path_exists(tcx_path):
        tcx_content = bucket.blob(tcx_path).download_as_bytes()
        df_tcx = parse_tcx_to_dataframe(tcx_content)
        
        st.write("#### Telemetry")
        met1, met2 = st.columns(2)
        y1 = met1.selectbox("Metric 1", ["HeartRate", "Cadence", "Watts", "Altitude"], index=0, key=f"stats_y1_{activity_id}")
        y2 = met2.selectbox("Metric 2", ["HeartRate", "Cadence", "Watts", "Altitude"], index=3, key=f"stats_y2_{activity_id}")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_tcx["Time"], y=df_tcx[y1], name=y1, line=dict(color="#ef4444")), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_tcx["Time"], y=df_tcx[y2], name=y2, line=dict(color="#10b981")), secondary_y=True)
        fig.update_layout(height=400, template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

def show(conn):
    df_stats = conn(sql.activities_stats())

    if df_stats.empty or "startTimeLocal" not in df_stats.columns:
        st.warning("⚠️ Could not load activity data. Please check your BigQuery connection and credentials.")
        return

    df_stats["startTimeLocal"] = pd.to_datetime(df_stats["startTimeLocal"], errors="coerce")

    sports = {
        "🏃‍♂️ Run": df_stats[df_stats["activityTypeGrouped"] == "running"],
        "🚴‍♂️ Bike": df_stats[df_stats["activityTypeGrouped"] == "cycling"],
        "🏊‍♂️ Swim": df_stats[df_stats["activityTypeGrouped"] == "swimming"],
    }
   
    st.markdown("---")
    st.header("🔥 Best Metrics")

    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            sport_bottom_metrics(sport_name, df_sport)


    st.markdown("---")
    st.title("🏅 Volume Records")
    st.markdown("My all-time best performances across different activities.")
    
    if "selected_activity_id" not in st.session_state:
        st.session_state.selected_activity_id = None


    # --- Metric Selector ---
    st.write("### Choose Metric")
    if 'metric_choice' not in st.session_state:
        st.session_state.metric_choice = "duration"
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("⏱ Duration", width="stretch", type="primary" if st.session_state.metric_choice == "duration" else "secondary"):
            st.session_state.metric_choice = "duration"
            st.rerun()
    with col2:
        if st.button("📏 Distance", width="stretch", type="primary" if st.session_state.metric_choice == "distance" else "secondary"):
            st.session_state.metric_choice = "distance"
            st.rerun()


    summary_list = []
    for sport_name, df_sport in sports.items():
        if not df_sport.empty:
            df_subset = sport_main_metrics_row(sport_name, df_sport, st.session_state.metric_choice)
            summary_list.append(df_subset)
    summary_df = pd.concat(summary_list, ignore_index=True) if summary_list else pd.DataFrame()

    # Display selected record detail
    if st.session_state.selected_activity_id:
        with st.container():
            st.markdown("---")
            show_activity_detail(st.session_state.selected_activity_id, df_stats, conn)
            if st.button("Close Detail"):
                st.session_state.selected_activity_id = None
                st.rerun()
        st.markdown("---")

    if not summary_df.empty:
        # Sort and table display logic
        sport_label_map = {"running": "Run", "cycling": "Bike", "swimming": "Swim"}
        # Ensure we don't have duplicates or handle column selection better
        summary_df["Label"] = (
            "Longest " + summary_df["period"].str.title() +
            " " + summary_df["activityTypeGrouped"].map(lambda x: sport_label_map.get(x, x.capitalize()))
        )
        
        # We don't need a copy, we can modify summary_df directly as it's not used elsewhere
        summary_df["duration"] = summary_df["duration"].apply(ut.format_duration_no_days)
        df_display = summary_df

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

        sorted_stats = df_display.sort_values("Label", ascending=True)
        paginated_df, selected_page_row, selected_row = ut.paginated_table(
            df=sorted_stats,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=5,
            session_key="summary_stats"
        )
        
        if selected_row is not None:
            # Update detail from table selection
            table_act_id = sorted_stats.iloc[selected_row]['activityId']
            if table_act_id != st.session_state.selected_activity_id:
                st.session_state.selected_activity_id = table_act_id
                st.rerun()