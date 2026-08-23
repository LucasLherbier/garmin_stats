"""Mobile-friendly HTML activity reports — Strava-inspired layouts."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import pandas as pd

from actions.activity_splits import aggregate_selected_laps, resolve_sport
from actions.report_charts import (
    LIST_COLORS,
    hr_zone_seconds_from_laps,
    svg_bike_np_splits_table,
    svg_hr_zones,
    svg_hr_zones_from_seconds,
    svg_pace_workout_chart,
    svg_power_curve,
    svg_power_skills,
    svg_run_list_splits_table,
    svg_run_splits_table,
    svg_swim_splits_table,
)
from actions.report_map import LEAFLET_HEAD, html_route_map
from utils.pipeline.workout_summaries.parse_laps import format_duration, format_pace


STRAVA_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: #fff;
  color: #2d2d2d;
  -webkit-font-smoothing: antialiased;
}
.phone {
  max-width: 430px;
  width: 100%;
  margin: 0 auto;
  background: #fff;
  min-height: 100vh;
}
.intro-top {
  padding: 16px 16px 12px;
}
.intro-top h1 {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.25;
  color: #1a1a1a;
}
.intro-meta {
  padding: 12px 16px 10px;
  border-bottom: 1px solid #e8e8e8;
}
.map-wrap { width: 100%; line-height: 0; background: #eceae4; }
.route-map-leaflet { z-index: 0; }
.leaflet-control-attribution { font-size: 9px !important; }
.intro-meta .location {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 2px;
}
.intro-meta .when {
  font-size: 13px;
  color: #666;
}
.intro-meta .effect {
  font-size: 14px;
  font-weight: 600;
  color: #fc5200;
  margin-top: 6px;
}
.intro-meta .structure {
  font-size: 13px;
  line-height: 1.45;
  color: #444;
  margin-top: 6px;
}
.workout-block {
  padding: 0 16px 16px;
  font-size: 14px;
  line-height: 1.55;
  color: #444;
  white-space: pre-wrap;
}
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid #e8e8e8;
  border-bottom: 1px solid #e8e8e8;
}
.metric {
  padding: 14px 16px;
  border-bottom: 1px solid #e8e8e8;
  border-right: 1px solid #e8e8e8;
  text-align: center;
}
.metric:nth-child(2n) { border-right: none; }
.metric:nth-last-child(-n+2):nth-child(odd),
.metric:nth-last-child(1):nth-child(even) { border-bottom: none; }
.metric:nth-last-child(1):nth-child(odd) { border-bottom: none; }
.metrics-grid.three-col { grid-template-columns: 1fr 1fr 1fr; }
.metrics-grid.three-col .metric:nth-child(2n) { border-right: 1px solid #e8e8e8; }
.metrics-grid.three-col .metric:nth-child(3n) { border-right: none; }
.metric .label {
  font-size: 11px;
  color: #999;
  letter-spacing: 0.02em;
  margin-bottom: 3px;
}
.metric .value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.15;
}
.section {
  border-top: 10px solid #f5f5f5;
  padding: 16px 0 8px;
}
.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px 10px;
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
}
.section-head .logo { color: #fc5200; font-weight: 800; font-size: 14px; }
.chart-wrap { padding: 0 8px 8px; overflow: hidden; }
.splits-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.splits-table th {
  color: #aaa;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 8px 2px;
  text-align: left;
  border-bottom: 1px solid #eee;
}
.splits-table td {
  padding: 3px 8px;
  border-bottom: 1px solid #f3f3f3;
  vertical-align: middle;
  line-height: 1.2;
}
.split-km { font-weight: 600; color: #333; width: 28px; }
.split-time { color: #666; width: 44px; white-space: nowrap; font-size: 12px; }
.split-pace { font-weight: 600; color: #333; width: 36px; }
.split-bar { width: auto; }
.split-bar span { display: block; height: 14px; border-radius: 2px; max-width: 100%; }
.split-elev, .split-hr { color: #666; text-align: right; width: 32px; white-space: nowrap; }
.list-block {
  border-top: 10px solid #f5f5f5;
  padding: 14px 0 4px;
}
.list-block .list-name {
  padding: 0 16px 10px;
  font-size: 13px;
  font-weight: 600;
  color: #fc5200;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: center;
}
.list-block .list-splits {
  padding: 0 0 8px;
}
.list-block .list-splits-head {
  padding: 8px 16px 4px;
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.compare-table-wrap {
  padding: 0 12px 12px;
}
.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}
.compare-table th {
  color: #aaa;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 8px 3px;
  text-align: center;
  border-bottom: 1px solid #eee;
  white-space: normal;
  line-height: 1.2;
}
.compare-table td {
  padding: 10px 3px;
  border-bottom: 1px solid #f3f3f3;
  vertical-align: middle;
  color: #333;
  text-align: center;
  line-height: 1.2;
}
.compare-table td:first-child,
.compare-table th:first-child {
  text-align: left;
  padding-left: 4px;
}
.compare-table td:first-child {
  font-weight: 700;
  color: #fc5200;
  font-size: 13px;
}
.list-splits-block {
  border-top: 1px solid #eee;
  padding: 6px 0 4px;
}
.list-splits-block .list-splits-head {
  padding: 6px 16px 2px;
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.footer {
  padding: 24px 16px 32px;
  text-align: center;
  font-size: 11px;
  color: #bbb;
  border-top: 10px solid #f5f5f5;
}
"""


def _esc(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return html.escape(str(value))


def _format_activity_datetime(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%B %d, %Y at %I:%M %p")
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%B %d, %Y at %I:%M %p")
        except ValueError:
            continue
    return text


def _metric_block(label: str, value: str) -> str:
    return f'<div class="metric"><div class="label">{_esc(label)}</div><div class="value">{_esc(value)}</div></div>'


def _metrics_grid(pairs: list[tuple[str, str]]) -> str:
    return f'<div class="metrics-grid">{"".join(_metric_block(l, v) for l, v in pairs)}</div>'


def _activity_summary_metrics(activity_row, sport: str) -> list[tuple[str, str]]:
    sport = sport.lower()
    duration = activity_row.get("duration")
    distance = activity_row.get("distance")

    if sport == "running":
        dist_km = float(distance) if distance is not None and not pd.isna(distance) else None
        pace = format_pace(float(duration) / dist_km) if duration and dist_km and dist_km > 0 else "—"
        elev = activity_row.get("elevationGain")
        cal = activity_row.get("calories")
        hr = activity_row.get("averageHR")
        return [
            ("Distance", f"{dist_km:.1f} km" if dist_km else "—"),
            ("Pace", pace or "—"),
            ("Moving Time", format_duration(duration) if duration else "—"),
            ("Elevation Gain", f"{int(float(elev))} m" if elev is not None and not pd.isna(elev) else "—"),
            ("Calories", f"{int(cal):,} cal" if cal is not None and not pd.isna(cal) else "—"),
            ("Avg Heart Rate", f"{int(hr)} bpm" if hr is not None and not pd.isna(hr) else "—"),
        ]

    if sport == "cycling":
        dist_km = float(distance) if distance is not None and not pd.isna(distance) else None
        elev = activity_row.get("elevationGain")
        cal = activity_row.get("calories")
        hr = activity_row.get("averageHR")
        speed = activity_row.get("averageSpeed")
        return [
            ("Distance", f"{dist_km:.1f} km" if dist_km else "—"),
            ("Moving Time", format_duration(duration) if duration else "—"),
            ("Avg Speed", f"{float(speed) * 3.6:.1f} km/h" if speed is not None and not pd.isna(speed) else "—"),
            ("Elevation Gain", f"{int(float(elev))} m" if elev is not None and not pd.isna(elev) else "—"),
            ("Calories", f"{int(cal):,} cal" if cal is not None and not pd.isna(cal) else "—"),
            ("Avg Heart Rate", f"{int(hr)} bpm" if hr is not None and not pd.isna(hr) else "—"),
        ]

    if sport == "swimming":
        dist_m = float(distance) * 1000.0 if distance is not None and not pd.isna(distance) else None
        if dist_m and dist_m >= 914:
            dist_label = f"{dist_m * 1.09361:.0f} yd"
        elif dist_m:
            dist_label = f"{dist_m:.0f} m"
        else:
            dist_label = "—"
        if duration and distance and float(distance) > 0:
            pace_100m = float(duration) / (float(distance) * 10.0)
            pace_label = f"{int(pace_100m) // 60}:{int(round(pace_100m)) % 60:02d} /100m"
        else:
            pace_label = "—"
        hr = activity_row.get("averageHR")
        max_hr = activity_row.get("maxHR")
        cal = activity_row.get("calories")
        return [
            ("Distance", dist_label),
            ("Moving Time", format_duration(duration) if duration else "—"),
            ("Avg Pace", pace_label),
            ("Avg Heart Rate", f"{int(hr)} bpm" if hr is not None and not pd.isna(hr) else "—"),
            ("Max Heart Rate", f"{int(max_hr)} bpm" if max_hr is not None and not pd.isna(max_hr) else "—"),
            ("Calories", f"{int(cal):,} Cal" if cal is not None and not pd.isna(cal) else "—"),
        ]

    return []


def _list_summary_metrics(agg: dict[str, Any], sport: str) -> list[tuple[str, str]]:
    """Selected-list averages as a Strava metrics grid (no power, no split labels)."""
    sport = sport.lower()

    if sport == "running":
        metrics = [
            ("Distance", f"{agg.get('distance_km', 0):.2f} km" if agg.get("distance_km") else "—"),
            ("Pace", agg.get("avg_pace") or "—"),
            ("Moving Time", agg.get("time") or "—"),
            ("Elevation Gain", f"{int(agg['elevation_gain_m'])} m" if agg.get("elevation_gain_m") is not None else "—"),
            ("Avg Heart Rate", f"{int(agg['avg_hr'])} bpm" if agg.get("avg_hr") is not None else "—"),
        ]
        if agg.get("avg_cadence") is not None:
            metrics.append(("Cadence", f"{int(round(agg['avg_cadence']))} spm"))
        if agg.get("avg_stride_m") is not None:
            metrics.append(("Stride Length", f"{agg['avg_stride_m'] * 100:.0f} cm"))
        return metrics

    if sport == "cycling":
        speed = agg.get("avg_speed_kmh")
        metrics = [
            ("Distance", f"{agg.get('distance_km', 0):.2f} km" if agg.get("distance_km") else "—"),
            ("Moving Time", agg.get("time") or "—"),
            ("NP", f"{int(round(agg['avg_np_w']))} W" if agg.get("avg_np_w") is not None else "—"),
            ("Cadence", f"{int(round(agg['avg_cadence']))} rpm" if agg.get("avg_cadence") is not None else "—"),
            ("Avg Speed", f"{speed:.1f} km/h" if speed is not None else "—"),
            ("Elevation Gain", f"{int(agg['elevation_gain_m'])} m" if agg.get("elevation_gain_m") is not None else "—"),
            ("Avg Heart Rate", f"{int(agg['avg_hr'])} bpm" if agg.get("avg_hr") is not None else "—"),
        ]
        return metrics

    if sport == "swimming":
        dist_m = agg.get("distance_m")
        return [
            ("Distance", f"{dist_m:.0f} m" if dist_m else "—"),
            ("Moving Time", agg.get("time") or "—"),
            ("Avg Pace", agg.get("avg_pace") or "—"),
            ("Avg Heart Rate", f"{int(agg['avg_hr'])} bpm" if agg.get("avg_hr") is not None else "—"),
        ]

    return []


def _comparison_row(name: str, agg: dict[str, Any], sport: str) -> dict[str, str]:
    """Compact comparison row for mobile (no Splits column)."""
    sport = sport.lower()

    def _n(val, fmt: str) -> str:
        return fmt.format(val) if val is not None else "—"

    if sport == "cycling":
        return {
            "List": name,
            "Time": agg.get("time") or "—",
            "NP": _n(agg.get("avg_np_w"), "{:.0f}"),
            "HR": _n(agg.get("avg_hr"), "{:.0f}"),
        }

    if sport == "running":
        return {
            "List": name,
            "Dist": _n(agg.get("distance_km"), "{:.1f}"),
            "Time": agg.get("time") or "—",
            "Pace": agg.get("avg_pace") or "—",
            "HR": _n(agg.get("avg_hr"), "{:.0f}"),
            "Cad": _n(agg.get("avg_cadence"), "{:.0f}"),
            "Elev": _n(agg.get("elevation_gain_m"), "{:.0f}"),
        }

    if sport == "swimming":
        dist_m = agg.get("distance_m")
        return {
            "List": name,
            "Dist": f"{dist_m:.0f}" if dist_m else "—",
            "Time": agg.get("time") or "—",
            "Pace": agg.get("avg_pace") or "—",
            "HR": _n(agg.get("avg_hr"), "{:.0f}"),
        }

    return {"List": name}


def _list_splits_html(
    laps: list[dict],
    picks: list[int],
    sport: str,
    *,
    bar_color: str | None = None,
    list_title: str | None = None,
) -> str:
    if not picks:
        return ""
    subset = [laps[i] for i in picks if 0 <= i < len(laps)]
    if not subset:
        return ""
    sport = sport.lower()
    if sport == "running":
        table = svg_run_list_splits_table(subset, bar_color=bar_color)
    elif sport == "cycling":
        table = svg_bike_np_splits_table(subset, bar_color=bar_color)
    else:
        table = svg_swim_splits_table(subset)
    if not table:
        return ""
    title = list_title or "Splits"
    return f'<div class="list-splits-block"><div class="list-splits-head">{_esc(title)}</div>{table}</div>'


def _list_comparison_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    columns = list(rows[0].keys())
    head = "".join(f"<th>{_esc(col)}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col, "—")
            cells.append(f"<td>{_esc(val)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"""
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>"""


def _list_blocks_html(list_aggregates: list[dict[str, Any]], laps: list[dict], sport: str) -> str:
    if not list_aggregates:
        return ""

    compare_rows = []
    splits_parts = []
    for list_idx, item in enumerate(list_aggregates):
        name = f"#{list_idx + 1}"
        agg = item.get("agg") or {}
        picks = item.get("picks") or []
        if not agg:
            continue
        compare_rows.append(_comparison_row(name, agg, sport))
        list_color = LIST_COLORS[list_idx % len(LIST_COLORS)]
        list_time = agg.get("time") or "—"
        splits_html = _list_splits_html(
            laps,
            picks,
            sport,
            bar_color=list_color,
            list_title=f"{list_time} · {name}",
        )
        if splits_html:
            splits_parts.append(splits_html)

    if not compare_rows:
        return ""

    return (
        f'<div class="section"><div class="section-head">Split Comparison</div>'
        f'{_list_comparison_table(compare_rows)}'
        f'{"".join(splits_parts)}</div>'
    )


def _hr_zones_section(laps: list[dict], hr_series, max_hr) -> str:
    zones_svg = ""
    if hr_series is not None and not hr_series.empty:
        zones_svg = svg_hr_zones(hr_series, max_hr=max_hr)
    if not zones_svg and laps:
        zone_seconds, _ = hr_zone_seconds_from_laps(laps, max_hr=max_hr)
        zones_svg = svg_hr_zones_from_seconds(zone_seconds)
    if not zones_svg:
        return ""
    return (
        f'<div class="section"><div class="section-head">Heart Rate Zones</div>'
        f'<div class="chart-wrap">{zones_svg}</div></div>'
    )


def _run_body(laps: list[dict], hr_series, max_hr) -> str:
    parts = []
    zones = _hr_zones_section(laps, hr_series, max_hr)
    if zones:
        parts.append(zones)

    chart = svg_pace_workout_chart(laps)
    if chart:
        parts.append(
            f'<div class="section"><div class="section-head">Workout Analysis</div>'
            f'<div class="chart-wrap">{chart}</div></div>'
        )
    splits = svg_run_splits_table(laps)
    if splits:
        parts.append(f'<div class="section"><div class="section-head">Splits</div>{splits}</div>')
    return "".join(parts)


def _bike_body(laps: list[dict], power_profile: dict | None, hr_series, max_hr) -> str:
    parts = []
    zones = _hr_zones_section(laps, hr_series, max_hr)
    if zones:
        parts.append(zones)

    if power_profile:
        curve = power_profile.get("power_curve") or {}
        curve_svg = svg_power_curve(curve)
        if curve_svg:
            parts.append(
                f'<div class="section"><div class="section-head">'
                f'<span class="logo">&gt;</span> Power Curve</div>'
                f'<div class="chart-wrap">{curve_svg}</div></div>'
            )
        skills_svg = svg_power_skills(curve)
        if skills_svg:
            parts.append(
                f'<div class="section"><div class="section-head">Power Skills</div>'
                f'<div class="chart-wrap">{skills_svg}</div></div>'
            )
    return "".join(parts)


def _swim_body(laps: list[dict]) -> str:
    splits = svg_swim_splits_table(laps)
    if not splits:
        return ""
    return f'<div class="section"><div class="section-head">Splits</div>{splits}</div>'


def _structure_summary(activity_row) -> str | None:
    text = activity_row.get("structure_summary")
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    cleaned = str(text).strip()
    return cleaned or None


def _effect_label(activity_row) -> str | None:
    label = activity_row.get("trainingEffectLabel")
    if label is None or (isinstance(label, float) and pd.isna(label)):
        return None
    text = str(label).strip()
    if not text:
        return None
    return text.replace("_", " ").title()


def _intro_html(
    activity_row,
    sport_label: str,
    title: str,
    when: str,
    track_points: list | None,
    *,
    effect_label: str | None = None,
    structure_summary: str | None = None,
) -> tuple[str, bool]:
    effect_html = ""
    if effect_label:
        effect_html = f'<div class="effect">{_esc(effect_label)}</div>'

    structure_html = ""
    if structure_summary:
        structure_html = f'<div class="structure">{_esc(structure_summary)}</div>'

    map_html = ""
    uses_leaflet = False
    if track_points and len(track_points) >= 2:
        leaflet_map = html_route_map(track_points)
        if leaflet_map:
            map_html = f'<div class="map-wrap">{leaflet_map}</div>'
            uses_leaflet = True

    intro = f"""
    <div class="intro-top"><h1>{_esc(title)}</h1></div>
    {map_html}
    <div class="intro-meta">
      <div class="when">{_esc(when)}</div>
      {effect_html}
      {structure_html}
    </div>"""
    return intro, uses_leaflet


def build_activity_report_html(
    activity_row,
    laps: list[dict],
    list_aggregates: list[dict[str, Any]] | None = None,
    *,
    power_profile: dict | None = None,
    hr_series: pd.Series | None = None,
    track_points: list | None = None,
) -> str:
    sport = resolve_sport(activity_row)
    sport_label = {"running": "Run", "cycling": "Ride", "swimming": "Swim"}.get(sport, sport.title())
    title = activity_row.get("activityName") or f"{sport_label} Activity"
    when = _format_activity_datetime(activity_row.get("startTimeLocal"))
    effect_label = _effect_label(activity_row)
    structure_summary = _structure_summary(activity_row)

    summary_metrics = _activity_summary_metrics(activity_row, sport)
    max_hr = activity_row.get("maxHR")

    if sport == "running":
        sport_body = _run_body(laps, hr_series, max_hr)
    elif sport == "cycling":
        sport_body = _bike_body(laps, power_profile, hr_series, max_hr)
    else:
        sport_body = _swim_body(laps)

    lists_html = _list_blocks_html(list_aggregates or [], laps, sport)
    intro_html, uses_leaflet = _intro_html(
        activity_row,
        sport_label,
        title,
        when,
        track_points,
        effect_label=effect_label,
        structure_summary=structure_summary,
    )
    leaflet_head = LEAFLET_HEAD if uses_leaflet else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>{_esc(title)}</title>
  {leaflet_head}
  <style>{STRAVA_CSS}</style>
</head>
<body>
  <div class="phone">
    {intro_html}
    {_metrics_grid(summary_metrics)}
    {sport_body}
    {lists_html}
    <div class="footer">Garmin Analytics</div>
  </div>
</body>
</html>"""


def build_list_aggregates(
    laps: list[dict],
    list_picks: list[list[int]],
    sport: str,
    *,
    list_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    aggregates = []
    for list_idx, picked in enumerate(list_picks):
        if not picked:
            continue
        agg = aggregate_selected_laps(laps, picked, sport)
        if not agg:
            continue
        default_name = f"List {list_idx + 1}"
        name = default_name
        if list_names and list_idx < len(list_names) and list_names[list_idx]:
            name = str(list_names[list_idx]).strip() or default_name
        aggregates.append({"name": name, "agg": agg, "picks": picked})
    return aggregates
