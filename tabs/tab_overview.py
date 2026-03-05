import streamlit as st
import pandas as pd
from datetime import timedelta
from utils import sql_queries as sql 
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

    # ----- Initialize Global State -----
    if "sport" not in st.session_state:
        st.session_state.sport = "duration"
    if "granularity" not in st.session_state:
        st.session_state.granularity = "week"
    if "time_range_metrics" not in st.session_state:
        st.session_state.time_range_metrics = "4_units"
    if "start_date" not in st.session_state or "end_date" not in st.session_state:
        st.session_state.start_date, st.session_state.end_date = ut.compute_date_range(st.session_state.time_range_metrics)

    weekly_metrics_all = conn(
        sql.get_weekly_metrics_with_delta_query_overview()
    )

    # ----- Global totals for the top row -----
    week_total_duration = weekly_metrics_all["current_duration"].sum()
    last_week_total_duration = weekly_metrics_all["second_total_duration"].sum()
    week_nb_trainings = weekly_metrics_all["current_nb_trainings"].sum()
    last_week_nb_trainings = weekly_metrics_all["second_nb_trainings"].sum()

    # ----- Display Weekly Totals -----
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

    sport_display_map = {"swimming": "Swim", "cycling": "Bike", "running": "Run", "duration": "Overall"}
    sport_icon_map = {"swimming": "🏊‍♂️", "cycling": "🚴‍♂️", "running": "🏃‍♂️", "duration": "🎯"}

    # Ensure all main sports are shown even if 0
    main_sports_list = ["swimming", "cycling", "running"]
    for i, raw_sport in enumerate(main_sports_list):
        sport_data = weekly_metrics_all[weekly_metrics_all['activityTypeGrouped'] == raw_sport]
        
        if not sport_data.empty:
            row = sport_data.iloc[0]
            val = row["current_distance"]
            delta = row["distance_delta"]
        else:
            val = 0
            delta = 0
            
        sport_label = sport_display_map.get(raw_sport, raw_sport.capitalize())
        icon = sport_icon_map.get(raw_sport, "🎯")
        with cols[i+2]:
            ui.metric_card(
                f"{sport_label} (km)",
                ut.safe_format(val, "{:.2f}"),
                ut.safe_format(delta, "{:+.2f}"),
                icon=icon
            )
              
    st.markdown("---")

    # ----- Training Explorer Selectors -----
    st.write("### 🔍 Training Explorer")
    
    # Granularity Toggle (Week/Month)
    g_cols = st.columns(2)
    if g_cols[0].button("📅 Week", key="week_toggle_main", use_container_width=True, type="primary" if st.session_state.granularity == 'week' else "secondary"):
        st.session_state.granularity = 'week'
        st.rerun()
    if g_cols[1].button("📆 Month", key="month_toggle_main", use_container_width=True, type="primary" if st.session_state.granularity == 'month' else "secondary"):
        st.session_state.granularity = 'month'
        st.rerun()

    # Sport Toggle (Buttons)
    sport_options = ["duration", "swimming", "cycling", "running"]
    st.write("") # Spacer
    s_cols = st.columns(len(sport_options))
    for i, sport_opt in enumerate(sport_options):
        label = f"{sport_icon_map[sport_opt]} {sport_display_map[sport_opt]}"
        if s_cols[i].button(label, key=f"sport_btn_{sport_opt}", use_container_width=True, type="primary" if st.session_state.sport == sport_opt else "secondary"):
            st.session_state.sport = sport_opt
            st.rerun()

    period_label = "Week" if st.session_state.granularity == "week" else "Month"
              
    st.markdown("---")

    # ----- Volume Over Time Graph -----
    st.subheader(f"📈 {sport_display_map[st.session_state.sport]} Volume Over {period_label}s")
    
    tr_cols = st.columns(4)
    unit_label = "Weeks" if st.session_state.granularity == 'week' else "Months"
    ranges = [
        (f"4 {unit_label}", "4_units"), 
        (f"6 {unit_label}", "6_units"), 
        ("YTD", "ytd"), 
        ("All", "all")
    ]
    
    for i, (label, val) in enumerate(ranges):
        if tr_cols[i].button(label, key=f"tr_btn_{val}", use_container_width=True, type="primary" if st.session_state.time_range_metrics == val else "secondary"):
            st.session_state.time_range_metrics = val
            st.rerun()

    y_column = "total_duration" if st.session_state.sport == "duration" else "total_distance"
    y_title = "Total Duration (min)" if st.session_state.sport == "duration" else "Distance (km)"

    if st.session_state.sport == 'duration':
        sport_data = conn(sql.get_weekly_sport_query("duration", st.session_state.time_range_metrics, st.session_state.granularity))
        ut.plot_week_area(sport_data, "total_duration", "Total Duration (min)", "Overall", st.session_state.time_range_metrics)
    else:
        sport_data = conn(sql.get_weekly_sport_query(st.session_state.sport, st.session_state.time_range_metrics, st.session_state.granularity))
        ut.plot_week_area(sport_data, y_column, y_title, st.session_state.sport, st.session_state.time_range_metrics)

    st.markdown("---")

    # ----- Sport Performance & Breakdown (Merged) -----  
    st.subheader(f"📊 {sport_display_map[st.session_state.sport]} Performance & Breakdown")
    if st.session_state.sport == "duration":
        benchmarks = conn(sql.get_volume_metrics_query_overview(st.session_state.granularity))
    else:
        benchmarks = conn(sql.get_volume_metrics_query(st.session_state.sport, st.session_state.granularity))

    if not benchmarks.empty:
        dict_columns = {
            "last_1": f"Last {period_label}", 
            "last_4": f"Last 4 {period_label}s", 
            "last_12": f"Last 12 {period_label}s", 
            "last_all": "Year to Date"
        }
        
        main_sports = ["swimming", "cycling", "running"]
        sports_to_show = main_sports if st.session_state.sport == "duration" else [st.session_state.sport]
        weekly_metrics_filtered = weekly_metrics_all[weekly_metrics_all['activityTypeGrouped'].isin(sports_to_show)]

        for name_i, title in dict_columns.items():
            bench_filtered = benchmarks[benchmarks['name'] == name_i]
            if not bench_filtered.empty:
                is_last_one = (name_i == "last_1")
                with st.expander(f"📈 {title} Summary", expanded=is_last_one):
                    # Benchmark metrics
                    m_cols = st.columns(4)
                    dist = bench_filtered['distance_total'].fillna(0).iloc[0]
                    dur = bench_filtered['duration_total'].fillna(0).iloc[0]
                    trainings = bench_filtered['nb_trainings'].fillna(0).iloc[0]
                    
                    m_cols[0].metric("Distance (Total)", f"{dist:.1f} km")
                    m_cols[1].metric("Duration (Total)", ut.format_duration_no_days(dur))
                    m_cols[2].metric("Sessions", f"{trainings:.0f}")
                    
                    if st.session_state.sport == "swimming":
                        strokes = bench_filtered['totalNumberOfStrokes'].fillna(0).iloc[0]
                        m_cols[3].metric("Total Strokes", f"{strokes:,.0f}")
                    else:
                        elev = bench_filtered['elevationGain'].fillna(0).iloc[0]
                        m_cols[3].metric("Elevation Gain", f"{elev:.0f} m")

                    # Show Detailed Breakdown for the latest period for comparison
                    if not weekly_metrics_filtered.empty:
                        st.markdown("---")
                        st.write(f"**Detailed Breakdown (Latest {period_label})**" if not is_last_one else "**Detailed Breakdown**")
                        
                        for _, row in weekly_metrics_filtered.iterrows():
                            raw_sport_row = row["activityTypeGrouped"]
                            sport_row_label = sport_display_map.get(raw_sport_row, raw_sport_row.capitalize())
                            icon_row = sport_icon_map.get(raw_sport_row, "🎯")
                            
                            st.markdown(f"#### {icon_row} {sport_row_label}")
                            
                            metrics = [
                                ("Duration", row["current_duration"], row["duration_delta"], ut.format_duration, ut.format_duration_delta),
                                ("Distance (km)", row["current_distance"], row["distance_delta"], lambda x: ut.safe_format(x, "{:.2f}"), lambda x: ut.safe_format(x, "{:+.2f}")),
                                ("Avg HR (bpm)", row["current_avg_hr"], row["avg_hr_delta"], lambda x: ut.safe_format(x, "{:.0f}"), lambda x: ut.safe_format(x, "{:+.0f}")),
                                ("Avg Speed", row["current_avg_speed"], row["avg_speed_delta"], lambda x: ut.safe_format(x, "{:.1f}"), lambda x: ut.safe_format(x, "{:+.1f}")),
                                ("Elevation", row["current_total_elevation_gain"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
                                ("Calories", row["current_total_calories"], None, lambda x: ut.safe_format(x, "{:.0f}"), None),
                            ]
                            
                            # Create 6 columns for the 6 metrics to keep the sport on one row
                            metric_cols = st.columns(6)
                            for j, (name, current, delta, fmt_cur, fmt_delta) in enumerate(metrics):
                                with metric_cols[j]:
                                    if pd.notna(current):
                                        st.metric(name, fmt_cur(current), fmt_delta(delta) if delta is not None and pd.notna(delta) else None)
                                    else:
                                        st.metric(name, "—")
                            st.markdown("<br>", unsafe_allow_html=True)
