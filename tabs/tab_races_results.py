import streamlit as st
import pandas as pd
import sql_queries as sql
from actions import utils_ui as ui

def show(conn):
    st.title("🏅 Race Results")
    st.markdown("A gallery of my past race achievements and official results.")

    df = conn(sql.get_all_races_query())
    df = df.fillna("")

    df_running = df[df["sport"].str.contains("Running|Trail", case=False)]
    df_tri = df[df["sport"].str.contains("Triathlon", case=False)]

    # Tabs for sports
    sport_tab1, sport_tab2 = st.tabs(["🏊🚴🏃 Triathlon", "🏃 Running / Trail"])

    with sport_tab1:
        if not df_tri.empty:
            for _, row in df_tri.iterrows():
                with st.container(border=True):
                    st.markdown(f"### {row['name']}")
                    st.markdown(f"**Date:** {row['date']} | **Location:** {row['location']} | **Bib:** {row['bib']}")
                    
                    m_cols = st.columns(4)
                    with m_cols[0]: ui.metric_card("Finish Time", row['duration'], icon="⏱️")
                    with m_cols[1]: ui.metric_card("Overall Rank", f"{row['ranking']}/{row['nb_athletes']}", icon="🏆")
                    with m_cols[2]: ui.metric_card("Category Rank", f"{row['ranking_category']}", icon="📊")
                    with m_cols[3]: ui.metric_card("Gender Rank", f"{row['ranking_gender']}", icon="♂️")

                    with st.expander("🔍 Split Breakdown"):
                        s_cols = st.columns(4)
                        with s_cols[0]:
                            st.write("**Swim**")
                            st.write(f"{row['swimming']} ({row['swim_pace']})")
                        with s_cols[1]:
                            st.write("**Transition**")
                            st.write(f"T1: {row['t1']} | T2: {row['t2']}")
                        with s_cols[2]:
                            st.write("**Bike**")
                            st.write(f"{row['cycling']} ({row['cycling_pace']})")
                        with s_cols[3]:
                            st.write("**Run**")
                            st.write(f"{row['running']} ({row['running_pace']})")
                        
                        st.markdown(f"[🔗 View Official Results]({row['link']})")
        else:
            st.info("No triathlon results found.")

    with sport_tab2:
        if not df_running.empty:
            for _, row in df_running.iterrows():
                with st.container(border=True):
                    st.markdown(f"### {row['name']}")
                    st.markdown(f"**Date:** {row['date']} | **Location:** {row['location']} | **Bib:** {row['bib']}")
                    
                    m_cols = st.columns(4)
                    with m_cols[0]: ui.metric_card("Finish Time", row['duration'], icon="⏱️")
                    with m_cols[1]: ui.metric_card("Overall Rank", f"{row['ranking']}/{row['nb_athletes']}", icon="🏆")
                    with m_cols[2]: ui.metric_card("Category Rank", f"{row['ranking_category']}", icon="📊")
                    with m_cols[3]: ui.metric_card("Gender Rank", f"{row['ranking_gender']}", icon="♂️")

                    with st.expander("🔍 Details"):
                        st.write(f"**Pace:** {row['running_pace']}")
                        st.markdown(f"[🔗 View Official Results]({row['link']})")
        else:
            st.info("No running results found.")
