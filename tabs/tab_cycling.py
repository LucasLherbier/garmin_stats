import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import numpy as np
import sql_queries as sql

from actions.display_map import display_gpx_map
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.display_pace_bar_plot import plot_running_bar  # This may be replaced with a cycling pace plot if needed
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut


def show(conn):
    st.subheader("Cycling Metrics")

    # Fetch race metrics for cycling
    race_metrics = pd.read_sql(
        sql.get_volume_metrics_query("cycling"),
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
            st.markdown("<div style='text-align: center;'><strong>Elevation Gain</strong></div>", unsafe_allow_html=True)
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
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['elevationGain'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col8:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['calories'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col9:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['averageHR'].item() or 0:.0f}</div>", unsafe_allow_html=True)

    st.subheader("Cycling Distance Over Time")

    # Initialisation de la session state si nécessaire
    if 'time_range_metrics' not in st.session_state:
        st.session_state.time_range_metrics = "8_weeks"

    # Boutons de sélection
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    with col_btn1:
        if st.button("📅 8 Weeks", use_container_width=True, type="primary" if st.session_state.time_range_metrics == '8_weeks' else "secondary"):
            st.session_state.time_range_metrics = '8_weeks'
            st.rerun()

    with col_btn2:
        if st.button("📅 6 Months", use_container_width=True, type="primary" if st.session_state.time_range_metrics == '6_months' else "secondary"):
            st.session_state.time_range_metrics = '6_months'
            st.rerun()

    with col_btn3:
        if st.button("📅 YTD", use_container_width=True, type="primary" if st.session_state.time_range_metrics == 'ytd' else "secondary"):
            st.session_state.time_range_metrics = 'ytd'
            st.rerun()

    with col_btn4:
        if st.button("📅 All Time", use_container_width=True, type="primary" if st.session_state.time_range_metrics == 'all' else "secondary"):
            st.session_state.time_range_metrics = 'all'
            st.rerun()

    # Récupération des données et affichage du graphique
    cycling_data = pd.read_sql(sql.get_weekly_sport_query('cycling', st.session_state.time_range_metrics), conn)

    if not cycling_data.empty:
        # Adaptation du titre selon la sélection
        time_range_label = {
            "8_weeks": "Latest 8 Weeks",
            "6_months": "Last 6 Months",
            "ytd": "Year to Date",
            "all": "All Time"
        }.get(st.session_state.time_range_metrics, st.session_state.time_range_metrics)

        fig = px.area(
            cycling_data,
            x="Week",
            y="total_distance",  # Replace with cycling-specific metric if needed
            title=f"Cycling Distance by Week ({time_range_label})",
            markers=True
        )
        fig.update_traces(textposition='top center', texttemplate='%{y:.2f}')
        st.plotly_chart(fig)
    else:
        st.warning(f"No data available for the selected time range: {time_range_label}")

    st.subheader("Recent Cycling Activities")

    # Fetch activities data based on the selected time range for activities
    cycling_table = pd.read_sql(sql.get_recent_activities_query('cycling', st.session_state.time_range_metrics), conn)

    if not cycling_table.empty:
        # Define column configurations for cycling data
        column_configuration = {
            "Day": st.column_config.TextColumn("Day", width="small"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "activityId": st.column_config.TextColumn("Activity ID", width="small"),
            "distance": st.column_config.NumberColumn("Distance (km)", width="small"),
            "duration": st.column_config.TextColumn("Duration", width="small"),
            "calories": st.column_config.NumberColumn("Calories", width="small"),
            "averageHR": st.column_config.NumberColumn("Avg HR", width="small"),
            "elevationGain": st.column_config.NumberColumn("Elevation Gain (m)", width="small"),
            "elevationLoss": st.column_config.NumberColumn("Elevation Loss (m)", width="small"),
            "averageSpeed": st.column_config.NumberColumn("Avg Speed (km/h)", width="small"),
            "maxSpeed": st.column_config.NumberColumn("Max Speed (km/h)", width="small"),
            "averageTemperature": st.column_config.NumberColumn("Avg Temperature (°C)", width="small"),
            "maxHR": st.column_config.NumberColumn("Max HR", width="small"),
            "minHR": st.column_config.NumberColumn("Min HR", width="small"),
            "waterEstimated": st.column_config.NumberColumn("Water Estimated", width="small"),
        }

        # Optional: map internal column names to display names if you need a different order or label
        display_columns = {
            'Day': 'Day',
            'distance': 'Distance (km)',
            'duration': 'Duration',
            'elevationGain': 'Elevation Gain (m)',
            'elevationLoss': 'Elevation Loss (m)',
            'calories': 'Calories',
            'averageHR': 'Avg HR',
            'averageSpeed': 'Avg Speed (km/h)',
            'maxSpeed': 'Max Speed (km/h)',
            'averageTemperature': 'Avg Temperature (°C)',
            'maxHR': 'Max HR',
            'minHR': 'Min HR',
            'locationName': 'Location',
            'activityName': 'Activity Name',
            'type': 'Type',
            'activityId': 'Activity ID',
            'waterEstimated': 'Water Estimated',
            'activityName': 'Activity Name',
        }
                
        available_columns = {col: display_columns[col] for col in display_columns if col in cycling_table.columns}
        display_df = cycling_table[list(available_columns.keys())].rename(columns=display_columns)

        # Pagination logic
        page_size = 10
        total_pages = (len(display_df) + page_size - 1) // page_size

        # Initialize current_page in session_state if not present
        if "current_page" not in st.session_state:
            st.session_state.current_page = 1

        # Calculate start and end indices
        start_idx = (st.session_state.current_page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = display_df.iloc[start_idx:end_idx]

        # Display the paginated dataframe
        selected_rows = st.dataframe(
            paginated_df,
            column_config=column_configuration,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="cycling_dataframe",  # Fixed key to keep selection
        )

        # Pagination UI at the bottom
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])
        with col1:
            if st.button("⏪ First", use_container_width=True, disabled=st.session_state.current_page == 1):
                st.session_state.current_page = 1
                st.rerun()
        with col2:
            if st.button("← Prev", use_container_width=True, disabled=st.session_state.current_page == 1):
                st.session_state.current_page -= 1
                st.rerun()
        with col3:
            st.markdown(f"<div style='text-align: center; margin-top: 7px;'><strong>{st.session_state.current_page} / {total_pages}</strong></div>", unsafe_allow_html=True)
        with col4:
            if st.button("Next →", use_container_width=True, disabled=st.session_state.current_page == total_pages):
                st.session_state.current_page += 1
                st.rerun()
        with col5:
            if st.button("Last ⏩", use_container_width=True, disabled=st.session_state.current_page == total_pages):
                st.session_state.current_page = total_pages
                st.rerun()

        # Check if a row is selected
        if selected_rows and len(selected_rows["selection"]["rows"]) > 0:
            selected_row_index = selected_rows["selection"]["rows"][0]
            selected_row_data = paginated_df.iloc[selected_row_index]
            
            # Check if the column 'Activity ID' exists in paginated_df
            if 'Activity ID' in paginated_df.columns:
                selected_row_id = selected_row_data['Activity ID']
                st.write(f"Selected Activity ID: {selected_row_id}")

                # Create a list of metrics to display
                metrics = [
                    ("Distance (km)", f"{selected_row_data.get('Distance (km)', 0):.2f}"),
                    ("Duration", selected_row_data.get('Duration', 0)),
                    ("Elevation Gain (m)", f"{selected_row_data.get('Elevation Gain (m)', 0):.0f}"),
                    ("Avg Speed (km/h)", f"{selected_row_data.get('Avg Speed (km/h)', 0):.2f}"),
                    ("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f}"),
                    ("Calories", f"{selected_row_data.get('Calories', 0):.0f}"),
                    ("Water Estimated", f"{selected_row_data.get('Water Estimated', 0):.0f}"),
                    ("Elevation Loss (m)", f"{selected_row_data.get('Elevation Loss (m)', 0):.0f}"),
                    ("Max Speed (km/h)", f"{selected_row_data.get('Max Speed (km/h)', 0):.0f}"),
                    ("Max HR", f"{selected_row_data.get('Max HR', 0):.0f}"),
                ]

                # Display metrics in 4 columns per row
                for i in range(0, len(metrics), 5):
                    cols = st.columns(5)
                    for j, (name, value) in enumerate(metrics[i:i+5]):
                        with cols[j]:
                            st.metric(name, value)

                # Display GPX file if exists
                activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                activity_output_dir = os.path.join(project_root, "data", "raw", activity_month, str(selected_row_id))
                gpx_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.gpx")
                if os.path.exists(gpx_file_path):
                    display_gpx_map(gpx_file_path) 
                else:
                    st.error("GPX file not found.")


                print('selected_row_data\n\n\n\n\n\n', display_df)

                # st.subheader("Avg Moving Pace per Split")
                # split_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.csv")
                # if os.path.exists(split_file_path):
                #     pace_fig = plot_running_bar(split_file_path)
                #     st.plotly_chart(pace_fig, use_container_width=True)
                # else:
                #     st.warning(f"Split file not found")

                # Check for TCX file
                tcx_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.tcx")
                if os.path.exists(tcx_file_path):
                    # Parse TCX file to DataFrame
                    df = parse_tcx_to_dataframe(tcx_file_path)
                    # Create some space in the app layout for better visibility
                    st.markdown("<h2 style='text-align: center;'>Choose Metrics to Display</h2>", unsafe_allow_html=True)
                    

                    # Default Y-Axis metrics
                    default_y1 = 'HeartRate'
                    default_y2 = 'Altitude'

                    # Create columns for selecting Y-Axis from dropdowns
                    cols = st.columns(2)

                    with cols[0]:
                        y_axis_metric_1 = st.selectbox(
                            "Select Y-Axis Metric 1", 
                            ["HeartRate", "Cadence", "Watts", "Altitude"], 
                            index=["HeartRate", "Cadence", "Watts", "Altitude"].index(default_y1)
                        )

                    with cols[1]:
                        y_axis_metric_2 = st.selectbox(
                            "Select Y-Axis Metric 2", 
                            ["HeartRate", "Cadence", "Watts", "Altitude"], 
                            index=["HeartRate", "Cadence", "Watts", "Altitude"].index(default_y2)
                        )


                    # Get the Y-axis data based on the selections
                    y_data_1 = df[y_axis_metric_1]
                    y_data_2 = df[y_axis_metric_2]

                    # Create figure with secondary y-axis if needed
                    fig = make_subplots(specs=[[{"secondary_y": True}]])

                    # Function to add traces
                    def add_trace(name, data, color, hovertemplate, secondary_y):
                        fig.add_trace(
                            go.Scatter(
                                x=df["Time"],
                                y=data,
                                name=name,
                                line=dict(color=color),
                                hovertemplate=hovertemplate + "<extra></extra>",
                            ),
                            secondary_y=secondary_y,
                        )
    
                    # Add Y-axis trace 1
                    if y_axis_metric_1 == "HeartRate" or y_axis_metric_1 == "Watts":
                        hover_y1 = f"{y_axis_metric_1}: %{{y:.0f}}<br>Time: %{{x}}"
                        add_trace(y_axis_metric_1, y_data_1, "red", hover_y1, secondary_y=True)
                    else:
                        hover_y1 = f"{y_axis_metric_1}: %{{y:.2f}}<br>Time: %{{x}}"
                        add_trace(y_axis_metric_1, y_data_1, "green", hover_y1, secondary_y=False)

                    # Add Y-axis trace 2
                    if y_axis_metric_2 == "HeartRate" or y_axis_metric_2 == "Watts":
                        hover_y2 = f"{y_axis_metric_2}: %{{y:.0f}}<br>Time: %{{x}}"
                        add_trace(y_axis_metric_2, y_data_2, "purple", hover_y2, secondary_y=True)
                    else:
                        hover_y2 = f"{y_axis_metric_2}: %{{y:.2f}}<br>Time: %{{x}}"
                        add_trace(y_axis_metric_2, y_data_2, "orange", hover_y2, secondary_y=False)

                    # Update layout with titles
                    fig.update_layout(
                        title=f"Activity Data: {y_axis_metric_1} and {y_axis_metric_2} vs Time",
                        xaxis_title="Time",
                        yaxis_title=f"{y_axis_metric_1}",
                        yaxis2_title=f"{y_axis_metric_2}" if y_axis_metric_2 in ["HeartRate", "Watts"] else "",
                        hovermode="x unified",
                        height=600,
                    )

                    # Show the plot
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("TCX not found")
    else:
        st.info("No cycling activities found.")
