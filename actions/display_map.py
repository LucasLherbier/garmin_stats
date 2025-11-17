import xml.etree.ElementTree as ET
import folium
from streamlit_folium import st_folium
import streamlit as st

def display_gpx_map(gpx_file_path):
    # Parse the GPX file
    namespace = {
        'default': 'http://www.topografix.com/GPX/1/1',
        'ns3': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
    }
    tree = ET.parse(gpx_file_path)
    root = tree.getroot()

    # Extract track points
    track_points = []
    for trk in root.findall('default:trk', namespace):
        for trkseg in trk.findall('default:trkseg', namespace):
            for trkpt in trkseg.findall('default:trkpt', namespace):
                lat = float(trkpt.attrib['lat'])
                lon = float(trkpt.attrib['lon'])
                track_points.append((lat, lon))

    st.title("GPX Track Viewer")

    if track_points:
        # Center the map on the middle point of the track
        mid_index = len(track_points) // 2
        center_lat, center_lon = track_points[mid_index]

        # Use full width of the Streamlit container
        m = folium.Map(location=(center_lat, center_lon), zoom_start=13, width='100%', height='600')

        # Add track to the map
        folium.PolyLine(track_points, color="blue", weight=2.5, opacity=1).add_to(m)

        # Fit the map to the track bounds
        m.fit_bounds(track_points)

        # Display map
        st_folium(m, width="100%", height=600)
    else:
        st.warning("No track points found.")
