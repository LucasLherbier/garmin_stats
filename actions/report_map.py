"""GPX track parsing and map rendering for mobile HTML reports."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET


def gpx_track_points(gpx_input: bytes | str) -> list[tuple[float, float]]:
    namespace = {"default": "http://www.topografix.com/GPX/1/1"}
    if isinstance(gpx_input, bytes):
        root = ET.fromstring(gpx_input)
    else:
        root = ET.fromstring(gpx_input.encode() if not gpx_input.strip().startswith("<") else gpx_input)

    points: list[tuple[float, float]] = []
    for trkpt in root.findall(".//default:trkpt", namespace):
        lat = trkpt.attrib.get("lat")
        lon = trkpt.attrib.get("lon")
        if lat is None or lon is None:
            continue
        points.append((float(lat), float(lon)))
    return points


def svg_route_map(track_points: list[tuple[float, float]], width: int = 430, height: int = 220) -> str:
    if len(track_points) < 2:
        return ""

    lats = [p[0] for p in track_points]
    lons = [p[1] for p in track_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    pad_lat = max((max_lat - min_lat) * 0.08, 0.001)
    pad_lon = max((max_lon - min_lon) * 0.08, 0.001)
    min_lat -= pad_lat
    max_lat += pad_lat
    min_lon -= pad_lon
    max_lon += pad_lon

    margin = 12
    inner_w = width - margin * 2
    inner_h = height - margin * 2

    def px(lon: float) -> float:
        span = max_lon - min_lon
        return margin + inner_w * ((lon - min_lon) / span if span else 0.5)

    def py(lat: float) -> float:
        span = max_lat - min_lat
        return margin + inner_h * (1 - (lat - min_lat) / span if span else 0.5)

    pts = " ".join(f"{px(lon):.1f},{py(lat):.1f}" for lat, lon in track_points)
    step = max(len(track_points) // 180, 1)
    sampled = track_points[::step]
    if sampled[-1] != track_points[-1]:
        sampled = sampled + [track_points[-1]]
    poly = " ".join(f"{px(lon):.1f},{py(lat):.1f}" for lat, lon in sampled)

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" class="route-map">
      <rect width="{width}" height="{height}" fill="#eceae4"/>
      <polyline points="{poly}" fill="none" stroke="#fc5200" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="{px(track_points[0][1]):.1f}" cy="{py(track_points[0][0]):.1f}" r="5" fill="#fff" stroke="#fc5200" stroke-width="2"/>
    </svg>"""


LEAFLET_HEAD = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
"""


def html_route_map(track_points: list[tuple[float, float]], height: int = 220, map_id: str = "route-map") -> str:
    """Interactive OpenStreetMap route (Leaflet), matching the run/bike app tabs."""
    if len(track_points) < 2:
        return ""

    lats = [p[0] for p in track_points]
    lons = [p[1] for p in track_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    coords_js = json.dumps([[lat, lon] for lat, lon in track_points])
    bounds_js = json.dumps([[min_lat, min_lon], [max_lat, max_lon]])

    return f"""
    <div id="{map_id}" class="route-map-leaflet" style="width:100%;height:{height}px;"></div>
    <script>
    (function() {{
      var map = L.map("{map_id}", {{scrollWheelZoom: false, zoomControl: false}});
      L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
      }}).addTo(map);
      var line = L.polyline({coords_js}, {{color: "#fc5200", weight: 4, opacity: 1}}).addTo(map);
      map.fitBounds({bounds_js}, {{padding: [14, 14]}});
      L.circleMarker(line.getLatLngs()[0], {{
        radius: 5, color: "#fc5200", weight: 2, fillColor: "#fff", fillOpacity: 1
      }}).addTo(map);
    }})();
    </script>"""
