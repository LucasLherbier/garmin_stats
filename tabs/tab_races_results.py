import streamlit as st
import pandas as pd

def show(conn):

    df = pd.read_sql_query("SELECT * FROM races ORDER BY date DESC", conn)
    df = df.fillna("")

    df_running = df[df["sport"].str.contains("Running|Trail", case=False)]
    df_tri = df[df["sport"].str.contains("Triathlon", case=False)]

    st.title("🏅 Race Results Dashboard")

    # ----- CSS for cards & layout ---------------------------------------
    st.markdown("""
        <style>
            .scroll-container {
                display: flex;
                overflow-x: auto;
                padding: 10px 0;
                gap: 20px;
            }
            .race-card {
                min-width: 420px;
                max-width: 420px;
                background: #ffffff10;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 15px;
                backdrop-filter: blur(4px);
            }
            .race-title {
                font-size: 1.4rem;
                font-weight: 700;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # ======================================================================
    #  SPORT SELECTOR (2 columns at top)
    # ======================================================================
    col1, col2 = st.columns(2)

    with col1:
        choose_tri = st.button("🏊🚴🏃 Triathlon", use_container_width=True)

    with col2:
        choose_run = st.button("🏃 Running / Trail", use_container_width=True)

    # Default: show triathlon
    selected = "triathlon"
    if choose_run:
        selected = "running"
    elif choose_tri:
        selected = "triathlon"

    st.write("---")

    # ======================================================================
    #  SELECTED SPORT RESULTS
    # ======================================================================

    if selected == "triathlon":

        st.header("🏊🚴🏃 Triathlon Races")

        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)

        for _, row in df_tri.iterrows():

            st.markdown(
                f'<div class="race-title">{row["date"]} – {row["name"]}</div>',
                unsafe_allow_html=True
            )

            col_main, col_button = st.columns([8, 2])

            with col_main:
                st.markdown(f"""
                <div style="font-size: 1.2rem; line-height: 1.4; margin-top:5px"">
                    📍 {row['location']} &nbsp;&nbsp;
                    🎽 Bib {row['bib']} &nbsp;&nbsp;
                    🏁 {row['distance']} &nbsp;&nbsp; 
                    <span style="font-size: 1.4rem; font-weight: 700; color:#FFD700;">
                        ⏱ {row['duration']} &nbsp;&nbsp; 
                        🏆 Rank {row['ranking']}/{row['nb_athletes']}
                    </span>
                    &nbsp;&nbsp; | &nbsp;&nbsp; 
                    📊 #{row['ranking_category']} {row['category']} &nbsp;&nbsp;
                    ♂️ #{row['ranking_gender']} Male &nbsp;&nbsp; | 
                    <a href="{row['link']}" target="_blank">🔗 Results</a>
                </div>
                """, unsafe_allow_html=True)

            with col_button:
                with st.expander("More details"):
                    st.table(pd.DataFrame({
                        "Split": ["Swim", "Swim Pace", "T1", "Bike", "Bike Pace", "T2", "Run", "Run Pace"],
                        "Value": [
                            row["swimming"],
                            row["swim_pace"],
                            row["t1"],
                            row["cycling"],
                            row["cycling_pace"],
                            row["t2"],
                            row["running"],
                            row["running_pace"]
                        ]
                    }).set_index("Split"))
                st.markdown('</div>', unsafe_allow_html=True)



        st.markdown('</div>', unsafe_allow_html=True)

    # ======================================================================
    # RUNNING SECTION
    # =====================================================================
    else:
        st.header("🏃 Running & Trail Races")

        st.markdown('<div class="scroll-container">', unsafe_allow_html=True)

        for _, row in df_running.iterrows():

            # Race title
            st.markdown(f'<div class="race-title">{row["date"]} – {row["name"]}</div>', unsafe_allow_html=True)

            # Two columns: main info + details expander
            col_main, col_button = st.columns([8, 2])

            with col_main:
                st.markdown(f"""
                <div style="font-size: 1.15rem; line-height: 1.4;">
                📍 {row['location']} &nbsp;&nbsp;
                🎽 Bib {row['bib']} &nbsp;&nbsp;
                🏁 {row['distance']} &nbsp;&nbsp;
                <span style="font-size: 1.5rem; font-weight: 700; color:#FFD700;">⏱ {row['duration']}</span>
                &nbsp;&nbsp; | &nbsp;&nbsp;
                🏆 {row['ranking']}/{row['nb_athletes']} &nbsp;&nbsp; | &nbsp;&nbsp;
                📊 {row['category']} (#{row['ranking_category']}) &nbsp;&nbsp; | &nbsp;&nbsp;
                ♂️ #{row['ranking_gender']} Male &nbsp;&nbsp; | &nbsp;&nbsp;
                <a href="{row['link']}" target="_blank">🔗 Official Results</a>
                </div>
                """, unsafe_allow_html=True)


            with col_button:
                with st.expander("More details"):
                    st.table(pd.DataFrame({
                        "Split": ["Running Time", "Running Pace"],
                        "Value": [row["running"], row["running_pace"]]
                    }).set_index("Split"))

            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
