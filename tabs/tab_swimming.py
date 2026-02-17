import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from actions import utils as ut
from actions import utils_ui as ui
import sql_queries as sql
from utils_gcp import read_csv_from_gcs, check_gcs_path_exists
from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_swimming_csv
from actions.display_pace_bar_plot import plot_swimming_bar

def show(conn):
    st.title("🏊‍♂️ Swim Analytics")
    st.markdown("Detailed insights into my swim performance and history activities")

    # Fetch race metrics
    race_metrics = conn(sql.get_volume_metrics_query("swimming"))

    if not race_metrics.empty:
        st.write("### Volume Summary")
        dict_columns = {"last_1":"Last Week", "last_4":"Last 4 Weeks", "last_12":"Last 12 Weeks", "last_18":"Last 18 Weeks", "last_all": "YTD"}
        
        tabs = st.tabs(list(dict_columns.values()))
        for i, (key, title) in enumerate(dict_columns.items()):
            with tabs[i]:
                row = race_metrics[race_metrics['name'] == key]
                if not row.empty:
                    cols = st.columns(4)
                    with cols[0]: ui.metric_card("Total Distance", f"{row['distance_total'].item() or 0:.0f} m", icon="📏")
                    with cols[1]: ui.metric_card("Total Duration", ut.format_duration_no_days(row['duration_total'].item()), icon="⏱️")
                    with cols[2]: ui.metric_card("Trainings", f"{row['nb_trainings'].item() or 0:.0f}", icon="🏊‍♂️")
                    with cols[3]: ui.metric_card("Avg HR", f"{row['averageHR'].item() or 0:.0f} bpm", icon="❤️")

    st.markdown("---")

    st.write("### Performance Trends")
    if "time_range_metrics" not in st.session_state:
        st.session_state.time_range_metrics = "8_weeks"

    tr_cols = st.columns(4)
    ranges = [("8 Weeks", "8_weeks"), ("6 Months", "6_months"), ("YTD", "ytd"), ("All Time", "all")]
    for i, (label, val) in enumerate(ranges):
        if tr_cols[i].button(label, use_container_width=True, type="primary" if st.session_state.time_range_metrics == val else "secondary"):
            st.session_state.time_range_metrics = val
            st.rerun()

    swimming_data = conn(sql.get_weekly_sport_query("swimming", st.session_state.time_range_metrics))

    if not swimming_data.empty:
        fig = px.area(swimming_data, x="Week", y="total_distance", markers=True, 
                     color_discrete_sequence=['#38bdf8'], 
                     template="plotly_dark")
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.write("### 📜 Recent Activities")

    swimming_table = conn(sql.get_recent_activities_query("swimming", st.session_state.time_range_metrics))

    if not swimming_table.empty:
        column_configuration = {
            "Day": st.column_config.TextColumn("Day"),
            "distance": st.column_config.NumberColumn("Distance (m)", format="%d"),
            "duration": st.column_config.TextColumn("Duration"),
            "averageHR": st.column_config.NumberColumn("Avg HR"),
            "totalNumberOfStrokes": st.column_config.NumberColumn("Strokes"),
        }

        display_columns = {
            "Day": "Day",
            "distance": "Distance (m)",
            "duration": "Duration",
            "averageHR": "Avg HR",
            "totalNumberOfStrokes": "Total Strokes",
            "activityName": "Activity Name",
        }

        paginated_df, selected_index = ut.paginated_table(
            df=swimming_table,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="swimming_list",
        )

        if selected_index is not None:
            selected_row_data = paginated_df.iloc[selected_index]
            selected_row_id = swimming_table.iloc[selected_index]["activityId"]

            st.markdown(f"#### 🔎 Activity Details: {selected_row_data.get('Activity Name')}")

            m_cols = st.columns(4)
            with m_cols[0]: ui.metric_card("Distance", f"{selected_row_data.get('Distance (m)', 0):.0f} m", icon="📏")
            with m_cols[1]: ui.metric_card("Duration", selected_row_data.get("Duration", ""), icon="⏱️")
            with m_cols[2]: ui.metric_card("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f} bpm", icon="❤️")
            with m_cols[3]: ui.metric_card("Total Strokes", f"{selected_row_data.get('Total Strokes', 0):.0f}", icon="🏊‍♂️")

            activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
            gcs_base_path = f"data/raw/{activity_month}/{selected_row_id}"
            gcs_csv_path = f"{gcs_base_path}/{selected_row_id}.csv"

            st.write("#### Pace Analysis")
            if check_gcs_path_exists(gcs_csv_path):
                df = read_csv_from_gcs(gcs_csv_path)
                if df is not None:
                    df = parse_swimming_csv(df)
                    st.plotly_chart(plot_swimming_bar(df), use_container_width=True)

                    st.write("#### Split Details")
                    main_splits = df[~df['Split'].astype(str).str.contains(r'\.') & ~df['IsRest']]
                    cols_keep = ['Split','Swim Stroke','Distance','Time','Avg Pace', 'Avg HR','Total Strokes','Calories']
                    cols_to_select = [c for c in cols_keep if c in main_splits.columns]
                    main_splits = main_splits[cols_to_select].reset_index(drop=True)
                    st.dataframe(main_splits, use_container_width=True)
    else:
        st.info("No swimming activities found.")

