import streamlit as st
import pandas as pd
from datetime import timedelta
import sql_queries as sql
from utils_gcp import query_bigquery
import os
import sys

# Custom tab imports
import tabs.tab_swimming as tab_swimming
import tabs.tab_cycling as tab_cycling
import tabs.tab_running as tab_running
import tabs.tab_race as tab_race
import tabs.tab_overview as tab_overview
import tabs.tab_stats as tab_stats
import tabs.tab_races_results as tab_races_results

# Set page config
st.set_page_config(
    page_title="Garmin Dash",
    page_icon="⌚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Helper Functions
def format_duration(seconds):
    if seconds is None:
        return "N/A"
    return str(timedelta(seconds=seconds)).split(".")[0]

def main():
    # Load assets
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        load_css(css_path)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; font-family: \"Outfit\", sans-serif; letter-spacing: 0.05em;'>NAVIGATION</h2>", unsafe_allow_html=True)
        st.markdown("<div style='height: 2px; background: linear-gradient(to right, #3b82f6, #10b981); margin: 10px 40px 25px 40px; border-radius: 2px;'></div>", unsafe_allow_html=True)
        
        tab = st.radio(
            "Select Dashboard",
            ["📊 Stats", "🏡 Overview", "🏃‍♂️ Run", "🏊‍♂️ Swim", "🚴‍♂️ Bike", "🎯 Race Training", "🏅 Race Results"],
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)
        
        with st.expander("✨ PRO TIPS", expanded=True):
            st.markdown("""
            <div style='font-size: 0.9rem; color: #94a3b8;'>
            • Click <b>Activities</b> in tables to see detailed telemetry.<br><br>
            • Use the <b>Stats</b> tab for all-time records across sports.<br><br>
            • <b>Race Training</b> tracks your progress toward specific goals.
            </div>
            """, unsafe_allow_html=True)


    # --- Content Rendering ---
    container = st.container()
    with container:
        if tab == "🏡 Overview":
            tab_overview.show(query_bigquery)
        elif tab == "🏊‍♂️ Swim":
            tab_swimming.show(query_bigquery)
        elif tab == "🚴‍♂️ Bike":
            tab_cycling.show(query_bigquery)
        elif tab == "🏃‍♂️ Run":
            tab_running.show(query_bigquery)
        elif tab == "🎯 Race Training":
            tab_race.show(query_bigquery)
        elif tab == "📊 Stats":
            tab_stats.show(query_bigquery)
        elif tab == "🏅 Race Results":
            tab_races_results.show(query_bigquery)

if __name__ == "__main__":
    main()

