import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
import os
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import numpy as np
import sql_queries as sql

from actions.running_pace_bar_plot import plot_pace_bar
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
                st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{ut.format_duration(race_metrics_filtered['duration_total'].item())}</div>", unsafe_allow_html=True)
            with col5:
                st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{ut.format_duration(race_metrics_filtered['duration_avg'].item())}</div>", unsafe_allow_html=True)
            with col6:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['nb_trainings'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col7:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['elevationGain'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col8:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['calories'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col9:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['averageHR'].item() or 0:.0f}</div>", unsafe_allow_html=True)

    st.subheader("Running Distance Over Time")

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
    swimming_data = pd.read_sql(sql.get_weekly_sport_query('swimming', st.session_state.time_range_metrics), conn)

    if not swimming_data.empty:
        # Adaptation du titre selon la sélection
        time_range_label = {
            "8_weeks": "Latest 8 Weeks",
            "6_months": "Last 6 Months",
            "ytd": "Year to Date",
            "all": "All Time"
        }.get(st.session_state.time_range_metrics, st.session_state.time_range_metrics)

        fig = px.area(
            swimming_data,
            x="Week",
            y="total_distance",
            title=f"Running Distance by Week ({time_range_label})",
            markers=True
        )
        fig.update_traces(textposition='top center', texttemplate='%{y:.2f}')
        st.plotly_chart(fig)
    else:
        st.warning(f"No data available for the selected time range: {time_range_label}")


    st.subheader("Recent Running Activities")


    # Fetch activities data based on the selected time range for activities
    swimming_table = pd.read_sql(sql.get_recent_activities_query('swimming', st.session_state.time_range_metrics), conn)

    if not swimming_table.empty:
        # Define column configurations
        column_configuration = {
            "Day": st.column_config.TextColumn("Day", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Activity ID": st.column_config.TextColumn("Activity ID", width="small"),
            "Distance (km)": st.column_config.NumberColumn("Distance (km)", width="small"),
            "Duration": st.column_config.TextColumn("Duration", width="small"),
            "Calories": st.column_config.NumberColumn("Calories", width="small"),
            "Avg HR": st.column_config.NumberColumn("Avg HR", width="small"),
            "Elevation Gain (m)": st.column_config.NumberColumn("Elevation Gain (m)", width="small"),
            "Avg Speed (km/h)": st.column_config.NumberColumn("Avg Speed (km/h)", width="small"),
            "Avg Cadence": st.column_config.NumberColumn("Avg Cadence", width="small"),
            "Elevation Loss (m)": st.column_config.NumberColumn("Elevation Loss (m)", width="small"),
            "Training Effect": st.column_config.TextColumn("Training Effect", width="small"),
            "Training Effect Label": st.column_config.TextColumn("Training Effect Label", width="small"),
            "Max HR": st.column_config.NumberColumn("Max HR", width="small"),
            "Min HR": st.column_config.NumberColumn("Min HR", width="small"),
        }
        # Rename columns for display
        display_columns = {
            'Day': 'Day',
            'distance': 'Distance (km)',
            'duration': 'Duration',
            'elevationGain': 'Elevation Gain (m)',
            'calories': 'Calories',
            'averageHR': 'Avg HR',
            'averageSpeed': 'Avg Speed (km/h)',
            'averageRunCadence': 'Avg Cadence',
            'elevationLoss': 'Elevation Loss (m)',
            'trainingEffectLabel': 'Training Effect Label',
            'trainingEffect': 'Training Effect',
            'maxHR': 'Max HR',
            'minHR': 'Min HR',
            'locationName': 'Location',
            'activityName': 'Activity Name',
            'activityTypeGrouped': 'Type',
            'activityId': 'Activity ID',
        }
        paginated_df, selected_row = ut.paginated_table(
            df=swimming_table,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="swimming"
        )

                
        # Check if a row is selected
        if selected_row and len(selected_row["selection"]["rows"]) > 0:
            selected_row_index = selected_row["selection"]["rows"][0]
            selected_row_data = paginated_df.iloc[selected_row_index]
            # Vérifiez que la colonne 'Activity ID' existe dans paginated_df
            if 'Activity ID' in paginated_df.columns:
                selected_row_id = selected_row_data['Activity ID']
                st.write(f"Selected Activity ID: {selected_row_id}")
                # Create a list of metrics to display
                metrics = [
                    ("Distance (km)", f"{selected_row_data.get('Distance (km)', 0):.2f}"),
                    ("Duration", selected_row_data.get('Duration', 0)),
                    ("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f}"),
                    ("Elevation Gain (m)", f"{selected_row_data.get('Elevation Gain (m)', 0):.0f}"),
                    ("Calories", f"{selected_row_data.get('Calories', 0):.0f}"),
                    ("Avg Speed (km/h)", f"{selected_row_data.get('Avg Speed (km/h)', 0):.2f}"),
                    ("Avg Cadence", f"{selected_row_data.get('Avg Cadence', 0):.1f}"),
                    ("Elevation Loss (m)", f"{selected_row_data.get('Elevation Loss (m)', 0):.0f}")
                ]

                # Display metrics in 5 columns per row
                for i in range(0, len(metrics), 4):
                    cols = st.columns(4)
                    for j, (name, value) in enumerate(metrics[i:i+4]):
                        with cols[j]:
                            st.metric(name, value)

                # Display GPX file if exists
                activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                activity_output_dir = os.path.join(project_root, "data", "raw", activity_month, str(selected_row_id))

                st.subheader("Avg Moving Pace per Split")
                split_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.csv")
                if os.path.exists(split_file_path):
                    pace_fig = plot_pace_bar(split_file_path)
                    st.plotly_chart(pace_fig, use_container_width=True)
                else :
                    st.warning(f"Split file not found")
                                        
                # Check for TCX file
                tcx_file_path = os.path.join(activity_output_dir, f"{str(selected_row_id)}.tcx")
                # if os.path.exists(tcx_file_path):
                #     # Parse TCX file to DataFrame
                #     df = parse_tcx_to_dataframe(tcx_file_path)
                #     # Create some space in the app layout for better visibility
                #     st.markdown("<h2 style='text-align: center;'>Choose Metrics to Display</h2>", unsafe_allow_html=True)
                    

                #     # Default Y-Axis metrics
                #     default_y1 = 'HeartRate'
                #     default_y2 = 'Altitude'

                #     # Create columns for selecting Y-Axis from dropdowns
                #     cols = st.columns(2)

                #     with cols[0]:
                #         y_axis_metric_1 = st.selectbox(
                #             "Select Y-Axis Metric 1", 
                #             ["HeartRate", "Cadence", "Watts", "Altitude"], 
                #             index=["HeartRate", "Cadence", "Watts", "Altitude"].index(default_y1)
                #         )

                #     with cols[1]:
                #         y_axis_metric_2 = st.selectbox(
                #             "Select Y-Axis Metric 2", 
                #             ["HeartRate", "Cadence", "Watts", "Altitude"], 
                #             index=["HeartRate", "Cadence", "Watts", "Altitude"].index(default_y2)
                #         )


                #     # Get the Y-axis data based on the selections
                #     y_data_1 = df[y_axis_metric_1]
                #     y_data_2 = df[y_axis_metric_2]

                #     # Create figure with secondary y-axis if needed
                #     fig = make_subplots(specs=[[{"secondary_y": True}]])

                #     # Function to add traces
                #     def add_trace(name, data, color, hovertemplate, secondary_y):
                #         fig.add_trace(
                #             go.Scatter(
                #                 x=df["Time"],
                #                 y=data,
                #                 name=name,
                #                 line=dict(color=color),
                #                 hovertemplate=hovertemplate + "<extra></extra>",
                #             ),
                #             secondary_y=secondary_y,
                #         )
    
                #     # Add Y-axis trace 1
                #     if y_axis_metric_1 == "HeartRate" or y_axis_metric_1 == "Watts":
                #         hover_y1 = f"{y_axis_metric_1}: %{{y:.0f}}<br>Time: %{{x}}"
                #         add_trace(y_axis_metric_1, y_data_1, "red", hover_y1, secondary_y=True)
                #     else:
                #         hover_y1 = f"{y_axis_metric_1}: %{{y:.2f}}<br>Time: %{{x}}"
                #         add_trace(y_axis_metric_1, y_data_1, "green", hover_y1, secondary_y=False)

                #     # Add Y-axis trace 2
                #     if y_axis_metric_2 == "HeartRate" or y_axis_metric_2 == "Watts":
                #         hover_y2 = f"{y_axis_metric_2}: %{{y:.0f}}<br>Time: %{{x}}"
                #         add_trace(y_axis_metric_2, y_data_2, "purple", hover_y2, secondary_y=True)
                #     else:
                #         hover_y2 = f"{y_axis_metric_2}: %{{y:.2f}}<br>Time: %{{x}}"
                #         add_trace(y_axis_metric_2, y_data_2, "orange", hover_y2, secondary_y=False)

                #     # Update layout with titles
                #     fig.update_layout(
                #         title=f"Activity Data: {y_axis_metric_1} and {y_axis_metric_2} vs Time",
                #         xaxis_title="Time",
                #         yaxis_title=f"{y_axis_metric_1}",
                #         yaxis2_title=f"{y_axis_metric_2}" if y_axis_metric_2 in ["HeartRate", "Watts"] else "",
                #         hovermode="x unified",
                #         height=600,
                #     )

                #     # Show the plot
                #     st.plotly_chart(fig, use_container_width=True)
                # else:
                #     st.error("TCX not found")
            else:
                st.error("La colonne 'Activity ID' est introuvable dans les données affichées.")




    else:
        st.info("No swimming activities found.")