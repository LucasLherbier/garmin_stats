import streamlit as st
import pandas as pd
from datetime import timedelta
from utils import sql_queries as sql 
import plotly.express as px
import uuid
from actions import utils as ut
from actions import utils_ui as ui
from utils.pipeline.preprocess_activities import TRAINING_RACE_PERIODS

def show(conn):
    st.title("🎯 Race Preparation")
    st.markdown("Monitor my training volume and intensity leading up to my goal races.")

    # Use centralized races definition
    races = TRAINING_RACE_PERIODS[::-1]

    # Race Selection
    race_options = [f"{race['race']} ({race['distance']})" for race in races]
    selected_race_display = st.selectbox("Select Target Race", race_options)
    
    # Find the selected race data
    selected_race_index = race_options.index(selected_race_display)
    selected_race_data = races[selected_race_index]

    # Current date for filtering future races
    today_dt = pd.Timestamp.now()
    # For metrics and distance graphs: only show up to today or race end
    analysis_end_date = min(today_dt, pd.to_datetime(selected_race_data['end'])).strftime('%Y-%m-%d')

    # Fetch race metrics (using truncated period if applicable)
    race_metrics = conn(sql.get_race_metrics_query(selected_race_data['start'], analysis_end_date))

    if not race_metrics.empty:
        st.write("### Preparation Summary")
        
        m_cols = st.columns(4)
        with m_cols[0]: ui.metric_card("Avg Weekly Duration", ut.format_duration(race_metrics['average_duration_per_week'].iloc[0]), icon="⏱️")
        with m_cols[1]: ui.metric_card("Total Swim", f"{race_metrics['total_distance_swim'].iloc[0] or 0:.0f} km", icon="🏊‍♂️")
        with m_cols[2]: ui.metric_card("Total Bike", f"{race_metrics['total_distance_bike'].iloc[0] or 0:.0f} km", icon="🚴‍♂️")
        with m_cols[3]: ui.metric_card("Total Run", f"{race_metrics['total_distance_run'].iloc[0] or 0:.0f} km", icon="🏃‍♂️")

        st.markdown("---")
        st.write("### Detailed Volume Breakdown")
        
        # Comparison metrics
        comp_cols = st.columns(3)
        with comp_cols[0]:
            ui.metric_card("Swim Weekly Avg", f"{race_metrics['average_week_distance_swim'].iloc[0] or 0:.1f} km", icon="🌊")
        with comp_cols[1]:
            ui.metric_card("Bike Weekly Avg", f"{race_metrics['average_week_distance_bike'].iloc[0] or 0:.1f} km", icon="🛣️")
        with comp_cols[2]:
            ui.metric_card("Run Weekly Avg", f"{race_metrics['average_week_distance_run'].iloc[0] or 0:.1f} km", icon="🏁")

        st.markdown("---")
        
        # Distance Metrics Table (Restored version)
        st.subheader("📊 Historical Prep Benchmarks")

        # Header row
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown("**Timeframe**")
        with col2: st.markdown("<div style='text-align: center;'><strong>🏊‍♂️ Swim</strong></div>", unsafe_allow_html=True)
        with col3: st.markdown("<div style='text-align: center;'><strong>🚴‍♂️ Bike</strong></div>", unsafe_allow_html=True)
        with col4: st.markdown("<div style='text-align: center;'><strong>🏃‍♂️ Run</strong></div>", unsafe_allow_html=True)

        rows = [
            ("Avg Weekly", "average_week_distance_swim", "average_week_distance_bike", "average_week_distance_run", "{:.1f}"),
            ("Avg (8W)", "average_8week_distance_swim", "average_8week_distance_bike", "average_8week_distance_run", "{:.1f}"),
            ("Avg Monthly", "average_month_distance_swim", "average_month_distance_bike", "average_month_distance_run", "{:.0f}")
        ]

        # Colors for each sport (transparent backgrounds)
        colors = ["rgba(56, 189, 248, 0.15)", "rgba(16, 185, 129, 0.15)", "rgba(59, 130, 246, 0.15)"]

        for label, swim_col, bike_col, run_col, fmt in rows:
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.markdown(f"**{label}**")
            
            vals = [race_metrics[swim_col].iloc[0], race_metrics[bike_col].iloc[0], race_metrics[run_col].iloc[0]]
            cols = [col2, col3, col4]
            
            for c, val, color in zip(cols, vals, colors):
                with c:
                    st.markdown(f"<div style='text-align: center; background-color: {color}; padding: 0.5rem; border-radius: 0.5rem; border: 1px solid rgba(255,255,255,0.1);'>{fmt.format(val or 0)}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Granularity selection
        st.subheader("📈 Distance Over Time")
        
        if 'granularity' not in st.session_state:
            st.session_state.granularity = 'week'
        
        g_cols = st.columns(4)
        if g_cols[0].button("📅 Week", use_container_width=True, type="primary" if st.session_state.granularity == 'week' else "secondary"):
            st.session_state.granularity = 'week'
            st.rerun()
        if g_cols[1].button("📆 Month", use_container_width=True, type="primary" if st.session_state.granularity == 'month' else "secondary"):
            st.session_state.granularity = 'month'
            st.rerun()

        granularity = st.session_state.granularity

        sports = [
            {'name': 'swimming', 'display': 'Swim', 'emoji': '🏊‍♂️', 'color': '#38bdf8'},
            {'name': 'cycling', 'display': 'Bike', 'emoji': '🚴‍♂️', 'color': '#10b981'}, 
            {'name': 'running', 'display': 'Run', 'emoji': '🏃‍♂️', 'color': '#3b82f6'}
        ]
        
        for sport in sports:
            sport_data = conn(sql.get_race_distance_by_timerange_query(
                selected_race_data['start'], analysis_end_date, granularity, sport['name']
            ))
            if not sport_data.empty:
                fig = px.area(sport_data, x="time_period", y="total_distance", markers=True, 
                             color_discrete_sequence=[sport['color']], template="plotly_dark")
                fig.update_layout(
                    title=dict(
                        text=f"{sport['emoji']} {sport['display']} Volume",
                        font=dict(size=18, family="Outfit")
                    ),
                    plot_bgcolor='rgba(255, 255, 255, 0.03)',
                    paper_bgcolor='rgba(255, 255, 255, 0.03)',
                    yaxis_title="Distance (km)",
                    xaxis_title=granularity.capitalize(),
                    margin=dict(t=50, b=40, l=60, r=20),
                    shapes=[dict(
                        type='rect',
                        xref='paper',
                        yref='paper',
                        x0=0,
                        y0=0,
                        x1=1,
                        y1=1,
                        line=dict(color='rgba(255, 255, 255, 0.1)', width=1)
                    )]
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.write("### ⏱️ Total Training Load")
        activity_duration_data = conn(sql.get_activity_duration_by_granularity_query(
            selected_race_data['start'], selected_race_data['end'], st.session_state.granularity
        ))
        if not activity_duration_data.empty:
            ut.plot_week_volume(activity_duration_data, st.session_state.granularity)
    else:
        st.warning("No preparation data available for this race period.")
