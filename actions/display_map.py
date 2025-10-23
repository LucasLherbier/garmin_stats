import folium
import streamlit as st
from streamlit_folium import st_folium
import xml.etree.ElementTree as ET

def display_gpx_map(gpx_file_path):
    # Parse the GPX file
    tree = ET.parse(gpx_file_path)
    root = tree.getroot()

    # Define the namespace for GPX files
    namespace = {'ns': 'http://www.topografix.com/GPX/1/1'}

    # Extract track points
    track_points = []
    for trkpt in root.findall('.//ns:trkpt', namespace):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        track_points.append([lat, lon])

    if not track_points:
        st.write("No track points found.")
        return

    # Create a map centered on the first track point
    m = folium.Map(location=track_points[0], zoom_start=12)

    # Add the track to the map
    folium.PolyLine(track_points, color="blue", weight=2.5, opacity=1).add_to(m)

    # Display the map in Streamlit
    st_folium(m, width=700, height=500)

# Streamlit app
st.title("GPX File Viewer")
gpx_file = st.file_uploader("Upload a GPX file", type="gpx")

if gpx_file is not None:
    display_gpx_map(gpx_file)
