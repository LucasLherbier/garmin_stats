import streamlit as st
import pandas as pd
from datetime import timedelta
import sql_queries as sql 
import plotly.express as px
import uuid

def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def show(conn):
    st.subheader("🏁 Race Metrics")

    # Define races with their periods
    races = [
        {'start': '2022-05-02', 'end': '2022-07-15', 'distance': 'Olympic', 'race': 'Magog 2022'},
        {'start': '2022-05-02', 'end': '2022-09-09', 'distance': 'Olympic', 'race': 'Esprint Montréal 2022'},
        {'start': '2023-01-06', 'end': '2023-07-14', 'distance': 'Olympic', 'race': 'Magog 2023'},
        {'start': '2023-01-06', 'end': '2023-08-19', 'distance': '70.3', 'race': 'Mont Tremblant 2023'},
        {'start': '2023-01-06', 'end': '2023-09-09', 'distance': 'Sprint', 'race': 'Esprint Montréal 2023'},
        {'start': '2023-01-06', 'end': '2024-06-21', 'distance': 'Olympic', 'race': 'Mont Tremblant 2024'},
        {'start': '2023-12-04', 'end': '2024-07-13', 'distance': '140.6', 'race': 'Vitoria Gasteiz 2024'},
        {'start': '2024-12-30', 'end': '2025-09-06', 'distance': '70.3', 'race': 'Santa Cruz 2025'},
        {'start': '2024-12-30', 'end': '2025-09-20', 'distance': '70.3', 'race': 'Cervia 2025'}
    ]

    # Race Selection
    race_options = [f"{race['race']} ({race['distance']})" for race in races]
    selected_race_display = st.selectbox("Select Race", race_options)
    
    # Find the selected race data
    selected_race_index = race_options.index(selected_race_display)
    selected_race_data = races[selected_race_index]

    # Distance Metrics Table
    st.subheader("📊 Distance Metrics (km)")

    # Fetch race metrics
    race_metrics = pd.read_sql(
        sql.get_race_metrics_query(selected_race_data['start'], selected_race_data['end']),
        conn
    )

    if not race_metrics.empty:
        # Header row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Metric**")
        with col2:
            st.markdown("<div style='text-align: center;'><strong>🏊‍♂️ Swimming</strong></div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='text-align: center;'><strong>🚴‍♂️ Cycling</strong></div>", unsafe_allow_html=True)
        with col4:
            st.markdown("<div style='text-align: center;'><strong>🏃‍♂️ Running</strong></div>", unsafe_allow_html=True)

        # Total row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Total**")
        with col2:
            st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics['total_distance_swim'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; background-color: rgba(255, 127, 14, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(255, 127, 14, 0.3);'>{race_metrics['total_distance_bike'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{race_metrics['total_distance_run'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)

        # Average Weekly row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Avg Weekly**")
        with col2:
            st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics['average_week_distance_swim'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; background-color: rgba(255, 127, 14, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(255, 127, 14, 0.3);'>{race_metrics['average_week_distance_bike'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{race_metrics['average_week_distance_run'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)

        # Average Last 8 Weeks row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Avg (8W)**")
        with col2:
            st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics['average_8week_distance_swim'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; background-color: rgba(255, 127, 14, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(255, 127, 14, 0.3);'>{race_metrics['average_8week_distance_bike'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{race_metrics['average_8week_distance_run'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)

        # Average Monthly row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Avg Monthly**")
        with col2:
            st.markdown(f"<div style='text-align: center; background-color: rgba(31, 119, 180, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(31, 119, 180, 0.3);'>{race_metrics['average_month_distance_swim'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='text-align: center; background-color: rgba(255, 127, 14, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(255, 127, 14, 0.3);'>{race_metrics['average_month_distance_bike'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)
        with col4:
            st.markdown(f"<div style='text-align: center; background-color: rgba(44, 160, 44, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(44, 160, 44, 0.3);'>{race_metrics['average_month_distance_run'].iloc[0] or 0:.0f}</div>", unsafe_allow_html=True)

        # Duration metrics - centered
        st.subheader("⏱️ Duration Metrics")
        col_spacer5, col4, col_spacer6, col5, col_spacer7 = st.columns([2, 3, 1, 3, 2])
        
        with col4:
            st.metric("Avg Duration per Week", format_duration(race_metrics['average_duration_per_week'].iloc[0]))
        with col5:
            st.metric("Avg Duration (Last 8 Weeks)", format_duration(race_metrics['average_duration_last_8_weeks'].iloc[0]))

        # Granularity selection with buttons
        st.subheader("📈 Distance Over Time")
        
        # Initialize session state if not exists
        if 'granularity' not in st.session_state:
            st.session_state.granularity = 'Week'
        
        # Create button columns for better spacing
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
        
        with col_btn1:
            if st.button("📅 Week", use_container_width=True, type="primary" if st.session_state.granularity == 'Week' else "secondary"):
                st.session_state.granularity = 'Week'
                st.rerun()
        
        with col_btn2:
            if st.button("📆 Month", use_container_width=True, type="primary" if st.session_state.granularity == 'Month' else "secondary"):
                st.session_state.granularity = 'Month'
                st.rerun()

        granularity = st.session_state.granularity

        # Display current selection
        st.info(f"Currently showing: **{granularity}ly** view")

        # Graphs for each sport
        sports = [
            {'name': 'swimming', 'display': 'Swimming', 'emoji': '🏊‍♂️', 'color': '#1f77b4'},
            {'name': 'cycling', 'display': 'Cycling', 'emoji': '🚴‍♂️', 'color': '#ff7f0e'}, 
            {'name': 'running', 'display': 'Running', 'emoji': '🏃‍♂️', 'color': '#2ca02c'}
        ]
        
        for sport in sports:
            st.subheader(f"{sport['emoji']} {sport['display']} Distance Over Time")
            sport_data = pd.read_sql(
                sql.get_race_distance_by_timerange_query(
                    selected_race_data['start'], 
                    selected_race_data['end'], 
                    granularity, 
                    sport['name']
                ),
                conn
            )
            print(selected_race_data['start'], 
                    selected_race_data['end'], 
                    granularity, 
                    sport['name'])
            if not sport_data.empty:
                fig = px.area(
                    sport_data,
                    x="time_period",
                    y="total_distance",
                    title=f"{sport['emoji']} {sport['display']} Distance by {granularity} - {selected_race_data['race']}",
                    markers=True,
                    color_discrete_sequence=[sport['color']]
                )
                fig.update_traces(textposition='top center', texttemplate='%{y:.0f}')
                fig.update_layout(
                    xaxis_title=granularity,
                    yaxis_title="Distance (km)"
                )
                st.plotly_chart(fig, use_container_width=True, key=f"{sport['name']}_distance_chart_{uuid.uuid4()}")
            else:
                st.warning(f"No {sport['display'].lower()} data available for the selected race period.")


    else:
        st.warning("No data available for the selected race period.")

    # Fetch activity duration data based on the selected granularity and race dates
    activity_duration_data = pd.read_sql(
        sql.get_activity_duration_by_granularity_query(
            selected_race_data['start'], 
            selected_race_data['end'], 
            st.session_state.granularity
        ),
        conn
    )

    # Format the duration to hh:mm:ss
    activity_duration_data['FormattedDuration'] = activity_duration_data['Duration'].apply(format_duration)

    # Create a stacked bar plot
    if not activity_duration_data.empty:
        fig = px.bar(
            activity_duration_data,
            x="TimePeriod",
            y="Duration",
            color="activityTypeGrouped",
            title=f"Activity Duration by {st.session_state.granularity}",
            labels={"TimePeriod": "Time Period", "Duration": "Duration (seconds)"}
        )
        # Update traces to show formatted duration as text on the bars
        # Ensure that the text is set for each trace individually
        for trace in fig.data:
            trace_name = trace.name  # Get the name of the trace (activityTypeGrouped)
            trace_text = activity_duration_data.loc[activity_duration_data['activityTypeGrouped'] == trace_name, 'FormattedDuration']
            trace.text = trace_text.tolist()
        
        # Update layout to reflect the correct y-axis title
        fig.update_layout(yaxis_title="Duration (hh:mm:ss)")
            
        # Define tick values and their corresponding formatted labels
        max_duration = int(activity_duration_data['Duration'].max()*1.75)  # Ensure max_duration is an integer
        tickvals = list(range(0, max_duration + 1, 7200))  # Every 2 hours
        ticktext = [format_duration(val) for val in tickvals]
        
        # Set the y-axis ticks to display formatted durations
        fig.update_yaxes(tickvals=tickvals, ticktext=ticktext, range=[0, max_duration])
        
        # Use a unique key for the plotly chart
        st.plotly_chart(fig, key=f"activity_duration_chart_{sport['name']}_{uuid.uuid4()}")

    # Use a unique key for the plotly chart
    else:
        st.warning(f"No activity duration data available for the selected granularity: {st.session_state.granularity}")
