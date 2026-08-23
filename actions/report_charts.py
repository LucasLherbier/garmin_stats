"""Inline SVG charts for mobile HTML activity reports."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from actions.cycling_splits import _lap_duration_s
from actions.power_curve import POWER_CURVE_DURATIONS, duration_display_label
from utils.pipeline.workout_summaries.parse_laps import cycling_lap_power_w, format_duration, format_pace


LIST_COLORS = [
    "#fc5200", "#3b82f6", "#22c55e", "#eab308", "#a855f7",
    "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
]

# Backwards-compatible alias
SPLIT_COLORS = LIST_COLORS


def _fmt_pace_short(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def svg_pace_workout_chart(laps: list[dict], width: int = 380, height: int = 240) -> str:
    """Strava-like pace bar chart from run laps (uniform bar color)."""
    usable = []
    for lap in laps:
        pace = lap.get("avg_pace_s_km")
        dist = float(lap.get("distance_km") or 0)
        if pace and dist > 0:
            usable.append({"pace": float(pace), "dist": dist, "split": lap.get("split")})

    if not usable:
        return ""

    paces = [row["pace"] for row in usable]
    min_p, max_p = min(paces), max(paces)
    pad = max(15, (max_p - min_p) * 0.15)
    y_min, y_max = min_p - pad, max_p + pad
    avg_pace = sum(paces) / len(paces)

    margin = dict(l=36, r=12, t=16, b=28)
    inner_w = width - margin["l"] - margin["r"]
    inner_h = height - margin["t"] - margin["b"]
    total_dist = sum(row["dist"] for row in usable)
    x = margin["l"]

    def y_pos(pace: float) -> float:
        ratio = (pace - y_min) / (y_max - y_min) if y_max > y_min else 0.5
        return margin["t"] + ratio * inner_h

    bars = []
    for row in usable:
        bar_w = inner_w * (row["dist"] / total_dist) if total_dist else inner_w / len(usable)
        y_top = y_pos(row["pace"])
        y_base = margin["t"] + inner_h
        bar_h = max(4, y_base - y_top)
        cx = x + bar_w / 2
        bars.append(
            f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{max(bar_w - 1, 2):.1f}" '
            f'height="{bar_h:.1f}" rx="2" fill="#7eb8e6" opacity="1"/>'
        )
        x += bar_w

    avg_y = y_pos(avg_pace)
    tick_lines = []
    for pace_val in [y_min, (y_min + y_max) / 2, y_max]:
        y = y_pos(pace_val)
        tick_lines.append(
            f'<line x1="{margin["l"]}" y1="{y:.1f}" x2="{width - margin["r"]}" y2="{y:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )
        tick_lines.append(
            f'<text x="{margin["l"] - 6}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="10" fill="#999">{_fmt_pace_short(pace_val)}</text>'
        )

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
      {''.join(tick_lines)}
      <line x1="{margin['l']}" y1="{avg_y:.1f}" x2="{width - margin['r']}" y2="{avg_y:.1f}"
            stroke="#bbb" stroke-width="1" stroke-dasharray="4 3"/>
      {''.join(bars)}
    </svg>"""


def svg_run_splits_table(laps: list[dict], *, show_hr: bool = False, bar_color: str | None = None) -> str:
    """Strava-style splits: KM | PACE | bar | ELEV [| HR]."""
    rows_html = []
    paces = [lap.get("avg_pace_s_km") for lap in laps if lap.get("avg_pace_s_km")]
    fastest = min(paces) if paces else None

    for lap in laps:
        pace_s = lap.get("avg_pace_s_km")
        pace_txt = _fmt_pace_short(pace_s) if pace_s else "—"
        split = lap.get("split", "—")
        elev = lap.get("elevation_gain_m")
        elev_txt = f"{int(round(elev))}" if elev is not None else "—"

        if pace_s and fastest:
            intensity = fastest / pace_s
            bar_pct = int(35 + 65 * min(intensity, 1.15))
            if bar_color:
                row_color = bar_color
            elif pace_s <= fastest * 1.05:
                row_color = "#7eb8e6"
            else:
                row_color = "#c5dff5"
        else:
            bar_pct = 35
            row_color = bar_color or "#e5e7eb"

        hr_cell = ""
        if show_hr:
            hr = lap.get("avg_hr")
            hr_txt = f"{int(round(hr))}" if hr is not None else "—"
            hr_cell = f'<td class="split-hr">{hr_txt}</td>'

        rows_html.append(
            f"""<tr>
              <td class="split-km">{split}</td>
              <td class="split-pace">{pace_txt}</td>
              <td class="split-bar"><span style="width:{bar_pct}%;background:{row_color}"></span></td>
              <td class="split-elev">{elev_txt}</td>
              {hr_cell}
            </tr>"""
        )

    if not rows_html:
        return ""

    hr_head = "<th>HR</th>" if show_hr else ""
    return f"""
    <table class="splits-table">
      <thead><tr>
        <th>KM</th><th>PACE</th><th></th><th>ELEV</th>{hr_head}
      </tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>"""


def svg_run_list_splits_table(laps: list[dict], *, bar_color: str | None = None) -> str:
    """Compact list comparison splits: Time | Pace | bar | HR."""
    rows_html = []
    paces = [lap.get("avg_pace_s_km") for lap in laps if lap.get("avg_pace_s_km")]
    fastest = min(paces) if paces else None
    row_color = bar_color or "#7eb8e6"

    for lap in laps:
        dur_s = _lap_duration_s(lap)
        time_txt = format_duration(dur_s) if dur_s else "—"
        pace_s = lap.get("avg_pace_s_km")
        pace_txt = _fmt_pace_short(pace_s) if pace_s else "—"
        hr = lap.get("avg_hr")
        hr_txt = f"{int(round(hr))}" if hr is not None else "—"

        if pace_s and fastest:
            intensity = fastest / pace_s
            bar_pct = int(35 + 65 * min(intensity, 1.15))
        else:
            bar_pct = 35

        rows_html.append(
            f"""<tr>
              <td class="split-time">{time_txt}</td>
              <td class="split-pace">{pace_txt}</td>
              <td class="split-bar"><span style="width:{bar_pct}%;background:{row_color}"></span></td>
              <td class="split-hr">{hr_txt}</td>
            </tr>"""
        )

    if not rows_html:
        return ""

    return f"""
    <table class="splits-table">
      <thead><tr>
        <th>Time</th><th>Pace</th><th></th><th>HR</th>
      </tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>"""


def svg_bike_np_splits_table(laps: list[dict], *, bar_color: str | None = None) -> str:
    """Strava-style bike splits: Split | NP | bar | HR."""
    rows_html = []
    power_vals = []
    for lap in laps:
        p = cycling_lap_power_w(lap)
        if p is not None:
            power_vals.append(float(p))
    peak = max(power_vals) if power_vals else None

    for lap in laps:
        dur_s = _lap_duration_s(lap)
        time_txt = format_duration(dur_s) if dur_s else "—"
        np_w = cycling_lap_power_w(lap)
        np_txt = f"{int(round(np_w))}" if np_w is not None else "—"
        hr = lap.get("avg_hr")
        hr_txt = f"{int(round(hr))}" if hr is not None else "—"

        if np_w is not None and peak:
            intensity = float(np_w) / peak
            bar_pct = int(35 + 65 * min(intensity, 1.0))
            if bar_color:
                row_color = bar_color
            elif intensity >= 0.85:
                row_color = "#9b59b6"
            else:
                row_color = "#c4b5fd"
        else:
            bar_pct = 35
            row_color = bar_color or "#e5e7eb"

        rows_html.append(
            f"""<tr>
              <td class="split-time">{time_txt}</td>
              <td class="split-pace">{np_txt}</td>
              <td class="split-bar"><span style="width:{bar_pct}%;background:{row_color}"></span></td>
              <td class="split-hr">{hr_txt}</td>
            </tr>"""
        )

    if not rows_html:
        return ""

    return f"""
    <table class="splits-table">
      <thead><tr>
        <th>Time</th><th>NP</th><th></th><th>HR</th>
      </tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>"""


def _hr_zone_index(hr: float, max_hr: float) -> int:
    pct = hr / max_hr if max_hr > 0 else 0
    thresholds = [0.60, 0.70, 0.80, 0.90, 0.95, 0.99]
    for i, threshold in enumerate(thresholds):
        if pct < threshold:
            return i
    return 6


def hr_zone_seconds_from_laps(laps: list[dict], max_hr: float | None = None) -> tuple[list[float], float]:
    """Duration (seconds) in each HR zone, estimated from lap avg HR."""
    zone_seconds = [0.0] * 7
    hr_samples = [lap.get("avg_hr") for lap in laps if lap.get("avg_hr") is not None]
    if not hr_samples:
        return zone_seconds, float(max_hr or 190)

    estimated_max = float(max_hr or max(hr_samples) * 1.05)
    for lap in laps:
        hr = lap.get("avg_hr")
        dur = _lap_duration_s(lap)
        if hr is None or dur <= 0:
            continue
        zone_seconds[_hr_zone_index(float(hr), estimated_max)] += dur
    return zone_seconds, estimated_max


def svg_hr_zones_from_seconds(
    zone_seconds: list[float],
    width: int = 380,
    height: int = 130,
) -> str:
    """Horizontal zone distribution bar chart (Z1–Z7) with visible segments."""
    total = sum(zone_seconds)
    if total <= 0:
        return ""

    colors = ["#fde8ef", "#f8c4d8", "#e898bc", "#c96aa8", "#9b59b6", "#6b2d84", "#1f1f1f"]
    margin = dict(l=8, r=8, t=8, b=36)
    bar_h = 56
    x = margin["l"]
    inner_w = width - margin["l"] - margin["r"]
    rects = []
    labels = []

    for i, seconds in enumerate(zone_seconds):
        w = inner_w * (seconds / total)
        if w < 1:
            w = 1 if seconds > 0 else 0
        if w <= 0:
            continue
        rects.append(
            f'<rect x="{x:.1f}" y="{margin["t"]}" width="{max(w, 2):.1f}" height="{bar_h}" fill="{colors[i]}"/>'
        )
        cx = x + max(w, 2) / 2
        pct = int(round(100 * seconds / total))
        if pct >= 3:
            labels.append(
                f'<text x="{cx:.1f}" y="{margin["t"] + bar_h + 16}" text-anchor="middle" '
                f'font-size="11" fill="#666">Z{i + 1}</text>'
            )
            labels.append(
                f'<text x="{cx:.1f}" y="{margin["t"] + bar_h + 30}" text-anchor="middle" '
                f'font-size="9" fill="#999">{pct}%</text>'
            )
        x += w

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
      {''.join(rects)}
      {''.join(labels)}
    </svg>"""


def svg_hr_zones(hr_values: pd.Series, max_hr: float | None = None, width: int = 380, height: int = 130) -> str:
    """Horizontal zone distribution from telemetry HR samples."""
    numeric = pd.to_numeric(hr_values, errors="coerce").dropna()
    numeric = numeric[numeric > 0]
    if numeric.empty:
        return ""

    max_hr = float(max_hr or numeric.max() or 190)
    zone_seconds = [0.0] * 7
    for hr in numeric:
        zone_seconds[_hr_zone_index(float(hr), max_hr)] += 1.0
    return svg_hr_zones_from_seconds(zone_seconds, width=width, height=height)


def _nice_y_ticks(y_min: float, y_max: float, count: int = 5) -> list[int]:
    """Round y-axis ticks spanning the data range."""
    span = y_max - y_min
    if span <= 0:
        return [int(y_min)]
    step = max(25, int(round(span / count / 25)) * 25)
    start = int(math.floor(y_min / step) * step)
    ticks = []
    v = start
    while v <= y_max + step * 0.01:
        if v >= y_min * 0.95:
            ticks.append(v)
        v += step
    return ticks or [int(y_min), int(y_max)]


def svg_power_curve(power_curve: dict[str, float | None], width: int = 380, height: int = 200) -> str:
    """Line chart of peak power vs duration (log x-axis, Strava-style grid)."""
    labels = [label for label in POWER_CURVE_DURATIONS if power_curve.get(label) is not None]
    if len(labels) < 2:
        return ""

    points = [
        (POWER_CURVE_DURATIONS[label], float(power_curve[label]), duration_display_label(label))
        for label in labels
    ]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    y_min = max(0, min(ys) * 0.88)
    y_max = max(ys) * 1.06

    margin = dict(l=44, r=14, t=12, b=36)
    inner_w = width - margin["l"] - margin["r"]
    inner_h = height - margin["t"] - margin["b"]
    base_y = margin["t"] + inner_h
    log_min = math.log10(max(min(xs), 1))
    log_max = math.log10(max(xs))

    def px(sec: float) -> float:
        if log_max <= log_min:
            return margin["l"]
        return margin["l"] + inner_w * ((math.log10(max(sec, 1)) - log_min) / (log_max - log_min))

    def py(watts: float) -> float:
        ratio = (watts - y_min) / (y_max - y_min) if y_max > y_min else 0.5
        return margin["t"] + inner_h * (1 - ratio)

    grid = []
    # Horizontal grid + y labels
    for tick in _nice_y_ticks(y_min, y_max):
        y = py(tick)
        grid.append(
            f'<line x1="{margin["l"]}" y1="{y:.1f}" x2="{width - margin["r"]}" y2="{y:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )
        grid.append(
            f'<text x="{margin["l"] - 5}" y="{y + 3.5:.1f}" text-anchor="end" '
            f'font-size="10" fill="#999">{tick}</text>'
        )

    # Vertical grid at each duration tick
    for sec, _, _ in points:
        x = px(sec)
        grid.append(
            f'<line x1="{x:.1f}" y1="{margin["t"]}" x2="{x:.1f}" y2="{base_y:.1f}" '
            f'stroke="#ececec" stroke-width="1"/>'
        )

    # Axis box
    grid.append(
        f'<line x1="{margin["l"]}" y1="{margin["t"]}" x2="{margin["l"]}" y2="{base_y:.1f}" '
        f'stroke="#d4d4d4" stroke-width="1"/>'
    )
    grid.append(
        f'<line x1="{margin["l"]}" y1="{base_y:.1f}" x2="{width - margin["r"]}" y2="{base_y:.1f}" '
        f'stroke="#d4d4d4" stroke-width="1"/>'
    )
    grid.append(
        f'<text x="{margin["l"] - 2}" y="{base_y + 14:.1f}" text-anchor="end" '
        f'font-size="10" fill="#999">W</text>'
    )

    path = "M " + " L ".join(f"{px(s):.1f},{py(w):.1f}" for s, w, _ in points)
    tick_labels = []
    for sec, _, label in points:
        tick_labels.append(
            f'<text x="{px(sec):.1f}" y="{height - 6}" text-anchor="middle" '
            f'font-size="9" fill="#888">{label}</text>'
        )

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
      <rect x="{margin['l']}" y="{margin['t']}" width="{inner_w}" height="{inner_h}" fill="#fafafa"/>
      {''.join(grid)}
      <path d="{path}" fill="none" stroke="#5b21b6" stroke-width="2.5"/>
      {''.join(f'<circle cx="{px(s):.1f}" cy="{py(w):.1f}" r="3.5" fill="#5b21b6"/>' for s, w, _ in points)}
      {''.join(tick_labels)}
    </svg>"""


def _estimate_label_width(label: str, watts: float, font_size: int) -> float:
    return len(f"{label} {int(watts)}W") * font_size * 0.52


def _clamp_radar_label(
    lx: float,
    ly: float,
    anchor: str,
    est_w: float,
    width: float,
    height: float,
    *,
    margin: float = 8,
    font_size: int = 14,
) -> tuple[float, float]:
    if anchor == "start":
        lx = min(lx, width - margin - est_w)
        lx = max(lx, margin)
    elif anchor == "end":
        lx = max(lx, margin + est_w)
        lx = min(lx, width - margin)
    else:
        lx = max(margin + est_w / 2, min(lx, width - margin - est_w / 2))
    ly = max(margin + font_size, min(ly, height - margin))
    return lx, ly


def svg_power_skills(power_curve: dict[str, float | None], width: int = 380, height: int = 340) -> str:
    """Power skills radar with background grid (sprint / attack / climb)."""
    rings = [
        ("15s", "#3b82f6"), ("30s", "#3b82f6"), ("1m", "#3b82f6"),
        ("2m", "#22c55e"), ("5m", "#22c55e"), ("10m", "#22c55e"),
        ("20m", "#f97316"), ("30m", "#f97316"), ("60m", "#f97316"),
    ]
    entries = [(label, power_curve.get(label), color) for label, color in rings if power_curve.get(label)]
    if not entries:
        return ""

    pad_x, pad_y = 24, 18
    cx = width / 2
    cy = height / 2 - 6
    n = len(entries)
    labels_svg = []
    polygon_pts = []
    grid_svg = []

    values = [e[1] for e in entries]
    v_max = max(values) if values else 1

    font_size = 14
    max_label_w = max(_estimate_label_width(label, watts, font_size) for label, watts, _ in entries)
    label_gap = min(34, max(22, max_label_w * 0.35))
    inner = min(width - 2 * pad_x, height - 2 * pad_y)
    radius = inner / 2 - max_label_w * 0.55 - label_gap
    radius = max(radius, inner * 0.28)

    if radius < inner * 0.34:
        font_size = 12
        max_label_w = max(_estimate_label_width(label, watts, font_size) for label, watts, _ in entries)
        label_gap = min(30, max(20, max_label_w * 0.35))
        radius = inner / 2 - max_label_w * 0.55 - label_gap
        radius = max(radius, inner * 0.26)

    # Background concentric rings + radial spokes
    for frac in (0.25, 0.5, 0.75, 1.0):
        r = radius * frac
        grid_svg.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" '
            f'stroke="rgba(0,0,0,0.10)" stroke-width="1"/>'
        )
    for i in range(n):
        angle = -math.pi / 2 + (2 * math.pi * i / n)
        x2 = cx + radius * math.cos(angle)
        y2 = cy + radius * math.sin(angle)
        grid_svg.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="rgba(0,0,0,0.10)" stroke-width="1"/>'
        )

    for i, (label, watts, color) in enumerate(entries):
        angle = -math.pi / 2 + (2 * math.pi * i / n)
        norm = (watts / v_max) if v_max else 0
        r = radius * (0.35 + 0.65 * norm)
        px_pt = cx + r * math.cos(angle)
        py_pt = cy + r * math.sin(angle)
        polygon_pts.append(f"{px_pt:.1f},{py_pt:.1f}")

        lx = cx + (radius + label_gap) * math.cos(angle)
        ly = cy + (radius + label_gap) * math.sin(angle)
        anchor = "middle"
        if math.cos(angle) > 0.3:
            anchor = "start"
        elif math.cos(angle) < -0.3:
            anchor = "end"
        est_w = _estimate_label_width(label, watts, font_size)
        lx, ly = _clamp_radar_label(lx, ly, anchor, est_w, width, height, font_size=font_size)
        labels_svg.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="{font_size}" fill="{color}">'
            f'<tspan font-weight="700">{label}</tspan>'
            f'<tspan fill="#333" font-weight="600"> {int(watts)}W</tspan></text>'
        )

    poly = " ".join(polygon_pts)
    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" overflow="visible">
      {''.join(grid_svg)}
      <polygon points="{poly}" fill="rgba(91,33,182,0.18)" stroke="#5b21b6" stroke-width="2"/>
      {''.join(labels_svg)}
    </svg>"""


def svg_swim_splits_table(laps: list[dict]) -> str:
    rows = []
    for lap in laps:
        if lap.get("is_rest"):
            continue
        pace = lap.get("avg_pace_s_100m")
        pace_txt = f"{_fmt_pace_short(pace)}/100m" if pace else "—"
        dist = lap.get("distance_m")
        dist_txt = f"{int(dist)}" if dist else "—"
        dur = float(lap.get("time_s") or 0)
        rows.append(
            f"""<tr>
              <td>{lap.get('split', '—')}</td>
              <td>{format_duration(dur) or '—'}</td>
              <td>{dist_txt}</td>
              <td>{pace_txt}</td>
              <td>{int(lap['avg_hr']) if lap.get('avg_hr') else '—'}</td>
            </tr>"""
        )
    if not rows:
        return ""
    return f"""
    <table class="splits-table">
      <thead><tr><th>Split</th><th>Time</th><th>Dist</th><th>Pace</th><th>HR</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""
