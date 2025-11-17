import streamlit as st
import pandas as pd
import sqlite3
from datetime import timedelta
import sql_queries as sql

import plotly.express as px
import tabs.tab_swimming as tab_swimming
import tabs.tab_cycling as tab_cycling
import tabs.tab_running as tab_running
import tabs.tab_race as tab_race
import tabs.tab_overview as tab_overview

import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "activities.db")
conn = sqlite3.connect(db_path)
st.set_page_config(layout="wide")

# --- Helper Functions ---
def format_duration(seconds):
    if seconds is None:
        return "N/A"
    return str(timedelta(seconds=seconds)).split(".")[0]

# --- Main App ---
def main():
    # Connect to SQLite DB
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    st.title("Garmin Activity Dashboard")

    # Load data
    #df = pd.read_sql("SELECT * FROM activities", conn)

    # Sidebar filters
    st.sidebar.header("Filters")
    filter_type = st.sidebar.selectbox(
        "Filter by", ["week", "month", "year", "race"]
    )
    filter_value = st.sidebar.text_input(f"Enter {filter_type} (e.g., '2025-09-08' for week)")

    # Apply filter condition for SQL
    filter_condition = f"{filter_type} = '{filter_value}'" if filter_value else "1=1"

    # Sidebar tabs
    st.sidebar.header("Tabs")
    tab = st.sidebar.radio("Select Tab", ["Overview","Running", "Swimming", "Cycling", "Race"])

    if tab == "Overview":
        tab_overview.show(conn)
    elif tab == "Swimming":
        tab_swimming.show(conn)
    elif tab == "Cycling":
        tab_cycling.show(conn)
    elif tab == "Running":
        # Time range selector for running distance chart (main panel)
        tab_running.show(conn)
    elif tab == "Race":
        # Time range selector for running distance chart (main panel)
        tab_race.show(conn)


if __name__ == "__main__":
    main()
