from datetime import timedelta
import plotly.express as px
import streamlit as st
import uuid
from actions import utils as ut


def pace_to_seconds(pace):
    """Convert pace string (mm:ss) to seconds."""
    h, m, s = map(int, pace.split(':'))
    return m * 60 + s

def format_to_mmss(t):
    try:
        parts = t.split(':')
        s = int(float(parts[-1])) + int(parts[-2])*60
        return f"{s//60:02d}:{s%60:02d}"
    except:
        return "00:00"


def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def format_duration_delta(seconds):
    if seconds is None:
        return "0:00:00"
    sign = "+" if seconds > 0 else ""
    return f"{sign}{format_duration(abs(seconds))}"

def safe_format(value, fmt="{:.2f}", default="N/A"):
    if value is None:
        return default
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return default
    
    
def format_duration_no_days(seconds):
    if seconds is None:
        return "00:00:00"
    if isinstance(seconds, str) and ":" in seconds:
        return seconds
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return str(seconds)
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hours:02}:{minutes:02}:{sec:02}"

def plot_week_volume(activity_duration_data, granularity):
    if activity_duration_data.empty:
        st.warning("No activity data to plot.")
        return

    # Format durations for display
    activity_duration_data["FormattedDuration"] = activity_duration_data["Duration"].apply(format_duration_no_days)

    # Custom color map for sports to match dashboard theme
    sport_colors = {
        "running": "#3b82f6",  # Blue
        "cycling": "#10b981",  # Green
        "swimming": "#06b6d4", # Cyan
        "walking": "#f59e0b",  # Amber
        "hiking": "#8b5cf6",   # Violet
        "strength_training": "#ec4899", # Pink
        "other": "#94a3b8"     # Slate
    }

    # ----- TOTALS -----
    totals = (
        activity_duration_data.groupby("TimePeriod")["Duration"]
        .sum()
        .reset_index()
        .rename(columns={"Duration": "TotalDuration"})
    )
    totals["FormattedTotal"] = totals["TotalDuration"].apply(format_duration_no_days)
    
    # ----- BAR CHART -----
    fig = px.bar(
        activity_duration_data,
        x="TimePeriod",
        y="Duration",
        color="activityTypeGrouped",
        color_discrete_map=sport_colors,
        template="plotly_dark",
        custom_data=["FormattedDuration"]
    )

    # Modern bar styling
    fig.update_traces(
        marker_line_width=0,
        opacity=0.9,
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{customdata[0]}<extra></extra>"
    )

    # Layout enhancements
    fig.update_layout(
        title=dict(
            text=f"Total Volume ({granularity.capitalize()})",
            font=dict(size=20, family="Outfit")
        ),
        plot_bgcolor='rgba(255, 255, 255, 0.03)',
        paper_bgcolor='rgba(255, 255, 255, 0.03)',
        margin=dict(t=60, b=80, l=60, r=20),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            title=None,
            bgcolor='rgba(0,0,0,0)'
        ),
        xaxis=dict(
            title=None,
            showgrid=False,
            tickfont=dict(color="#94a3b8")
        ),
        yaxis=dict(
            title="Duration",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            tickfont=dict(color="#94a3b8")
        ),
        bargap=0.15,
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

    # Y-AXIS Ticks (HH:MM:SS)
    max_duration = int(totals["TotalDuration"].max() * 1.1)
    # Ensure at least 4 ticks
    step = max(3600, (max_duration // 4) // 3600 * 3600) 
    tickvals = list(range(0, max_duration + 1, step if step > 0 else 3600))
    ticktext = [format_duration_no_days(v) for v in tickvals]

    fig.update_yaxes(
        tickvals=tickvals,
        ticktext=ticktext,
        range=[0, max_duration]
    )

    # Add total labels above bars
    fig.add_scatter(
        x=totals["TimePeriod"],
        y=totals["TotalDuration"] + (max_duration * 0.02),
        text=totals["FormattedTotal"],
        mode="text",
        textfont=dict(color="#f8fafc", size=11, family="Inter"),
        showlegend=False,
        hoverinfo='skip'
    )

    st.plotly_chart(fig, width="stretch", key=f"volume_chart_{uuid.uuid4()}")

def plot_week_area(running_data, y_column, y_title, sport_name, time_range_key):
    """
    Creates a weekly area chart for running metrics.

    Parameters:
        running_data (pd.DataFrame): Data with columns ['Week', y_column]
        y_column (str): Name of the metric column (e.g., total_distance, total_duration)
        y_title (str): Y-axis label
        sport_name (str): Sport name for title
        time_range_key (str): Key from session_state.time_range_metrics
    """

    time_range_label = {
        "4_units": "Latest 4 Periods",
        "6_units": "Latest 6 Periods",
        "ytd": "Year to Date",
        "all": "All Time"
    }.get(time_range_key, time_range_key)

    # Build area chart
    fig = px.area(
        running_data,
        x="Week",
        y=y_column,
        title=f"{sport_name.capitalize()} Volume ({time_range_label})",
        labels={y_column: y_title},
        markers=True
    )

    # Conditional formatting
    if y_column == "total_distance":
        fig.update_traces(texttemplate='%{y:.2f}')
    else:
        fig.update_traces(texttemplate='%{y}')

    fig.update_traces(textposition='top center')

    # Render in Streamlit
    st.plotly_chart(fig, width="stretch")
    
    
    
from datetime import date, timedelta

def get_monday(d):
    return d - timedelta(days=d.weekday())

def compute_date_range(key):
    today = date.today()
    end = get_monday(today)

    if key == "8_weeks":
        start = end - timedelta(weeks=8)

    elif key == "6_months":
        # Approx 6 months = 26 weeks (close enough for rolling charts)
        start = end - timedelta(weeks=26)

    elif key == "ytd":
        start = get_monday(date(today.year, 1, 1))

    elif key == "all":
        start = get_monday(date(1970, 1, 1))

    else:
        start = None

    return start, end

import streamlit as st

def paginated_table(
    df,
    display_columns,
    column_configuration=None,
    page_size=10,
    session_key="table"
):
    """
    Reusable paginated dataframe component.

    Returns:
        paginated_df: current page (renamed display columns)
        page_index: selected row index on the current page (for paginated_df.iloc)
        global_index: selected row index in the input df (for df.iloc)
    """
    # Debug: Check Streamlit version
    # st.sidebar.info(f"Streamlit Version: {st.__version__}")

    # -----------------------------------
    # Filter available columns
    # -----------------------------------
    available_columns = {
        col: display_columns[col]
        for col in display_columns
        if col in df.columns
    }

    display_df = df[list(available_columns.keys())].rename(columns=display_columns)

    # -----------------------------------
    # Pagination logic
    # -----------------------------------
    total_pages = (len(display_df) + page_size - 1) // page_size

    page_key = f"{session_key}_page"
    table_key = f"{session_key}_dataframe"

    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    # Compute slice
    start = (st.session_state[page_key] - 1) * page_size
    end = start + page_size
    paginated_df = display_df.iloc[start:end]

    # -----------------------------------
    # Display dataframe
    # -----------------------------------
    # Selection is 1.35.0+ feature
    use_selection = False
    try:
        from packaging import version
        if version.parse(st.__version__) >= version.parse("1.35.0"):
            use_selection = True
    except:
        # Fallback to simple check
        try:
            v_parts = [int(x) for x in st.__version__.split('.')]
            if v_parts[0] > 1 or (v_parts[0] == 1 and v_parts[1] >= 35):
                use_selection = True
        except:
            pass

    if use_selection:
        try:
            selected_rows = st.dataframe(
                paginated_df,
                column_config=column_configuration,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=table_key,
            )
        except TypeError:
            # Final fallback if something is weird with the version
            st.dataframe(
                paginated_df,
                column_config=column_configuration,
                hide_index=True,
                key=table_key,
            )
            selected_rows = None
    else:
        st.dataframe(
            paginated_df,
            column_config=column_configuration,
            hide_index=True,
            key=table_key,
        )
        selected_rows = None
        # st.info("💡 Note: Row selection is only supported in Streamlit 1.35.0+.")

    # Extract selected row
    selected_index = None
    if selected_rows is not None and isinstance(selected_rows, dict):
        selection = selected_rows.get("selection", {})
        rows = selection.get("rows", [])
        if rows:
            selected_index = rows[0]

    # -----------------------------------
    # Pagination Controls
    # -----------------------------------
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])

    with col1:
        if st.button("⏪ First", width="stretch",
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] = 1
            st.rerun()

    with col2:
        if st.button("← Prev", width="stretch",
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align:center;margin-top:7px;'><strong>{st.session_state[page_key]} / {total_pages}</strong></div>",
            unsafe_allow_html=True
        )

    with col4:
        if st.button("Next →", width="stretch",
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] += 1
            st.rerun()

    with col5:
        if st.button("Last ⏩", width="stretch",
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()

    global_index = start + selected_index if selected_index is not None else None
    return paginated_df, selected_index, global_index
