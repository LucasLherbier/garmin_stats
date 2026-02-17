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
    seconds = int(seconds)
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
        template="plotly_dark"
    )

    # Modern bar styling
    fig.update_traces(
        marker_line_width=0,
        opacity=0.9,
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{customdata}<extra></extra>",
        customdata=activity_duration_data["FormattedDuration"]
    )

    # Layout enhancements
    fig.update_layout(
        title=dict(
            text=f"Training Volume by {granularity.capitalize()}",
            font=dict(size=20, family="Outfit")
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
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
        bargap=0.15
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

    st.plotly_chart(fig, width='stretch', key=f"volume_chart_{uuid.uuid4()}")

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
        "8_weeks": "Latest 8 Weeks",
        "6_months": "Last 6 Months",
        "ytd": "Year to Date",
        "all": "All Time"
    }.get(time_range_key, time_range_key)

    # Build area chart
    fig = px.area(
        running_data,
        x="Week",
        y=y_column,
        title=f"{sport_name.capitalize()} by Week ({time_range_label})",
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
    st.plotly_chart(fig, width='stretch')
    
    
    
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
    
    Parameters
    ----------
    df : pd.DataFrame
    display_columns : dict
        Mapping {column_name → display_label}
    column_configuration : dict or None
        Config for st.dataframe()
    page_size : int
        Number of rows per page
    session_key : str
        Unique key for session_state pagination + table
    
    Returns
    -------
    paginated_df : pd.DataFrame
    selected_row : dict or None
    """

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
    selected_rows = st.dataframe(
        paginated_df,
        column_config=column_configuration,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )
    # Extract selected row
    selected_index = (
        selected_rows["selection"]["rows"][0]
        if selected_rows and selected_rows.get("selection", {}).get("rows")
        else None
    )

    # -----------------------------------
    # Pagination Controls
    # -----------------------------------
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])

    with col1:
        if st.button("⏪ First", width='stretch',
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] = 1
            st.rerun()

    with col2:
        if st.button("← Prev", width='stretch',
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align:center;margin-top:7px;'><strong>{st.session_state[page_key]} / {total_pages}</strong></div>",
            unsafe_allow_html=True
        )

    with col4:
        if st.button("Next →", width='stretch',
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] += 1
            st.rerun()

    with col5:
        if st.button("Last ⏩", width='stretch',
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()

    return paginated_df, selected_index
