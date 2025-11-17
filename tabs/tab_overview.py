import streamlit as st
import pandas as pd
from datetime import timedelta
import sql_queries as sql 
import plotly.express as px
import uuid
import sql_queries as sql
from actions import utils as ut

def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def show(conn):
    st.subheader("🏁 Last week Metrics")

    weekly_metrics = pd.read_sql(
        sql.get_weekly_metrics_with_delta_query_overview(),
        conn,
    )

    # ----- Global totals -----
    week_total_duration = weekly_metrics["current_duration"].sum()
    last_week_total_duration = weekly_metrics["second_total_duration"].sum()

    week_nb_trainings = weekly_metrics["current_nb_trainings"].sum()
    last_week_nb_trainings = weekly_metrics["second_nb_trainings"].sum()

    # ----- Ordered sports -----
    all_sports_columns = weekly_metrics['activityTypeGrouped'].unique()
    main_sports = ["swimming", "cycling", "running", "physical_reinforcement"] 
    all_sports_columns = main_sports  +  [s for s in all_sports_columns if s not in all_sports_columns]
    weekly_metrics["activityTypeGrouped"] = pd.Categorical(
        weekly_metrics["activityTypeGrouped"], categories=all_sports_columns, ordered=True
    )
    weekly_main_stats = weekly_metrics[weekly_metrics['activityTypeGrouped'].isin(["swimming", "cycling", "running"])].sort_values("activityTypeGrouped")
    # ----- Display totals -----
    st.subheader("Weekly Overview")
    cols = st.columns(5)
    cols[0].metric("Total Duration", ut.format_duration(week_total_duration), ut.format_duration(week_total_duration - last_week_total_duration))
    cols[1].metric("Total Trainings", week_nb_trainings, week_nb_trainings - last_week_nb_trainings)

    for i, (_, row) in enumerate(weekly_main_stats.iterrows()):
        sport = row["activityTypeGrouped"].capitalize().replace("_", " ")
        with cols[i+2]:
            st.metric(
                f"{sport} (km)",
                ut.safe_format(row["current_distance"], "{:.2f}"),
                ut.safe_format(row["distance_delta"], "{:+.2f}"),
            )
              
              
     # ----- Display Metrics as Table -----  
    st.header("Weekly Metrics by Sport")
    # Fetch race metrics
    race_metrics = pd.read_sql(
        sql.get_volume_metrics_query_overview(),
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
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['calories'].item() or 0:.0f}</div>", unsafe_allow_html=True)
            with col9:
                st.markdown(f"<div style='text-align: center; background-color: rgba(220, 20, 60, 0.2); padding: 0.5rem; border-radius: 0.25rem; border: 1px solid rgba(220, 20, 60, 0.3);'>{race_metrics_filtered['averageHR'].item() or 0:.0f}</div>", unsafe_allow_html=True)


    st.subheader("Running Distance Over Time")
    # Options
    sport_options = ["duration", "swimming", "cycling", "running", "physical_reinforcement"]

    # Layout
    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)

    # --- Column 1: DROPDOWN ---
    # Initialize session state
    if "sport" not in st.session_state:
        st.session_state.sport = "duration"
    with col_btn1:
        st.session_state.sport = st.selectbox(
            "Metric",
            sport_options,
            index=sport_options.index(st.session_state.sport),
            label_visibility="collapsed"
        )

    # --- Column 2–5: TIME RANGE BUTTONS ---
    if "time_range_metrics" not in st.session_state:
        st.session_state.time_range_metrics = "8_weeks"
        st.session_state.start_date, st.session_state.end_date = ut.compute_date_range('8_weeks')
        st.session_state.granularity = "week"

    with col_btn2:
        if st.button("📅 8 Weeks", use_container_width=True,
                    type="primary" if st.session_state.time_range_metrics == '8_weeks' else "secondary"):
            st.session_state.start_date, st.session_state.end_date = ut.compute_date_range('8_weeks')
            st.session_state.time_range_metrics = '8_weeks'
            st.session_state.granularity = "week"
            st.rerun()

    with col_btn3:
        if st.button("📅 6 Months", use_container_width=True,
                    type="primary" if st.session_state.time_range_metrics == '6_months' else "secondary"):
            st.session_state.start_date, st.session_state.end_date = ut.compute_date_range('6_months')
            st.session_state.time_range_metrics = '6_months'
            st.session_state.granularity = "month"

            st.rerun()

    with col_btn4:
        if st.button("📅 YTD", use_container_width=True,
                    type="primary" if st.session_state.time_range_metrics == 'ytd' else "secondary"):
            st.session_state.start_date, st.session_state.end_date = ut.compute_date_range('ytd')
            st.session_state.time_range_metrics = 'ytd'
            st.session_state.granularity = "month"
            st.rerun()

    with col_btn5:
        if st.button("📅 All Time", use_container_width=True,
                    type="primary" if st.session_state.time_range_metrics == 'all' else "secondary"):
            st.session_state.start_date, st.session_state.end_date = ut.compute_date_range('all')
            st.session_state.time_range_metrics = 'all'
            st.session_state.granularity = "month"

            st.rerun()

    # Determine correct y-axis column depending on sport selected
    y_column = {
        "duration": "total_duration",
        "physical_reinforcement": "nb_trainings"
    }.get(st.session_state.sport, "total_distance")

    # Y-axis title
    y_title = {
        "duration": "Total Duration (min)",
        "physical_reinforcement": "Training Sessions",
    }.get(st.session_state.sport, "Distance (km)")


    if st.session_state.sport == 'duration':
        print('st.session_state.granularity', st.session_state.granularity)
        activity_duration_data = pd.read_sql(
            sql.get_activity_duration_by_granularity_query(
                st.session_state.start_date, 
                st.session_state.end_date,
                st.session_state.granularity
            ),
            conn
        )
        ut.plot_week_volume(
            activity_duration_data,
            st.session_state.granularity
        )
    # Use a unique key for the plotly chart
    else:
        # Récupération des données et affichage du graphique
        sport_data = pd.read_sql(sql.get_weekly_sport_query(st.session_state.sport, st.session_state.time_range_metrics), conn)
        ut.plot_week_area(
            running_data=sport_data,
            y_column=y_column,
            y_title=y_title,
            sport_name=st.session_state.sport,
            time_range_key=st.session_state.time_range_metrics
        )

           
    weekly_metrics = weekly_metrics[weekly_metrics['activityTypeGrouped'].isin(main_sports)].sort_values("activityTypeGrouped")
    for _, row in weekly_metrics.iterrows():
        sport = row["activityTypeGrouped"].capitalize().replace("_", " ")

        st.subheader(f"🏋️ {sport}")

        # Define the metrics for each sport
        metrics = [
            ("Duration", row["current_duration"], row["duration_delta"], ut.format_duration, ut.format_duration_delta),
            ("Distance (km)", row["current_distance"], row["distance_delta"], lambda x: ut.safe_format(x, "{:.2f}"), lambda x: ut.safe_format(x, "{:+.2f}")),
            ("Avg HR (bpm)", row["current_avg_hr"], row["avg_hr_delta"], lambda x: ut.safe_format(x, "{:.0f}"), lambda x: ut.safe_format(x, "{:+.0f}")),
            ("Avg Speed (km/h)", row["current_avg_speed"], row["avg_speed_delta"], lambda x: ut.safe_format(x, "{:.2f}"), lambda x: ut.safe_format(x, "{:+.2f}")),
            ("Elevation Gain (m)", row["current_total_elevation_gain"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
            ("Calories", row["current_total_calories"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
            ("Water (ml)", row["current_total_water_estimated"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
            ("Vigorous Intensity (min)", row["current_total_vigorous_intensity"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
        ]

        # Display metrics in 4 columns per row
        for i in range(0, len(metrics), 8):
            cols = st.columns(8)
            for j, (name, current, delta, fmt_cur, fmt_delta) in enumerate(metrics[i:i+8]):
                with cols[j]:
                    if pd.notna(current):
                        current_display = fmt_cur(current)
                        if delta is not None and pd.notna(delta):
                            delta_display = fmt_delta(delta)
                            st.metric(name, current_display, delta_display)
                        else:
                            st.metric(name, current_display)
                    else:
                        st.metric(name, "—")