import plotly.graph_objects as go
import pandas as pd
from actions import utils as ut

import pandas as pd
import numpy as np

def plot_running_bar(split_file_path):
    """
    Plot Avg Moving Pace per Split as a bar chart.
    Hover shows distance (converted to meters) and pace for each split.
    """
    # Convert pace to seconds for plotting
    df = pd.read_csv(split_file_path, delimiter=',')  # Use the correct delimiter
    df = df.iloc[:-1]  # Remove last row if it contains unwanted data
    df['Avg Moving Paces (s)'] = df['Avg Moving Paces'].apply(ut.pace_to_seconds)

    # Calculate the x positions for each bar
    x_positions = [0.5]
    for i in range(1, len(df)):
        x_positions.append(x_positions[i-1] + df['Distance'].iloc[i-1])

    # Create a bar for each split
    fig = go.Figure()

    # Add bars for each split
    for i, (split, distance, moving_pace, x_pos) in enumerate(zip(df['Split'], df['Distance'], df['Avg Moving Paces (s)'], x_positions)):
        fig.add_trace(go.Bar(
            x=[x_pos],
            y=[moving_pace],
            width=distance,
            name=f'Split {split}',  # We will remove this from the legend
            offset=0,
            marker_color='royalblue',  # Set a solid color for better contrast
            hovertext=f"Split: {split}<br>Distance: {distance*1000:.0f} meters<br>Pace: {df['Avg Moving Paces'].iloc[i]}",
            hoverinfo='text',
        ))

    # Add vertical lines between splits
    for x_pos in x_positions[1:]:  # Skip the first since it's the starting point
        fig.add_trace(go.Scatter(
            x=[x_pos, x_pos],
            y=[0, max(df['Distance'])],  # Length of the vertical line based on the max elevation
            mode='lines',
            line=dict(color='white', width=2),  # Make lines slightly thicker and white for contrast
            showlegend=False  # Don't add these lines to the legend
        ))

    # Dynamic y-axis range
    min_pace = df['Avg Moving Paces (s)'].min() * 0.9
    max_pace = df['Avg Moving Paces (s)'].quantile(0.90)  # 90th percentile
    # Add padding for better readability
    pace_padding = 5  # Padding in seconds
    yaxis_min = max(min_pace - pace_padding, 0)  # Avoid going below 0
    yaxis_max = max_pace + pace_padding

    # Custom y-axis ticks
    pace_step = 30
    y_ticks = list(range(int(yaxis_min), int(yaxis_max) + 1, pace_step))
    y_ticktext = [f"{int(m)//60:02d}:{int(m)%60:02d}" for m in y_ticks]

    # Update layout for better UX/UI
    fig.update_layout(
        title='Avg Moving Pace per Split',
        xaxis_title='Split (Distance)',
        yaxis_title='Avg Moving Pace (mm:ss)',
        bargap=0.2,  # Adjust gap between bars for a cleaner look
        barmode='overlay',
        xaxis=dict(
            tickvals=x_positions,
            ticktext=df['Split'],
            showgrid=True,  # Show grid lines for better readability
            gridcolor='lightgray',
            zeroline=False,  # Don't show the zero line
            tickfont=dict(size=14, color='black', family='Arial, sans-serif'),  # Ensure tick labels are readable
        ),
        yaxis=dict(
            tickvals=y_ticks,
            ticktext=y_ticktext,
            range=[yaxis_min, yaxis_max],
            showgrid=True,  # Show grid lines for better readability
            gridcolor='lightgray',
            zeroline=False,  # Don't show the zero line
            tickfont=dict(size=14, color='black', family='Arial, sans-serif'),  # Ensure y-axis ticks are readable
            title_font=dict(size=16, color='black', family='Arial, sans-serif', weight='bold'),  # Bold y-axis title
        ),
        plot_bgcolor='#f5f5f5',  # Change background color (light gray)
        paper_bgcolor='#f5f5f5',  # Paper background (light gray)
        showlegend=False,  # Remove the legend (since we don't need it for splits)
        hovermode='x unified',  # Unified hover for better UX
        font=dict(
            family='Arial, sans-serif',  # Use a clean font
            size=16,  # Increase the font size for better readability
            color='black',  # Strong black color for all text
        ),
        hoverlabel=dict(
            bgcolor='white',  # Set background color to white for hover text
            font=dict(
                color='black',  # Ensure hover text is readable
                size=14,  # Adjust font size of hover text
                family='Arial, sans-serif',
            ),
        ),
    )

    return fig


import pandas as pd
import plotly.graph_objects as go

def plot_swimming_bar(df):
    # Remove last row (Summary)
    df = df.iloc[:-1]
    # Convert pace to seconds if not already
    if 'Avg Pace_seconds' not in df.columns:
        def pace_to_seconds(pace_str):
            m, s = pace_str.split(':')
            return int(m)*60 + int(s)
        df['Avg Pace_seconds'] = df['Avg Pace'].apply(pace_to_seconds)

    # Separate main splits
    main_splits = df[~df['Split'].astype(str).str.contains(r'\.') & ~df['IsRest']]

    # Compute X positions: left edges and centers
    split_distances = main_splits['Distance'].tolist()
    x_start = [0]
    for d in split_distances[:-1]:
        x_start.append(x_start[-1] + d)
    x_positions = [s + d/2 for s, d in zip(x_start, split_distances)]  # bar centers
    bar_widths = [d * 0.9 for d in split_distances]  # leave 10% gap
    
    fig = go.Figure()

    for xpos, width, (_, row) in zip(x_positions, bar_widths, main_splits.iterrows()):
        fig.add_trace(go.Bar(
            x=[xpos],
            y=[row['Avg Pace_seconds']],
            width=width,
            marker=dict(color='royalblue', line=dict(color='white', width=1)),
            hovertext=f"Split: {row['Split']}<br>Distance: {row['Distance']} m<br>Avg Pace: {row['Avg Pace']}",
            hoverinfo='text'
        ))

    # ---------------------------------------
    # IMPROVED Y-AXIS TICKS
    # ---------------------------------------
    pace_values = main_splits['Avg Pace_seconds']
    print(pace_values.min())
    pace_min = pace_values.min()
    pace_max = pace_values.max()

    # More generous bounds to generate more ticks
    yaxis_min = max(pace_min - 10, 0)
    yaxis_max = pace_max + 2

    # Set ~6 ticks
    tickvals = list(range(int(yaxis_min), int(yaxis_max) + 1, 10))
    y_ticktext = [f"{m//60:02d}:{m%60:02d}" for m in tickvals]

    fig.update_layout(
        xaxis_title='Distance',
        yaxis_title='Avg Pace (mm:ss)',

        xaxis=dict(
            tickfont=dict(color="white"),
            title_font=dict(color="white"),
            zeroline=False,
            showgrid=True,
            gridcolor="#444444",
            tickangle=45
        ),

        yaxis=dict(
            
            tickformat="%M:%S",            # <-- show pace as mm:ss automatically
            tickfont=dict(color="white"),
            range=[yaxis_min, yaxis_max],
            tickvals=tickvals,
            ticktext=y_ticktext,

            title_font=dict(color="white"),
            zeroline=False,
            showgrid=True,
            gridcolor="#444444"
        ),

        plot_bgcolor="#1e1e1e",           # <-- elegant dark-gray background
        paper_bgcolor="#1e1e1e",

        font=dict(
            family='Arial, sans-serif',
            size=16,
            color='white'
        ),
        margin=dict(
            l=80,
            r=60,   # <-- Add space on the right
            t=60,
            b=10
        ),
        showlegend=False
    )

    return fig

