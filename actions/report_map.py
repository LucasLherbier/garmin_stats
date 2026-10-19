"""GPX track parsing and map rendering for mobile HTML reports."""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

TILE_SIZE = 256
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_USER_AGENT = "GarminAnalytics/1.0 (activity report map; +https://garmin-stats.onrender.com)"
ROUTE_COLOR = "#fc5200"
ROUTE_WIDTH = 4


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


def _lat_lon_to_pixel(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    sin_lat = math.sin(math.radians(lat))
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n * TILE_SIZE
    y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * n * TILE_SIZE
    return x, y


def _fetch_osm_tile(z: int, x: int, y: int):
    from PIL import Image

    url = OSM_TILE_URL.format(z=z, x=x, y=y)
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": OSM_USER_AGENT})
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception as exc:
        logger.warning("OSM tile fetch failed z=%s x=%s y=%s: %s", z, x, y, exc)
        return None


def png_route_map(
    track_points: list[tuple[float, float]],
    *,
    width: int = 430,
    height: int = 220,
) -> bytes | None:
    """Raster map from OSM tiles + route overlay (works offline in shared HTML via embed)."""
    if len(track_points) < 2:
        return None

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.warning("Pillow not installed; skipping PNG route map")
        return None

    lats = [p[0] for p in track_points]
    lons = [p[1] for p in track_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    pad_lat = max((max_lat - min_lat) * 0.12, 0.002)
    pad_lon = max((max_lon - min_lon) * 0.12, 0.002)
    min_lat -= pad_lat
    max_lat += pad_lat
    min_lon -= pad_lon
    max_lon += pad_lon

    zoom = 11
    for z in range(16, 5, -1):
        nw_x, nw_y = _lat_lon_to_pixel(max_lat, min_lon, z)
        se_x, se_y = _lat_lon_to_pixel(min_lat, max_lon, z)
        if (se_x - nw_x) <= width * 1.05 and (se_y - nw_y) <= height * 1.05:
            zoom = z
            break

    nw_x, nw_y = _lat_lon_to_pixel(max_lat, min_lon, zoom)
    se_x, se_y = _lat_lon_to_pixel(min_lat, max_lon, zoom)
    span_x = max(se_x - nw_x, 1.0)
    span_y = max(se_y - nw_y, 1.0)

    x_off = (width - span_x) / 2
    y_off = (height - span_y) / 2
    world_left = nw_x - x_off
    world_top = nw_y - y_off
    world_right = world_left + width
    world_bottom = world_top + height

    tile_x0 = int(math.floor(world_left / TILE_SIZE))
    tile_y0 = int(math.floor(world_top / TILE_SIZE))
    tile_x1 = int(math.floor((world_right - 1) / TILE_SIZE))
    tile_y1 = int(math.floor((world_bottom - 1) / TILE_SIZE))

    canvas = Image.new("RGB", (width, height), (236, 234, 228))
    for tx in range(tile_x0, tile_x1 + 1):
        for ty in range(tile_y0, tile_y1 + 1):
            tile = _fetch_osm_tile(zoom, tx, ty)
            if tile is None:
                return None
            paste_x = int(tx * TILE_SIZE - world_left)
            paste_y = int(ty * TILE_SIZE - world_top)
            canvas.paste(tile, (paste_x, paste_y))

    def to_xy(lat: float, lon: float) -> tuple[float, float]:
        px_x, px_y = _lat_lon_to_pixel(lat, lon, zoom)
        return px_x - world_left, px_y - world_top

    draw = ImageDraw.Draw(canvas)
    step = max(len(track_points) // 400, 1)
    sampled = track_points[::step]
    if sampled[-1] != track_points[-1]:
        sampled = sampled + [track_points[-1]]
    line_pts = [to_xy(lat, lon) for lat, lon in sampled]
    if len(line_pts) >= 2:
        draw.line(line_pts, fill=ROUTE_COLOR, width=ROUTE_WIDTH, joint="curve")

    start_x, start_y = to_xy(track_points[0][0], track_points[0][1])
    r = 5
    draw.ellipse(
        (start_x - r, start_y - r, start_x + r, start_y + r),
        fill="#ffffff",
        outline=ROUTE_COLOR,
        width=2,
    )

    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()


def png_route_map_data_uri(track_points: list[tuple[float, float]]) -> str | None:
    raw = png_route_map(track_points)
    if not raw:
        return None
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def html_route_map_embed(track_points: list[tuple[float, float]], *, height: int = 220) -> str:
    """Static map for shared HTML: OSM screenshot PNG, else minimal SVG polyline."""
    if len(track_points) < 2:
        return ""

    data_uri = png_route_map_data_uri(track_points)
    if data_uri:
        return (
            f'<div class="map-wrap">'
            f'<img class="route-map-img" src="{data_uri}" width="100%" height="{height}" '
            f'alt="Activity route map" loading="lazy" decoding="async"/>'
            f"</div>"
        )

    static_map = svg_route_map(track_points, height=height)
    if static_map:
        return f'<div class="map-wrap">{static_map}</div>'
    return ""


LEAFLET_HEAD = """
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
"""


def html_route_map(track_points: list[tuple[float, float]], height: int = 220, map_id: str = "route-map") -> str:
    """Interactive map using Leaflet + OpenStreetMap tiles (no API key)."""
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
        attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a>"
      }}).addTo(map);
      var line = L.polyline({coords_js}, {{color: "#fc5200", weight: 4, opacity: 1}}).addTo(map);
      map.fitBounds({bounds_js}, {{padding: [14, 14]}});
      L.circleMarker(line.getLatLngs()[0], {{
        radius: 5, color: "#fc5200", weight: 2, fillColor: "#fff", fillOpacity: 1
      }}).addTo(map);
    }})();
    </script>"""
