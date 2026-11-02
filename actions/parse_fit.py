"""Parse Garmin FIT activity files into tabular / map-friendly structures."""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree as ET

import pandas as pd

_SEMICIRCLE_TO_DEG = 180.0 / (2**31)


def _semicircles_to_degrees(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * _SEMICIRCLE_TO_DEG
    except (TypeError, ValueError):
        return None


def parse_fit_to_dataframe(fit_input: bytes) -> pd.DataFrame:
    """Record messages as a TCX-like dataframe (Time, HeartRate, Watts, …)."""
    from fitparse import FitFile

    fit = FitFile(BytesIO(fit_input))
    rows: list[dict] = []
    for message in fit.get_messages("record"):
        fields = {field.name: field.value for field in message}
        timestamp = fields.get("timestamp")
        if timestamp is None:
            continue
        speed = fields.get("speed") or fields.get("enhanced_speed")
        speed_kmh = float(speed) * 3.6 if speed is not None else None
        rows.append(
            {
                "Time": pd.Timestamp(timestamp),
                "HeartRate": fields.get("heart_rate"),
                "Cadence": fields.get("cadence"),
                "Speed": speed_kmh,
                "Watts": fields.get("power"),
                "Altitude": fields.get("altitude") or fields.get("enhanced_altitude"),
                "Distance": fields.get("distance") or fields.get("enhanced_distance"),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def fit_track_points(fit_input: bytes) -> list[tuple[float, float]]:
    """GPS track from FIT record messages as (lat, lon) in degrees."""
    from fitparse import FitFile

    fit = FitFile(BytesIO(fit_input))
    points: list[tuple[float, float]] = []
    for message in fit.get_messages("record"):
        fields = {field.name: field.value for field in message}
        lat = _semicircles_to_degrees(fields.get("position_lat"))
        lon = _semicircles_to_degrees(fields.get("position_long"))
        if lat is None or lon is None:
            continue
        points.append((lat, lon))
    return points


def fit_bytes_to_gpx(fit_input: bytes) -> bytes | None:
    """Minimal GPX 1.1 track from FIT record messages (lat/lon/time/elevation)."""
    from fitparse import FitFile

    fit = FitFile(BytesIO(fit_input))
    gpx = ET.Element(
        "gpx",
        attrib={
            "version": "1.1",
            "creator": "garmin_stats",
            "xmlns": "http://www.topografix.com/GPX/1/1",
        },
    )
    trk = ET.SubElement(gpx, "trk")
    trkseg = ET.SubElement(trk, "trkseg")
    point_count = 0
    for message in fit.get_messages("record"):
        fields = {field.name: field.value for field in message}
        lat = _semicircles_to_degrees(fields.get("position_lat"))
        lon = _semicircles_to_degrees(fields.get("position_long"))
        if lat is None or lon is None:
            continue
        trkpt = ET.SubElement(trkseg, "trkpt", attrib={"lat": f"{lat:.7f}", "lon": f"{lon:.7f}"})
        timestamp = fields.get("timestamp")
        if timestamp is not None:
            ts = pd.Timestamp(timestamp)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
            ET.SubElement(trkpt, "time").text = ts.isoformat().replace("+00:00", "Z")
        alt = fields.get("altitude") or fields.get("enhanced_altitude")
        if alt is not None:
            ET.SubElement(trkpt, "ele").text = f"{float(alt):.2f}"
        point_count += 1
    if point_count == 0:
        return None
    return ET.tostring(gpx, encoding="utf-8", xml_declaration=True)
