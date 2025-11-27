import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import numpy as np
import plotly.express as px
from actions.display_pace_bar_plot import plot_running_bar
from actions import utils as ut
import sql_queries as sql
import plotly.graph_objects as go

from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_swimming_csv
from actions.display_pace_bar_plot import plot_swimming_bar
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut


def show(conn):
    st.subheader("Swimming Metrics")

    # Fetch race metrics
    race_metrics = pd.read_sql(
        sql.get_volume_metrics_query("swimming"),
        conn
    )

    if not race_metrics.empty:
        # Create 9 columns
        col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)

        # En-têtes
        with col1:
            st.markdown("**Metric**")
        with col2:
            st.markdown("<div style='text-align: center;'><strong>Distance (Total)</strong></div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='text-align: center;'><strong>Distance (Avg)</strong></div>", unsafe_allow_html=True)
        with col4:
            st.markdown("<div style='text-align: center;'><strong>Duration (Total)</strong></div>", unsafe_allow_html=True)
        with col5:
            st.markdown("<div style='text-align: center;'><strong>Duration (Avg)</strong></div>", unsafe_allow_html=True)
        with col6:
            st.markdown("<div style='text-align: center;'><strong>Trainings</strong></div>", unsafe_allow_html=True)
        with col7:
            st.markdown("<div style='text-align: center;'><strong>Total Number Of Strokes</strong></div>", unsafe_allow_html=True)
        with col8:
            st.markdown("<div style='text-align: center;'><strong>Calories</strong></div>", unsafe_allow_html=True)
        with col9:
            st.markdown("<div style='text-align: center;'><strong>Avg HR</strong></div>", unsafe_allow_html=True)

        # Ligne "Last Week"
        dict_columns = {"last_1":"Last week", "last_4":"Last 4 weeks", "last_12":"Last 12 weeks", "last_18":"Last 18 weeks", "last_all": "Year to Date"}
        for name_i, title in dict_columns.items() :
            race_metrics_filtered = race_metrics[race_metrics['name'] == name_i]
            col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
            with col1:
                st.markdown(f"{title}")
            with col2:
                st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics_filtered['distance_total'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics_filtered['distance_avg'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{ut.format_duration_no_days(race_metrics_filtered['duration_total'].item())}</div>", unsafe_allow_html=True)
            with col5:
                st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{ut.format_duration_no_days(race_metrics_filtered['duration_avg'].item())}</div>", unsafe_allow_html=True)
            with col6:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['nb_trainings'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col7:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['totalNumberOfStrokes'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col8:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['calories'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col9:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['averageHR'].item() or 0:.0f}</div>", unsafe_allow_html=True)

    st.subheader("Running Distance Over Time")

    if "time_range_metrics" not in st.session_state:
        st.session_state.time_range_metrics = "8_weeks"

    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("📅 8 Weeks", type="primary" if st.session_state.time_range_metrics == "8_weeks" else "secondary", use_container_width=True):
            st.session_state.time_range_metrics = "8_weeks"
            st.rerun()

    with col_btn2:
        if st.button("📅 6 Months", type="primary" if st.session_state.time_range_metrics == "6_months" else "secondary", use_container_width=True):
            st.session_state.time_range_metrics = "6_months"
            st.rerun()

    with col_btn3:
        if st.button("📅 YTD", type="primary" if st.session_state.time_range_metrics == "ytd" else "secondary", use_container_width=True):
            st.session_state.time_range_metrics = "ytd"
            st.rerun()

    with col_btn4:
        if st.button("📅 All Time", type="primary" if st.session_state.time_range_metrics == "all" else "secondary", use_container_width=True):
            st.session_state.time_range_metrics = "all"
            st.rerun()

    swimming_data = pd.read_sql(
        sql.get_weekly_sport_query("swimming", st.session_state.time_range_metrics), conn
    )

    if not swimming_data.empty:

        time_range_label = {
            "8_weeks": "Latest 8 Weeks",
            "6_months": "Last 6 Months",
            "ytd": "Year to Date",
            "all": "All Time",
        }[st.session_state.time_range_metrics]

        fig = px.area(
            swimming_data,
            x="Week",
            y="total_distance",
            title=f"Swimming Distance by Week ({time_range_label})",
            markers=True
        )
        st.plotly_chart(fig)

    # ================================
    # Recent Swimming Activities
    # ================================

    st.subheader("Recent Swimming Activities")

    swimming_table = pd.read_sql(
        sql.get_recent_activities_query("swimming", st.session_state.time_range_metrics), conn
    )

    if not swimming_table.empty:

        # Column configs (kept same structure)
        column_configuration = {
            "Day": st.column_config.TextColumn("Day", width="small"),
            #"Type": st.column_config.TextColumn("Type", width="small"),
            "Activity ID": st.column_config.TextColumn("Activity ID", width="small"),
            "Distance (km)": st.column_config.NumberColumn("Distance (km)", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Calories": st.column_config.NumberColumn("Calories", width="small"),
            "Avg HR": st.column_config.NumberColumn("Avg HR", width="small"),
            "Max HR": st.column_config.NumberColumn("Max HR", width="small"),
            #"Min HR": st.column_config.NumberColumn("Min HR", width="small"),
            "Total Strokes": st.column_config.NumberColumn("Total Strokes", width="small"),
            #"Avg Stroke Dist (m)": st.column_config.NumberColumn("Avg Stroke Dist (m)", width="small"),
            "Avg Swim Cadence": st.column_config.NumberColumn("Avg Swim Cadence", width="small"),
            #"Max Swim Cadence": st.column_config.NumberColumn("Max Swim Cadence", width="small"),
            "Avg Speed (km/h)": st.column_config.NumberColumn("Avg Speed (km/h)", width="small"),
            "Max Speed (km/h)": st.column_config.NumberColumn("Max Speed (km/h)", width="small"),
            "Training Effect": st.column_config.NumberColumn("Training Effect", width="small"),
            "Training Effect Label": st.column_config.TextColumn("Training Effect Label", width="small"),
            "Moderate Intensity (min)": st.column_config.NumberColumn("Moderate Intensity (min)", width="small"),
            "Vigorous Intensity (min)": st.column_config.NumberColumn("Vigorous Intensity (min)", width="small"),
        }

        display_columns = {
            "Day": "Day",
            #"activityTypeGrouped": "Type",
            "activityId": "Activity ID",
            "distance": "Distance (km)",
            "duration": "Duration",
            "calories": "Calories",
            "averageHR": "Avg HR",
            "maxHR": "Max HR",
            #"minHR": "Min HR",
            "totalNumberOfStrokes": "Total Strokes",
            #"averageStrokeDistance": "Avg Stroke Dist (m)",
            "averageSwimCadence": "Avg Swim Cadence",
            #"maxSwimCadence": "Max Swim Cadence",
            "averageSpeed": "Avg Speed (km/h)",
            "maxSpeed": "Max Speed (km/h)",
            #"averageSwolf": "Swolf",
            "trainingEffect": "Training Effect",
            "trainingEffectLabel": "Training Effect Label",
            "moderateIntensityMinutes": "Moderate Intensity (min)",
            "vigorousIntensityMinutes": "Vigorous Intensity (min)",
            #"locationName": "Location",
        }

        paginated_df, selected_index = ut.paginated_table(
            df=swimming_table,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="swimming",
        )

        if selected_index:
            selected_row_data = paginated_df.iloc[selected_index]
            selected_row_id = selected_row_data["Activity ID"]

            st.write(f"Selected Activity ID: {selected_row_id}")

            metrics = [
                ("Distance (km)", f"{selected_row_data.get('Distance (km)', 0):.2f}"),
                ("Duration", selected_row_data.get("Duration", "")),
                ("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f}"),
                ("Total Strokes", f"{selected_row_data.get('Total Strokes', 0):.0f}"),
                ("Calories", f"{selected_row_data.get('Calories', 0):.0f}"),
                ("Avg Cadence", f"{selected_row_data.get('Avg Cadence', 0):.1f}"),
                ("Max HR", f"{selected_row_data.get('Max HR', 0):.0f}"),

                ("Elevation Loss (m)", f"{selected_row_data.get('Elevation Loss (m)', 0):.0f}"),
            ]

            for i in range(0, len(metrics), 4):
                cols = st.columns(4)
                for j, (name, value) in enumerate(metrics[i:i+4]):
                    with cols[j]:
                        st.metric(name, value)

            # Split file display
            activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            activity_output_dir = os.path.join(project_root, "data", "raw", activity_month, str(selected_row_id))
            split_file_path = os.path.join(activity_output_dir, f"{selected_row_id}.csv")

            st.subheader("Avg Moving Pace per Split")
            # if os.path.exists(split_file_path):
            #     pace_fig = plot_running_bar(split_file_path)
            #     st.plotly_chart(pace_fig, use_container_width=True)
            # else :
            #     st.warning(f"Split file not found")
                                    
            # Check for TCX file
            tcx_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.csv")
            if os.path.exists(tcx_file_path):
                # Parse TCX file to DataFrame
                df = parse_swimming_csv(tcx_file_path)
                
                pace_fig = plot_swimming_bar(df)
                st.plotly_chart(pace_fig, use_container_width=True)

                # Create some space in the app layout for better visibility
                # Streamlit page setup
                st.set_page_config(page_title="Swimming Splits Table", layout="wide")
                st.title("🏊‍♂️ Swimming Splits Table")

                # Styled table for dark theme
                main_splits = df[~df['Split'].astype(str).str.contains(r'\.') & ~df['IsRest']]
                cols_keep = ['Split','Swim Stroke','Distance','Time','Avg Pace','Best Pace',
                    'Avg SWOLF','Avg HR','Max HR','Total Strokes','Avg Strokes','Calories']
                main_splits = main_splits[cols_keep]
                cols_to_round = ['Lengths', 'Avg SWOLF', 'Avg HR', 'Max HR', 'Total Strokes', 'Avg Strokes', 'Calories']
                for c in cols_to_round:
                    if c in main_splits.columns:
                        main_splits[c] = pd.to_numeric(main_splits[c], errors='coerce').round(0).astype('Int64')

                main_splits['Time'] = main_splits['Time'].astype(str).apply(ut.format_to_mmss )
                main_splits = main_splits.reset_index(drop=True)

                # Display in Streamlit with dark theme
                styled_table = (main_splits.style
                                .set_properties(**{'background-color': '#1e1e1e',
                                    'color':'white',
                                    'border-color':'#444444',
                                    'font-family':'Arial, sans-serif',
                                    'font-size':'12px',       # was 14px
                                    'text-align':'center'})
                                .set_table_styles([{'selector':'th','props':[('background-color','#333333'),
                                                                            ('color','white'),
                                                                            ('font-weight','bold'),
                                                                            ('text-align','center')]}])
                                .apply(lambda x: ['background-color: #2a2a2a' if i%2 else '' for i in range(len(x))], axis=1)
                                )

                st.dataframe(
                    styled_table,
                    use_container_width=True  # makes width auto-fit container
                )
            else:   
                st.error("La colonne 'Activity ID' est introuvable dans les données affichées.")


    else:
        st.info("No swimming activities found.")
