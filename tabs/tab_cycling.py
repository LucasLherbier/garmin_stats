import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import numpy as np
from utils import sql_queries as sql

from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_tcx_to_dataframe
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut
from actions import utils_ui as ui
from utils.utils_gcp import check_gcs_path_exists, read_csv_from_gcs, bucket


def show(conn):
    st.title("🚴‍♂️ Bike Analytics")
    st.markdown("Detailed insights into my bike performance and history activities")

    # Fetch race metrics for cycling
    race_metrics = conn(sql.get_volume_metrics_query("cycling"))

    if not race_metrics.empty:
        st.write("### Volume Summary")
        dict_columns = {"last_1":"Last Week", "last_4":"Last 4 Weeks", "last_12":"Last 12 Weeks", "last_18":"Last 18 Weeks", "last_all": "YTD"}
        
        if 'bike_volume_range' not in st.session_state:
            st.session_state.bike_volume_range = "last_1"

        # Selection buttons
        v_cols = st.columns(len(dict_columns))
        for i, (key, title) in enumerate(dict_columns.items()):
            if v_cols[i].button(title, key=f"v_bike_{key}", width="stretch", 
                                type="primary" if st.session_state.bike_volume_range == key else "secondary"):
                st.session_state.bike_volume_range = key
                st.rerun()

        selected_key = st.session_state.bike_volume_range
        row = race_metrics[race_metrics['name'] == selected_key]
        if not row.empty:
            cols = st.columns(4)
            avg_hr = row['averageHR'].fillna(0).iloc[0]
            with cols[0]: ui.metric_card("Total Distance", f"{row['distance_total'].iloc[0] or 0:.1f} km", icon="📏")
            with cols[1]: ui.metric_card("Total Duration", ut.format_duration_no_days(row['duration_total'].iloc[0]), icon="⏱️")
            with cols[2]: ui.metric_card("Trainings", f"{row['nb_trainings'].iloc[0] or 0:.0f}", icon="🚴‍♂️")
            with cols[3]: ui.metric_card("Avg HR", f"{avg_hr:.0f} bpm", icon="❤️")

    st.markdown("---")

    st.write("### Performance Trends")
    if 'time_range_metrics' not in st.session_state:
        st.session_state.time_range_metrics = "4_units"

    # Selection buttons
    tr_cols = st.columns(4)
    ranges = [("4 Weeks", "4_units"), ("6 Weeks", "6_units"), ("YTD", "ytd"), ("All Time", "all")]
    for i, (label, val) in enumerate(ranges):
        if tr_cols[i].button(label, key=f"tr_btn_{val}", width="stretch", type="primary" if st.session_state.time_range_metrics == val else "secondary"):
            st.session_state.time_range_metrics = val
            st.rerun()

    cycling_data = conn(sql.get_weekly_sport_query('cycling', st.session_state.time_range_metrics))
    ut.plot_week_area(cycling_data, "total_distance", "Distance (km)", "Cycling", st.session_state.time_range_metrics)

    st.markdown("---")
    st.write("### 📜 Recent Activities")

    cycling_table = conn(sql.get_recent_activities_query('cycling', st.session_state.time_range_metrics))

    if not cycling_table.empty:
        # Convert Day to YYYY-MM-DD
        cycling_table['Day'] = pd.to_datetime(cycling_table['Day']).dt.date

        column_configuration = {
            "Day": st.column_config.DateColumn("Day", format="YYYY-MM-DD"),
            "distance": st.column_config.NumberColumn("Distance (km)", format="%.2f"),
            "duration": st.column_config.TextColumn("Duration"),
            "averageHR": st.column_config.NumberColumn("Avg HR"),
            "averageSpeed": st.column_config.NumberColumn("Speed (km/h)", format="%.1f"),
        }
        
        display_columns = {
            'Day': 'Day',
            'distance': 'Distance (km)',
            'duration': 'Duration',
            'averageHR': 'Avg HR',
            'averageSpeed': 'Avg Speed (km/h)',
            'activityName': 'Activity Name',
        }
        
        paginated_df, selected_row = ut.paginated_table(
            df=cycling_table,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="cycling_list"
        )
                
        if selected_row is not None:
            selected_row_data = paginated_df.iloc[selected_row]
            selected_row_id = cycling_table.iloc[selected_row]['activityId']
            
            st.markdown(f"#### 🔎 Activity Details: {selected_row_data.get('Activity Name')}")
            
            m_cols = st.columns(4)
            with m_cols[0]: ui.metric_card("Distance", f"{selected_row_data.get('Distance (km)', 0):.2f} km", icon="📏")
            with m_cols[1]: ui.metric_card("Duration", selected_row_data.get('Duration', 0), icon="⏱️")
            with m_cols[2]: ui.metric_card("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f} bpm", icon="❤️")
            with m_cols[3]: ui.metric_card("Avg Speed", f"{selected_row_data.get('Avg Speed (km/h)', 0):.1f} km/h", icon="⚡")

            activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
            gcs_base_path = f"data/raw/{activity_month}/{selected_row_id}"
            
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
                y1 = met1.selectbox("Metric 1", ["HeartRate", "Cadence", "Watts", "Altitude"], index=0, key="cy1")
                y2 = met2.selectbox("Metric 2", ["HeartRate", "Cadence", "Watts", "Altitude"], index=3, key="cy2")

                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(x=df_tcx["Time"], y=df_tcx[y1], name=y1, line=dict(color="#ef4444")), secondary_y=False)
                fig.add_trace(go.Scatter(x=df_tcx["Time"], y=df_tcx[y2], name=y2, line=dict(color="#10b981")), secondary_y=True)
                fig.update_layout(height=400, template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig, width="stretch")
    else:
        st.info("No cycling activities found.")
