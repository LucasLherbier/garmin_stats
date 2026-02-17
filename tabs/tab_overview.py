import streamlit as st
import pandas as pd
from datetime import timedelta
import sql_queries as sql 
import plotly.express as px
import uuid
from actions import utils as ut
from actions import utils_ui as ui

def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def show(conn):
    st.title("🏁 Weekly Overview")
    st.markdown("A snapshot of my activity and progress over the last week.")

    weekly_metrics = conn(
        sql.get_weekly_metrics_with_delta_query_overview()
    )

    # ----- Global totals -----
    week_total_duration = weekly_metrics["current_duration"].sum()
    last_week_total_duration = weekly_metrics["second_total_duration"].sum()

    week_nb_trainings = weekly_metrics["current_nb_trainings"].sum()
    last_week_nb_trainings = weekly_metrics["second_nb_trainings"].sum()

    # ----- Ordered sports -----
    all_sports_columns = weekly_metrics['activityTypeGrouped'].unique()
    main_sports = ["swimming", "cycling", "running", "physical_reinforcement"] 
    weekly_metrics["activityTypeGrouped"] = pd.Categorical(
        weekly_metrics["activityTypeGrouped"], categories=main_sports, ordered=True
    )
    weekly_main_stats = weekly_metrics[weekly_metrics['activityTypeGrouped'].isin(["swimming", "cycling", "running"])].sort_values("activityTypeGrouped")
    
    # ----- Display totals -----
    st.write("### Weekly Totals")
    cols = st.columns(5)
    
    with cols[0]:
        ui.metric_card(
            "Total Duration", 
            ut.format_duration(week_total_duration), 
            ut.format_duration(week_total_duration - last_week_total_duration),
            icon="⏱️"
        )
    with cols[1]:
        ui.metric_card(
            "Total Trainings", 
            f"{week_nb_trainings:.0f}", 
            f"{week_nb_trainings - last_week_nb_trainings:+.0f}",
            icon="🏋️"
        )

    sport_display_map = {"swimming": "Swim", "cycling": "Bike", "running": "Run"}
    for i, (_, row) in enumerate(weekly_main_stats.iterrows()):
        raw_sport = row["activityTypeGrouped"]
        sport = sport_display_map.get(raw_sport, raw_sport.capitalize().replace("_", " "))
        icon = {"Swim": "🏊‍♂️", "Bike": "🚴‍♂️", "Run": "🏃‍♂️"}.get(sport, "🎯")
        with cols[i+2]:
            ui.metric_card(
                f"{sport} (km)",
                ut.safe_format(row["current_distance"], "{:.2f}"),
                ut.safe_format(row["distance_delta"], "{:+.2f}"),
                icon=icon
            )
              
    st.markdown("---")
              
    # ----- Display Metrics as Table -----  
    st.header("Weekly Metrics by Sport")
    race_metrics = conn(sql.get_volume_metrics_query_overview())

    if not race_metrics.empty:
        dict_columns = {"last_1":"Last week", "last_4":"Last 4 weeks", "last_12":"Last 12 weeks", "last_18":"Last 18 weeks", "last_all": "Year to Date"}
        
        # Display as a clean list of cards or a styled dataframe
        for name_i, title in dict_columns.items():
            race_metrics_filtered = race_metrics[race_metrics['name'] == name_i]
            if not race_metrics_filtered.empty:
                with st.expander(f"📊 {title} Details", expanded=(name_i == "last_1")):
                    m_cols = st.columns(4)
                    m_cols[0].metric("Distance (Total)", f"{race_metrics_filtered['distance_total'].item() or 0:.1f} km")
                    m_cols[1].metric("Duration (Total)", ut.format_duration_no_days(race_metrics_filtered['duration_total'].item()))
                    m_cols[2].metric("Trainings", f"{race_metrics_filtered['nb_trainings'].item() or 0:.0f}")
                    m_cols[3].metric("Avg HR", f"{race_metrics_filtered['averageHR'].item() or 0:.0f} bpm")

    st.markdown("---")

    st.subheader("Volume Over Time")
    sport_options = ["duration", "swimming", "cycling", "running", "physical_reinforcement"]
    sport_labels = {"duration": "Overall", "swimming": "🏊‍♂️ Swim", "cycling": "🚴‍♂️ Bike", "running": "🏃‍♂️ Run", "physical_reinforcement": "🏋️ Strength"}
    
    # Selection Row
    scol1, scol2 = st.columns([1, 2])
    with scol1:
        if "sport" not in st.session_state:
            st.session_state.sport = "duration"
        st.session_state.sport = st.selectbox(
            "Select Activity", 
            sport_options, 
            index=sport_options.index(st.session_state.sport),
            format_func=lambda x: sport_labels.get(x, x.capitalize())
        )
    
    with scol2:
        # Initialize session state if not exists
        if "time_range_metrics" not in st.session_state:
            st.session_state.time_range_metrics = "8_weeks"
        if "start_date" not in st.session_state or "end_date" not in st.session_state:
            st.session_state.start_date, st.session_state.end_date = ut.compute_date_range(st.session_state.time_range_metrics)
        if "granularity" not in st.session_state:
            st.session_state.granularity = "week"
            
        tr_cols = st.columns(4)
        ranges = [("8 Weeks", "8_weeks", "week"), ("6 Months", "6_months", "month"), ("YTD", "ytd", "month"), ("All Time", "all", "month")]
        for i, (label, val, gran) in enumerate(ranges):
            if tr_cols[i].button(label, use_container_width=True, type="primary" if st.session_state.time_range_metrics == val else "secondary"):
                st.session_state.start_date, st.session_state.end_date = ut.compute_date_range(val)
                st.session_state.time_range_metrics = val
                st.session_state.granularity = gran
                st.rerun()

    # Determine correct y-axis column
    y_column = {"duration": "total_duration", "physical_reinforcement": "nb_trainings"}.get(st.session_state.sport, "total_distance")
    y_title = {"duration": "Total Duration (min)", "physical_reinforcement": "Training Sessions"}.get(st.session_state.sport, "Distance (km)")

    if st.session_state.sport == 'duration':
        activity_duration_data = conn(sql.get_activity_duration_by_granularity_query(st.session_state.start_date, st.session_state.end_date, st.session_state.granularity))
        ut.plot_week_volume(activity_duration_data, st.session_state.granularity)
    else:
        sport_data = conn(sql.get_weekly_sport_query(st.session_state.sport, st.session_state.time_range_metrics))
        ut.plot_week_area(sport_data, y_column, y_title, st.session_state.sport, st.session_state.time_range_metrics)

    st.markdown("---")
    
    st.header("Detailed Sport Breakdown")
    weekly_metrics_filtered = weekly_metrics[weekly_metrics['activityTypeGrouped'].isin(main_sports)].sort_values("activityTypeGrouped")
    
    for _, row in weekly_metrics_filtered.iterrows():
        raw_sport = row["activityTypeGrouped"]
        sport = sport_display_map.get(raw_sport, raw_sport.capitalize().replace("_", " "))
        icon = {"Swim": "🏊‍♂️", "Bike": "🚴‍♂️", "Run": "🏃‍♂️"}.get(sport, "🏋️")
        with st.expander(f"{icon} {sport} Performance", expanded=False):
            metrics = [
                ("Duration", row["current_duration"], row["duration_delta"], ut.format_duration, ut.format_duration_delta),
                ("Distance (km)", row["current_distance"], row["distance_delta"], lambda x: ut.safe_format(x, "{:.2f}"), lambda x: ut.safe_format(x, "{:+.2f}")),
                ("Avg HR (bpm)", row["current_avg_hr"], row["avg_hr_delta"], lambda x: ut.safe_format(x, "{:.0f}"), lambda x: ut.safe_format(x, "{:+.0f}")),
                ("Avg Speed", row["current_avg_speed"], row["avg_speed_delta"], lambda x: ut.safe_format(x, "{:.1f}"), lambda x: ut.safe_format(x, "{:+.1f}")),
                ("Elevation", row["current_total_elevation_gain"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
                ("Calories", row["current_total_calories"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
            ]
            
            m_cols = st.columns(3)
            for j, (name, current, delta, fmt_cur, fmt_delta) in enumerate(metrics):
                with m_cols[j % 3]:
                    if pd.notna(current):
                        st.metric(name, fmt_cur(current), fmt_delta(delta) if delta is not None and pd.notna(delta) else None)
                    else:
                        st.metric(name, "—")
