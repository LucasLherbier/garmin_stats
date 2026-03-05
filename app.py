import streamlit as st
import pandas as pd
from datetime import timedelta
from utils import sql_queries as sql
from utils.utils_gcp import query_bigquery
import os
import sys
from streamlit_option_menu import option_menu

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
    initial_sidebar_state="collapsed"
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

    # --- Top Navigation Bar ---
    st.markdown("<div class='garmin-title-spacer'></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='garmin-title'>GARMIN ANALYTICS</h1>", unsafe_allow_html=True)
    st.markdown("<div class='garmin-title-divider'></div>", unsafe_allow_html=True)
    
    # Navigation buttons
    nav_options = ["Stats", "Overview", "Run", "Swim", "Bike", "Race", "Results"]
    icons = ["bar-chart-line-fill", "grid-3x3-gap-fill", "speedometer2", "water", "bicycle", "flag-fill", "trophy-fill"]

    selected_tab = option_menu(
        menu_title=None,
        options=nav_options,
        icons=icons,
        menu_icon="cast", 
        default_index=0, 
        orientation="horizontal",
        styles={
            "menu": {
                "background-color": "transparent !important",
            },
            "nav": {
                "background-color": "transparent !important", # Removes inner black bars
            },
            "container": {
                "padding": "5px !important", 
                "background-color": "rgba(15, 23, 42, 0.4)", # Your glass effect
                "border-radius": "18px",
                "border": "1px solid rgba(255, 255, 255, 0.1)",
                "backdrop-filter": "blur(20px)",
                "width": "100%",          
                "margin": "0 auto"
            },
            "icon": {"color": "#fdb927", "font-size": "17px"}, 
            "nav-link": {
                "font-family": "'Inter', 'Segoe UI', sans-serif",
                "font-size": "16px", 
                "font-weight": "500",
                "text-transform": "none",
                "letter-spacing": "0",
                "color": "#94a3b8",
                "border-radius": "14px",
                "transition": "all 0.3s ease",
            },
            "nav-link-selected": {
                "font-family": "'Inter', 'Segoe UI', sans-serif",
                "background": "linear-gradient(135deg, #551e82 0%, #3d1560 100%)",
                "color": "#ffffff",
                "font-weight": "600",
                "text-transform": "none",
                "letter-spacing": "0",
                "text-shadow": "0 2px 4px rgba(0,0,0,0.3)",
                "box-shadow": "0 8px 15px rgba(85, 30, 130, 0.35)",
                "border": "1px solid #fdb927",
            },
        }
    )

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("<h3 class='sidebar-title'>EXTRAS</h3>", unsafe_allow_html=True)
        with st.expander("✨ PRO TIPS", expanded=True):
            st.markdown("""
            <div class='pro-tips-content'>
            • Click <b>Activities</b> in tables to see detailed telemetry.<br><br>
            • Use the <b>Stats</b> tab for all-time records across sports.<br><br>
            • <b>Race Training</b> tracks your progress toward specific goals.
            </div>
            """, unsafe_allow_html=True)


    # --- Content Rendering ---
    if selected_tab == "Overview":
        tab_overview.show(query_bigquery)
    elif selected_tab == "Swim":
        tab_swimming.show(query_bigquery)
    elif selected_tab == "Bike":
        tab_cycling.show(query_bigquery)
    elif selected_tab == "Run":
        tab_running.show(query_bigquery)
    elif selected_tab == "Race":
        tab_race.show(query_bigquery)
    elif selected_tab == "Stats":
        tab_stats.show(query_bigquery)
    elif selected_tab == "Results":
        tab_races_results.show(query_bigquery)

if __name__ == "__main__":
    main()

