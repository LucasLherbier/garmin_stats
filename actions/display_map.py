import xml.etree.ElementTree as ET
import folium
from streamlit_folium import st_folium
import streamlit as st

def display_gpx_map(gpx_file_path):
    # Parse the GPX file
    namespace = {'default': 'http://www.topografix.com/GPX/1/1', 'ns3': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'}
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

    # Create a Streamlit app
    st.title("GPX Track Viewer")

    # Create a map centered around the first track point
    if track_points:
        m = folium.Map(location=track_points[0], zoom_start=13)

        # Add track points to the map
        folium.PolyLine(track_points, color="blue", weight=2.5, opacity=1).add_to(m)

        # Display the map in the Streamlit app
        st_folium(m, width=700, height=500)
    else:
        st.write("No track points found.")
