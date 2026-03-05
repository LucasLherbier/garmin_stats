import plotly.graph_objects as go
import pandas as pd
from actions import utils as ut

import pandas as pd
import numpy as np

def plot_running_bar(split_input):
    """
    Plot Avg Moving Pace per Split as a bar chart.
    Hover shows distance (converted to meters) and pace for each split.
    """
    # Convert pace to seconds for plotting
    if isinstance(split_input, str):
        df = pd.read_csv(split_input, delimiter=',')
    else:
        df = split_input.copy()
    
    # Filter out summary row if it exists
    df = df[df['Split'] != 'Summary']
    
    df['Avg Moving Paces (s)'] = df['Avg Moving Paces'].apply(ut.pace_to_seconds)

    # Calculate the x positions for each bar
    x_positions = [0]
    for i in range(1, len(df)):
        x_positions.append(x_positions[i-1] + df['Distance'].iloc[i-1])
    
    # Bar centers for labels
    bar_centers = [x + d/2 for x, d in zip(x_positions, df['Distance'])]

    # Create a bar for each split
    fig = go.Figure()

    # Add bars for each split
    fig.add_trace(go.Bar(
        x=bar_centers,
        y=df['Avg Moving Paces (s)'],
        width=df['Distance'],
        marker=dict(
            color='royalblue',
            line=dict(color='white', width=1)
        ),
        hovertext=[f"Split: {s}<br>Distance: {d*1000:.0f}m<br>Pace: {p}" 
                  for s, d, p in zip(df['Split'], df['Distance'], df['Avg Moving Paces'])],
        hoverinfo='text',
    ))

    # Dynamic y-axis range
    pace_vals = df['Avg Moving Paces (s)']
    min_p = pace_vals.min()
    max_p = pace_vals.max()
    
    yaxis_min = max(min_p - 15, 0)
    yaxis_max = max_p + 15

    # Ticks every 30s
    tick_step = 30 if (yaxis_max - yaxis_min) > 60 else 15
    y_ticks = list(range(int(yaxis_min), int(yaxis_max) + 1, tick_step))
    y_ticktext = [f"{int(m)//60:02d}:{int(m)%60:02d}" for m in y_ticks]

    # Update layout for better UX/UI
    fig.update_layout(
        title=dict(text='Avg Moving Pace per Split', font=dict(size=20, color='white')),
        xaxis_title='Distance (km)',
        yaxis_title='Pace (mm:ss)',
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=False,
            tickfont=dict(color='white'),
            title_font=dict(color='white')
        ),
        yaxis=dict(
            tickvals=y_ticks,
            ticktext=y_ticktext,
            range=[yaxis_min, yaxis_max],
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=False,
            tickfont=dict(color='white'),
            title_font=dict(color='white')
        ),
        plot_bgcolor='#1e1e1e',
        paper_bgcolor='#1e1e1e',
        showlegend=False,
        hovermode='closest',
        font=dict(family='Arial, sans-serif', size=14, color='white'),
        margin=dict(l=60, r=30, t=50, b=50),
        height=400
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
            try:
                if not pace_str or ":" not in str(pace_str):
                    return 0
                parts = str(pace_str).split(':')
                if len(parts) == 2:
                    m, s = parts
                    return int(float(m))*60 + int(float(s))
                return 0
            except (ValueError, TypeError):
                return 0
        df['Avg Pace_seconds'] = df['Avg Pace'].apply(pace_to_seconds)

    # Separate main splits
    if 'IsRest' not in df.columns:
        df['IsRest'] = df['Split'].astype(str).str.upper().str.contains("REST")
        
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

