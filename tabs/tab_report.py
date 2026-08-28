import os
import secrets

import streamlit as st
import pandas as pd
from datetime import date

from utils import sql_queries as sql
from utils.utils_gcp import (
    query_bigquery_live,
    check_gcs_path_exists,
    bucket,
    publish_report_html,
    REPORT_SHARE_EXPIRY_DAYS,
)
from utils.github_actions import trigger_weekly_sync
from actions.parse_tcx_csv import parse_tcx_to_dataframe
from actions.power_curve import power_profile_from_fit, power_profile_from_telemetry
from actions.activity_splits import (
    aggregate_selected_laps,
    aggregate_to_summary_row,
    laps_to_display_dataframe,
    parse_laps_field,
    resolve_sport,
    split_label_for_index,
)
from actions.report_html import build_activity_report_html, build_list_aggregates
from actions.report_map import gpx_track_points


def _verify_sync_password(password: str) -> str | None:
    expected = os.getenv("UPLOAD_TO_GITHUB", "").strip()
    if not expected:
        return "Sync is not configured. Set UPLOAD_TO_GITHUB in the environment."
    if not secrets.compare_digest(password, expected):
        return "Incorrect password."
    return None


def _render_upload_section() -> None:
    st.markdown("### Sync data")
    st.caption("Trigger the weekly Garmin extract + workout summaries on GitHub Actions.")

    sync_password = st.text_input("Sync password", type="password", key="report_sync_password")

    if st.button("Upload / Sync", type="primary", key="report_trigger_sync"):
        error = _verify_sync_password(sync_password)
        if error:
            st.error(error)
        else:
            st.session_state.report_show_upload_confirm = True

    if st.session_state.get("report_upload_message"):
        if st.session_state.get("report_upload_ok"):
            st.success(st.session_state.report_upload_message)
        else:
            st.error(st.session_state.report_upload_message)
        if st.session_state.get("report_upload_url"):
            st.markdown(f"[View workflow runs]({st.session_state.report_upload_url})")
        del st.session_state["report_upload_message"]
        del st.session_state["report_upload_ok"]
        if "report_upload_url" in st.session_state:
            del st.session_state["report_upload_url"]

    if st.session_state.get("report_show_upload_confirm"):
        st.warning(
            "Start a Garmin sync on GitHub Actions? "
            "This extracts the last ~2 weeks of activities and rebuilds workout summaries."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm sync", type="primary", key="report_confirm_sync"):
                error = _verify_sync_password(st.session_state.get("report_sync_password", ""))
                st.session_state.report_show_upload_confirm = False
                if error:
                    st.session_state.report_upload_ok = False
                    st.session_state.report_upload_message = error
                else:
                    result = trigger_weekly_sync()
                    st.session_state.report_upload_ok = result.ok
                    st.session_state.report_upload_message = result.message
                    if result.ok:
                        st.session_state.report_upload_url = result.workflow_url
                st.rerun()
        with c2:
            if st.button("Cancel", key="report_cancel_sync"):
                st.session_state.report_show_upload_confirm = False
                st.rerun()


def _render_split_picker(activity_id: int, laps: list[dict], sport: str) -> list[dict[str, str]] | None:
    st.write("#### Split lists")
    st.caption("Pick splits in each list, then **Run**. Metrics are **duration-weighted** (not a simple split average).")

    display_df = laps_to_display_dataframe(laps, sport)
    st.dataframe(display_df, width="stretch", hide_index=True)

    prefix = f"report_{activity_id}"
    lists_key = f"{prefix}_split_list_count"
    results_key = f"{prefix}_split_results"
    if lists_key not in st.session_state:
        st.session_state[lists_key] = 1

    split_options = list(range(len(laps)))
    split_labels = {i: split_label_for_index(laps, i) for i in split_options}

    def _picks_hash() -> tuple:
        return tuple(
            tuple(st.session_state.get(f"{prefix}_pick_{i}", []))
            for i in range(st.session_state[lists_key])
        )

    def _compute_result_rows() -> list[dict]:
        rows = []
        for list_idx in range(st.session_state[lists_key]):
            picked = st.session_state.get(f"{prefix}_pick_{list_idx}", [])
            if not picked:
                continue
            agg = aggregate_selected_laps(laps, picked, sport)
            if not agg:
                continue
            labels = ", ".join(str(laps[i].get("split", i + 1)) for i in picked)
            rows.append(aggregate_to_summary_row(f"List {list_idx + 1}", labels, agg, sport))
        return rows

    btn_cols = st.columns([1, 1, 1, 3])
    with btn_cols[0]:
        if st.button("Add list", key=f"{prefix}_add"):
            st.session_state[lists_key] += 1
            st.session_state.pop(results_key, None)
            st.rerun()
    with btn_cols[1]:
        if st.button("Reset", key=f"{prefix}_reset"):
            st.session_state[lists_key] = 1
            for key in list(st.session_state.keys()):
                if key.startswith(f"{prefix}_pick_"):
                    del st.session_state[key]
            st.session_state.pop(results_key, None)
            st.rerun()
    with btn_cols[2]:
        run_clicked = st.button("Run", type="primary", key=f"{prefix}_run")

    list_cols = st.columns(2)
    list_names: list[str] = []
    for list_idx in range(st.session_state[lists_key]):
        with list_cols[list_idx % 2]:
            st.multiselect(
                f"List {list_idx + 1}",
                options=split_options,
                format_func=lambda i, labels=split_labels: labels[i],
                key=f"{prefix}_pick_{list_idx}",
                placeholder="Select splits",
            )
            list_names.append(
                st.text_input(
                    f"List {list_idx + 1} name",
                    value=f"List {list_idx + 1}",
                    key=f"{prefix}_name_{list_idx}",
                    label_visibility="collapsed",
                    placeholder=f"List {list_idx + 1} name",
                )
            )

    if run_clicked:
        st.session_state[results_key] = {
            "rows": _compute_result_rows(),
            "picks_hash": _picks_hash(),
            "picks": _picks_hash(),
        }

    stored = st.session_state.get(results_key)
    if not stored:
        return None

    if stored.get("picks_hash") != _picks_hash():
        st.caption("Lists changed — click **Run** to update comparison.")
        return stored.get("rows")

    result_rows = stored.get("rows") or []
    if not result_rows:
        st.info("Select splits in at least one list, then click **Run**.")
        return None

    st.markdown("**Comparison**")
    st.dataframe(pd.DataFrame(result_rows), width="stretch", hide_index=True)
    return result_rows


def _current_list_picks(activity_id: int) -> tuple[list[list[int]], list[str]]:
    prefix = f"report_{activity_id}"
    lists_key = f"{prefix}_split_list_count"
    count = st.session_state.get(lists_key, 1)
    picks = []
    names = []
    for list_idx in range(count):
        picked = st.session_state.get(f"{prefix}_pick_{list_idx}", [])
        if picked:
            picks.append(picked)
            names.append(st.session_state.get(f"{prefix}_name_{list_idx}", f"List {list_idx + 1}"))
    return picks, names


def _publish_report_share(html: str, activity_id: int, date_str: str) -> None:
    share_state_key = f"report_share_{activity_id}"
    if not bucket:
        st.session_state[share_state_key] = {"error": "GCS bucket not configured."}
        return
    share_url = publish_report_html(html, activity_id, date_str)
    if share_url:
        st.session_state[share_state_key] = {"url": share_url}
    else:
        st.session_state[share_state_key] = {
            "error": "Could not publish report. Check GCS credentials."
        }


def _load_report_assets(activity_id: int, activity_day, sport: str) -> tuple[dict | None, object, list | None]:
    """Load power profile, HR series, and GPX track from GCS when available."""
    activity_month = pd.to_datetime(activity_day).strftime("%Y-%m")
    base = f"data/raw/{activity_month}/{activity_id}"
    power_profile = None
    hr_series = None
    track_points = None

    if not bucket:
        return None, None, None

    gpx_path = f"{base}/{activity_id}.gpx"
    tcx_path = f"{base}/{activity_id}.tcx"
    fit_path = f"{base}/{activity_id}.fit"

    try:
        if check_gcs_path_exists(gpx_path):
            gpx_content = bucket.blob(gpx_path).download_as_bytes()
            track_points = gpx_track_points(gpx_content)

        if check_gcs_path_exists(tcx_path):
            tcx_content = bucket.blob(tcx_path).download_as_bytes()
            df_tcx = parse_tcx_to_dataframe(tcx_content)
            if "HeartRate" in df_tcx.columns:
                hr_series = df_tcx["HeartRate"]
            if sport == "cycling":
                if check_gcs_path_exists(fit_path):
                    fit_content = bucket.blob(fit_path).download_as_bytes()
                    power_profile = power_profile_from_fit(fit_content)
                elif "Watts" in df_tcx.columns:
                    power_profile = power_profile_from_telemetry(df_tcx["Time"], df_tcx["Watts"])
    except Exception:
        pass

    return power_profile, hr_series, track_points


def show(conn) -> None:
    st.title("📋 Activity Report")
    st.markdown("Build a mobile-friendly HTML report from your activities and lap splits.")

    _render_upload_section()
    st.markdown("---")

    st.markdown("### 1. Select date")
    selected_date = st.date_input(
        "Activity date",
        value=date.today(),
        key="report_selected_date",
        label_visibility="collapsed",
    )
    date_str = selected_date.strftime("%Y-%m-%d")

    activities_df = query_bigquery_live(sql.get_activities_by_date_query(date_str))
    if activities_df.empty:
        st.info(f"No activities on {date_str}.")
        return

    st.markdown("### 2. Select activity")
    activities_df = activities_df.copy()
    activities_df["start_display"] = pd.to_datetime(activities_df["startTimeLocal"]).dt.strftime("%H:%M")
    activities_df["label"] = activities_df.apply(
        lambda row: (
            f"{row['start_display']} · {row.get('activityName') or 'Activity'} "
            f"({row.get('activityTypeGrouped', '?')})"
        ),
        axis=1,
    )

    activity_labels = activities_df["label"].tolist()
    selected_label = st.selectbox(
        "Activities on this date",
        options=activity_labels,
        key="report_activity_select",
        label_visibility="collapsed",
    )
    activity_row = activities_df[activities_df["label"] == selected_label].iloc[0]
    activity_id = int(activity_row["activityId"])

    detail_df = query_bigquery_live(sql.get_activity_report_query(activity_id))
    if detail_df.empty:
        st.error("Could not load activity details.")
        return

    detail = detail_df.iloc[0]
    sport = resolve_sport(detail)
    sport_icon = {"running": "🏃", "cycling": "🚴", "swimming": "🏊"}.get(sport, "⌚")
    st.caption(f"{sport_icon} {sport.title()} · ID {activity_id}")

    laps = parse_laps_field(detail.get("laps"))
    parse_status = detail.get("parse_status")
    if parse_status and str(parse_status) != "ok":
        st.warning(f"Lap splits unavailable (`parse_status`: {parse_status}). Report will use activity totals only.")
    elif not laps:
        st.info("No lap data for this activity. You can still generate a summary report.")

    list_aggregates = None
    if laps:
        _render_split_picker(activity_id, laps, sport)

    st.markdown("---")
    st.markdown("### 3. Generate report")

    list_picks, list_names = _current_list_picks(activity_id) if laps else ([], [])
    if list_picks:
        list_aggregates = build_list_aggregates(laps, list_picks, sport, list_names=list_names)

    power_profile, hr_series, track_points = _load_report_assets(
        activity_id, detail.get("startTimeLocal"), sport
    )

    html_doc = build_activity_report_html(
        detail,
        laps,
        list_aggregates=list_aggregates,
        power_profile=power_profile,
        hr_series=hr_series,
        track_points=track_points,
    )
    filename = f"report_{activity_id}_{date_str}.html"

    with st.expander("Preview HTML", expanded=False):
        st.components.v1.html(html_doc, height=720, scrolling=True)

    st.download_button(
        label="Create share link / Download",
        data=html_doc,
        file_name=filename,
        mime="text/html",
        type="primary",
        key=f"report_share_download_{activity_id}",
        on_click=_publish_report_share,
        args=(html_doc, activity_id, date_str),
        use_container_width=True,
    )

    share_state = st.session_state.get(f"report_share_{activity_id}")
    if share_state:
        if share_state.get("error"):
            st.error(share_state["error"])
        elif share_state.get("url"):
            st.success(f"Share link (valid {REPORT_SHARE_EXPIRY_DAYS} days) — send to friends:")
            st.link_button("Open shared report", share_state["url"], use_container_width=True)
            st.code(share_state["url"], language=None)
