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
from actions.power_curve import (
    POWER_CURVE_DURATIONS,
    duration_display_label,
    power_profile_from_fit,
    power_profile_from_telemetry,
)
import plotly.express as px
from plotly.subplots import make_subplots
from actions import utils as ut
from actions import utils_ui as ui
from actions.cycling_splits import (
    aggregate_selected_laps,
    aggregate_to_summary_row,
    laps_to_display_dataframe,
    parse_laps_field,
    split_label_for_index,
)
from utils.utils_gcp import check_gcs_path_exists, query_bigquery_live, read_csv_from_gcs, bucket


def _render_cycling_splits(activity_id: int) -> None:
    summary_df = query_bigquery_live(sql.get_workout_summary_detail_query(activity_id))
    if summary_df.empty:
        st.caption(
            "No lap splits in `workout_summaries` for this ride "
            "(race-prep window only — run backfill if needed)."
        )
        return

    row = summary_df.iloc[0]
    if row.get("parse_status") != "ok":
        st.caption(f"Splits unavailable (`parse_status`: {row.get('parse_status')}).")
        return

    laps = parse_laps_field(row.get("laps"))
    if not laps:
        st.caption("No lap rows stored for this activity.")
        return

    st.write("#### Splits")
    st.caption(
        "Pick splits in each list, then **Run**. Metrics are **duration-weighted**."
    )

    display_df = laps_to_display_dataframe(laps)
    st.dataframe(display_df, width="stretch", hide_index=True)

    lists_key = f"cy_split_list_count_{activity_id}"
    results_key = f"cy_split_results_data_{activity_id}"
    if lists_key not in st.session_state:
        st.session_state[lists_key] = 1

    split_options = list(range(len(laps)))
    split_labels = {i: split_label_for_index(laps, i) for i in split_options}

    def _picks_hash() -> tuple:
        return tuple(
            tuple(st.session_state.get(f"cy_split_pick_{activity_id}_{i}", []))
            for i in range(st.session_state[lists_key])
        )

    def _compute_result_rows() -> list[dict]:
        rows = []
        for list_idx in range(st.session_state[lists_key]):
            picked = st.session_state.get(f"cy_split_pick_{activity_id}_{list_idx}", [])
            if not picked:
                continue
            agg = aggregate_selected_laps(laps, picked)
            if not agg:
                continue
            labels = ", ".join(str(laps[i].get("split", i + 1)) for i in picked)
            rows.append(aggregate_to_summary_row(f"List {list_idx + 1}", labels, agg))
        return rows

    btn_cols = st.columns([1, 1, 1, 3])
    with btn_cols[0]:
        if st.button("Add list", key=f"cy_split_add_{activity_id}"):
            st.session_state[lists_key] += 1
            st.session_state.pop(results_key, None)
            st.rerun()
    with btn_cols[1]:
        if st.button("Reset", key=f"cy_split_reset_{activity_id}"):
            st.session_state[lists_key] = 1
            for key in list(st.session_state.keys()):
                if key.startswith(f"cy_split_pick_{activity_id}_"):
                    del st.session_state[key]
            st.session_state.pop(results_key, None)
            st.rerun()
    with btn_cols[2]:
        run_clicked = st.button("Run", type="primary", key=f"cy_split_run_{activity_id}")

    list_cols = st.columns(2)
    for list_idx in range(st.session_state[lists_key]):
        with list_cols[list_idx % 2]:
            st.multiselect(
                f"List {list_idx + 1}",
                options=split_options,
                format_func=lambda i, labels=split_labels: labels[i],
                key=f"cy_split_pick_{activity_id}_{list_idx}",
                placeholder="Select splits",
            )

    if run_clicked:
        st.session_state[results_key] = {
            "rows": _compute_result_rows(),
            "picks_hash": _picks_hash(),
        }

    stored = st.session_state.get(results_key)
    if not stored:
        return

    if stored.get("picks_hash") != _picks_hash():
        st.caption("Lists changed — click **Run** to update comparison.")
        return

    result_rows = stored.get("rows") or []
    if not result_rows:
        st.info("Select splits in at least one list, then click **Run**.")
        return

    st.markdown("**Comparison**")
    st.dataframe(pd.DataFrame(result_rows), width="stretch", hide_index=True)


def _render_power_profile(profile: dict) -> None:
    curve = profile["power_curve"]
    labels = [label for label in POWER_CURVE_DURATIONS if curve.get(label) is not None]
    if not labels:
        samples = profile.get("metadata", {}).get("sample_seconds", 0)
        st.info(
            f"No power curve for this activity ({samples} s of power data after resampling). "
            "Select a ride recorded with a power meter (outdoor PM or smart trainer)."
        )
        return

    values = [curve[label] for label in labels]
    theta = [duration_display_label(label) for label in labels]
    seconds = [POWER_CURVE_DURATIONS[label] for label in labels]

    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.write("#### Power profile (radar)")
        fig_radar = go.Figure(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=theta + [theta[0]],
                mode="lines+markers",
                name="Peak power",
                line=dict(color="#5b21b6", width=2),
                marker=dict(size=6, color="#5b21b6"),
                fill="toself",
                fillcolor="rgba(91, 33, 182, 0.15)",
                hovertemplate="%{theta}<br>%{r:.0f} W<extra></extra>",
            )
        )
        fig_radar.update_layout(
            height=420,
            template="plotly_white",
            polar=dict(
                radialaxis=dict(visible=True, gridcolor="rgba(0,0,0,0.08)"),
                angularaxis=dict(direction="clockwise", rotation=90, gridcolor="rgba(0,0,0,0.08)"),
            ),
            showlegend=False,
            margin=dict(l=40, r=40, t=30, b=30),
        )
        st.plotly_chart(fig_radar, width="stretch")

    with chart_cols[1]:
        st.write("#### Power curve")
        fig_curve = go.Figure(
            go.Scatter(
                x=seconds,
                y=values,
                mode="lines+markers",
                name="Peak power",
                line=dict(color="#5b21b6", width=2),
                marker=dict(size=7, color="#5b21b6"),
                hovertemplate="%{text}<br>%{y:.0f} W<extra></extra>",
                text=theta,
            )
        )
        fig_curve.update_layout(
            height=420,
            template="plotly_white",
            xaxis=dict(
                title="Duration",
                type="log",
                tickvals=seconds,
                ticktext=theta,
            ),
            yaxis=dict(title="Power (W)"),
            hovermode="x unified",
            margin=dict(l=40, r=20, t=30, b=40),
        )
        st.plotly_chart(fig_curve, width="stretch")


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
        
        paginated_df, selected_page_row, selected_row = ut.paginated_table(
            df=cycling_table,
            display_columns=display_columns,
            column_configuration=column_configuration,
            page_size=10,
            session_key="cycling_list"
        )
                
        if selected_row is not None:
            selected_row_data = paginated_df.iloc[selected_page_row]
            selected_row_id = int(cycling_table.iloc[selected_row]['activityId'])
            
            st.markdown(f"#### 🔎 Activity Details: {selected_row_data.get('Activity Name')}")
            
            m_cols = st.columns(4)
            with m_cols[0]: ui.metric_card("Distance", f"{selected_row_data.get('Distance (km)', 0):.2f} km", icon="📏")
            with m_cols[1]: ui.metric_card("Duration", selected_row_data.get('Duration', 0), icon="⏱️")
            with m_cols[2]: ui.metric_card("Avg HR", f"{selected_row_data.get('Avg HR', 0):.0f} bpm", icon="❤️")
            with m_cols[3]: ui.metric_card("Avg Speed", f"{selected_row_data.get('Avg Speed (km/h)', 0):.1f} km/h", icon="⚡")

            activity_month = datetime.strptime(str(selected_row_data["Day"]), "%Y-%m-%d").strftime("%Y-%m")
            gcs_base_path = f"data/raw/{activity_month}/{selected_row_id}"
            
            gpx_path = f"{gcs_base_path}/{selected_row_id}.gpx"
            st.caption("Route map is optional. Telemetry, power curve, and splits load independently.")
            if st.checkbox(
                "Show route map",
                value=False,
                key=f"cy_map_{selected_row_id}",
                help="GPX download + Folium map can slow the page on long rides.",
            ):
                if check_gcs_path_exists(gpx_path):
                    gpx_content = bucket.blob(gpx_path).download_as_bytes()
                    display_gpx_map(gpx_content)
                else:
                    st.caption("No GPX file for this activity.")

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

                fit_path = f"{gcs_base_path}/{selected_row_id}.fit"
                if check_gcs_path_exists(fit_path):
                    fit_content = bucket.blob(fit_path).download_as_bytes()
                    profile = power_profile_from_fit(fit_content)
                else:
                    profile = power_profile_from_telemetry(df_tcx["Time"], df_tcx["Watts"])

                _render_power_profile(profile)
            else:
                st.caption("No TCX file — telemetry and power curve unavailable for this activity.")

            _render_cycling_splits(selected_row_id)
    else:
        st.info("No cycling activities found.")
