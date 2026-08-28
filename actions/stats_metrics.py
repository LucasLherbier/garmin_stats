"""All-time stats metrics (ported from tabs/tab_stats.py, no Streamlit)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from actions import utils as ut


def longest_period_metric(df: pd.DataFrame, metric: str, period: str):
    if df.empty:
        return 0, "N/A", []
    agg = df.groupby(period, as_index=False)[metric].sum()
    if agg.empty:
        return 0, "N/A", []
    row = agg.loc[agg[metric].idxmax()]
    matching_rows_df = df[df[period] == row[period]]
    matching_activity_ids = matching_rows_df["activityId"].tolist()
    return row[metric], row[period], matching_activity_ids


def longest_single_activity(df: pd.DataFrame, metric: str):
    if df.empty or df[metric].dropna().empty:
        return None, None, None
    row = df.loc[df[metric].idxmax()]
    date = row["startTimeLocal"]
    return row[metric], (date.date() if pd.notna(date) else None), row["activityId"]


def _format_record_value(sport_name: str, metric_name: str, value) -> str:
    is_bike = "Bike" in sport_name
    dist_fmt = "{:.0f} km" if is_bike else "{:.2f} km"
    if metric_name == "duration":
        return ut.format_duration(value)
    return dist_fmt.format(value)


def _format_period_value(sport_name: str, metric_name: str, value) -> str:
    is_bike = "Bike" in sport_name
    dist_fmt = "{:.0f} km" if is_bike else "{:.2f} km"
    if metric_name == "duration":
        return ut.format_duration_no_days(value)
    return dist_fmt.format(value)


def sport_volume_records(sport_name: str, df: pd.DataFrame, metric_name: str) -> dict[str, Any]:
    info_dic: dict[str, list] = {"Day": [], "Week": [], "Month": [], "Year": []}
    day_val, day_period, info_dic["Day"] = longest_period_metric(df, metric_name, "Day")
    week_val, week_period, info_dic["Week"] = longest_period_metric(df, metric_name, "Week")
    month_val, month_period, _ = longest_period_metric(df, metric_name, "Month")
    year_val, year_period, _ = longest_period_metric(df, metric_name, "Year")

    cards = [
        {
            "label": "Longest Day",
            "value": _format_record_value(sport_name, metric_name, day_val),
            "period": str(day_period),
            "icon": "☀️",
        },
        {
            "label": "Longest Week",
            "value": _format_period_value(sport_name, metric_name, week_val),
            "period": str(week_period),
            "icon": "📅",
        },
        {
            "label": "Longest Month",
            "value": _format_period_value(sport_name, metric_name, month_val),
            "period": str(month_period),
            "icon": "🗓️",
        },
        {
            "label": "Longest Year",
            "value": _format_period_value(sport_name, metric_name, year_val),
            "period": str(year_period),
            "icon": "🏆",
        },
    ]

    df_list = []
    for key, ids in info_dic.items():
        if not ids:
            continue
        df_key = df[df["activityId"].isin(ids)].copy()
        df_key["period"] = key
        df_list.append(df_key)

    detail_rows = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()
    return {"sport_name": sport_name, "cards": cards, "detail_rows": detail_rows}


def sport_best_records(sport_name: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    speed, speed_date, _ = longest_single_activity(df, "averageSpeed")
    elev, elev_date, _ = longest_single_activity(df, "elevationGain")
    hr, hr_date, _ = longest_single_activity(df, "averageHR")
    cal, cal_date, _ = longest_single_activity(df, "calories")
    dist_val, dist_date, _ = longest_single_activity(df, "distance")
    dur_val, dur_date, _ = longest_single_activity(df, "duration")

    is_bike = "Bike" in sport_name
    is_run = "Run" in sport_name

    records: list[dict[str, Any]] = [
        {
            "label": "Fastest Speed",
            "value": f"{speed:.0f} km/h" if is_bike and speed is not None else (
                f"{speed:.1f} km/h" if speed is not None else "N/A"
            ),
            "date": str(speed_date) if speed_date else "",
            "icon": "⚡",
        },
        {
            "label": "Longest Distance",
            "value": (
                f"{dist_val:.0f} km" if is_bike and dist_val is not None else
                f"{dist_val:.2f} km" if dist_val is not None else "N/A"
            ),
            "date": str(dist_date) if dist_date else "",
            "icon": "📏",
        },
        {
            "label": "Longest Duration",
            "value": ut.format_duration_no_days(dur_val) if dur_val is not None else "N/A",
            "date": str(dur_date) if dur_date else "",
            "icon": "⏱️",
        },
    ]

    if is_run:
        if speed and speed > 0:
            pace_min = 60 / speed
            p_m, p_s = divmod(int(pace_min * 60), 60)
            pace_str = f"{p_m}:{p_s:02d} /km"
            records.append(
                {"label": "Fastest Pace", "value": pace_str, "date": str(speed_date), "icon": "🏃‍♂️"}
            )
        else:
            records.append({"label": "Fastest Pace", "value": "N/A", "date": "", "icon": "🏃‍♂️"})
    else:
        temp, temp_date, _ = longest_single_activity(df, "averageTemperature")
        records.append(
            {
                "label": "Max Temp",
                "value": f"{temp:.1f}°C" if temp is not None else "N/A",
                "date": str(temp_date) if temp_date else "",
                "icon": "🌡️",
            }
        )

    records.extend(
        [
            {
                "label": "Max Elevation",
                "value": f"{elev:.0f} m" if elev is not None else "N/A",
                "date": str(elev_date) if elev_date else "",
                "icon": "⛰️",
            },
            {
                "label": "Avg HR",
                "value": f"{hr:.0f} bpm" if hr is not None else "N/A",
                "date": str(hr_date) if hr_date else "",
                "icon": "❤️",
            },
            {
                "label": "Calories",
                "value": f"{cal:.0f} cal" if cal is not None else "N/A",
                "date": str(cal_date) if cal_date else "",
                "icon": "🔥",
            },
        ]
    )
    return records


def build_stats_payload(df_stats: pd.DataFrame, metric_choice: str = "duration") -> dict[str, Any]:
    if df_stats.empty or "startTimeLocal" not in df_stats.columns:
        return {"best_records": [], "volume_records": [], "summary_rows": []}

    df_stats = df_stats.copy()
    df_stats["startTimeLocal"] = pd.to_datetime(df_stats["startTimeLocal"], errors="coerce")

    sports = {
        "🏃‍♂️ Run": df_stats[df_stats["activityTypeGrouped"] == "running"],
        "🚴‍♂️ Bike": df_stats[df_stats["activityTypeGrouped"] == "cycling"],
        "🏊‍♂️ Swim": df_stats[df_stats["activityTypeGrouped"] == "swimming"],
    }

    best_records = []
    volume_records = []
    summary_parts = []

    sport_label_map = {"running": "Run", "cycling": "Bike", "swimming": "Swim"}

    for sport_name, df_sport in sports.items():
        if df_sport.empty:
            continue
        best_records.append({"sport_name": sport_name, "records": sport_best_records(sport_name, df_sport)})
        vol = sport_volume_records(sport_name, df_sport, metric_choice)
        volume_records.append({"sport_name": sport_name, "cards": vol["cards"]})
        if not vol["detail_rows"].empty:
            summary_parts.append(vol["detail_rows"])

    summary_rows: list[dict[str, Any]] = []
    if summary_parts:
        summary_df = pd.concat(summary_parts, ignore_index=True)
        summary_df["Label"] = (
            "Longest "
            + summary_df["period"].str.title()
            + " "
            + summary_df["activityTypeGrouped"].map(lambda x: sport_label_map.get(x, str(x).capitalize()))
        )
        summary_df = summary_df.copy()
        summary_df["duration"] = summary_df["duration"].apply(ut.format_duration_no_days)
        for _, row in summary_df.sort_values("Label").iterrows():
            summary_rows.append(
                {
                    "label": row["Label"],
                    "activityId": int(row["activityId"]),
                    "activityName": row.get("activityName"),
                    "locationName": row.get("locationName"),
                    "day": str(row.get("Day", ""))[:10],
                    "distance": float(row.get("distance") or 0),
                    "duration": row.get("duration"),
                    "averageHR": float(row.get("averageHR") or 0),
                    "averageSpeed": float(row.get("averageSpeed") or 0),
                    "elevationGain": float(row.get("elevationGain") or 0),
                    "calories": float(row.get("calories") or 0),
                }
            )

    return {
        "metric_choice": metric_choice,
        "best_records": best_records,
        "volume_records": volume_records,
        "summary_rows": summary_rows,
    }
