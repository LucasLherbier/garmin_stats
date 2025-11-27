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
    # Format durations for display
    activity_duration_data["FormattedDuration"] = activity_duration_data["Duration"].apply(format_duration_no_days)

    if activity_duration_data.empty:
        st.warning("No activity data to plot.")
        return

    # ----- TOTALS -----
    totals = (
        activity_duration_data.groupby("TimePeriod")["Duration"]
        .sum()
        .reset_index()
        .rename(columns={"Duration": "TotalDuration"})
    )
    totals["FormattedTotal"] = totals["TotalDuration"].apply(format_duration_no_days)
    total_map = dict(zip(totals["TimePeriod"], totals["FormattedTotal"]))

    # Calculate dynamic font size based on number of bars
    num_bars = len(totals["TimePeriod"])
    max_font = 18
    min_font = 8
    dynamic_font_size = max(min_font, min(max_font, int(110 / num_bars)))

    # ----- STACKED BAR -----
    fig = px.bar(
        activity_duration_data,
        x="TimePeriod",
        y="Duration",
        color="activityTypeGrouped",
        title=f"Activity Duration by {granularity}",
        labels={
            "TimePeriod": "Time Period",
            "Duration": "Duration",
            "activityTypeGrouped": "Sport"
        }
    )

    # Remove bar text, keep hover only
    for trace in fig.data:
        trace.text = None
        trace.customdata = activity_duration_data["FormattedDuration"]

    # ----- ADD TOTAL LABELS AT BOTTOM -----
    fig.add_scatter(
        x=totals["TimePeriod"],
        y=[totals["TotalDuration"].max() * 0.03] * len(totals),
        text=[f"<b>{t}</b>" for t in totals["FormattedTotal"]],
        mode="text",
        textfont=dict(color="black", size=dynamic_font_size),
        showlegend=False
    )

    for trace in fig.data:
        customdata_safe = trace.customdata if trace.customdata is not None else [""] * len(trace.x)
        # Create hover info combining total + segment duration
        hover_texts = [
            f"<b>Total: {total_map.get(x, '')}</b><br>{trace.name}: {cd}"
            for x, cd in zip(trace.x, customdata_safe)
        ]
        # Assign to customdata instead of text
        trace.customdata = hover_texts
        trace.hovertemplate = "%{customdata}<extra></extra>"

    # ----- Y-AXIS -----
    max_duration = int(totals["TotalDuration"].max() * 1.2)
    tickvals = list(range(0, max_duration + 1, 4 * 3600))
    ticktext = [format_duration_no_days(v) for v in tickvals]

    fig.update_yaxes(
        tickvals=tickvals,
        ticktext=ticktext,
        range=[0, max_duration],
        title="Duration (hh:mm:ss)"
    )

    st.plotly_chart(fig, key=f"activity_duration_chart_{uuid.uuid4()}")

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
    st.plotly_chart(fig)
    
    
    
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
        if st.button("⏪ First", use_container_width=True,
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] = 1
            st.rerun()

    with col2:
        if st.button("← Prev", use_container_width=True,
                     disabled=st.session_state[page_key] == 1):
            st.session_state[page_key] -= 1
            st.rerun()

    with col3:
        st.markdown(
            f"<div style='text-align:center;margin-top:7px;'><strong>{st.session_state[page_key]} / {total_pages}</strong></div>",
            unsafe_allow_html=True
        )

    with col4:
        if st.button("Next →", use_container_width=True,
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] += 1
            st.rerun()

    with col5:
        if st.button("Last ⏩", use_container_width=True,
                     disabled=st.session_state[page_key] >= total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()

    return paginated_df, selected_index
