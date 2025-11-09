# pace_bar_plot.py
import plotly.graph_objects as go
import pandas as pd

def pace_to_seconds(pace):
    """Convert pace string (mm:ss) to seconds."""
    h, m, s = map(int, pace.split(':'))
    return m * 60 + s

def plot_pace_bar(split_file_path):
    """
    Plot Avg Moving Pace per Split as a bar chart.
    Hover shows distance and pace for each split.
    """
    # Convert pace to seconds for plotting
    df = pd.read_csv(split_file_path, delimiter=',')  # Use the correct delimiter
    df = df.iloc[:-1]
    df['Avg Moving Paces (s)'] = df['Avg Moving Paces'].apply(pace_to_seconds)

    # Calculate the x positions for each bar
    x_positions = [0.5]
    for i in range(1, len(df)):
        x_positions.append(x_positions[i-1] + df['Distance'].iloc[i-1])

    # Create a bar for each split
    fig = go.Figure()
    for i, (split, distance, elevation, x_pos) in enumerate(zip(df['Split'], df['Distance'], df['Avg Moving Paces (s)'], x_positions)):
        fig.add_trace(go.Bar(
            x=[x_pos],
            y=[elevation],
            width=distance,
            name=f'Split {split}',
            offset=0,
            marker_color='royalblue',
            hovertext=f"Distance: {distance}<br>Pace: {df['Avg Moving Paces'].iloc[i]}",
            hoverinfo='text',
        ))

    # Custom y-axis ticks
    min_pace = df['Avg Moving Paces (s)'].min()
    max_pace = df['Avg Moving Paces (s)'].max()
    pace_step = 30
    y_ticks = list(range(int(min_pace), int(max_pace) + 1, pace_step))
    y_ticktext = [f"{int(m)//60:02d}:{int(m)%60:02d}" for m in y_ticks]

    # Update layout
    fig.update_layout(
        title='Avg Moving Pace per Split (Bar Width = Distance)',
        xaxis_title='Split (Distance)',
        yaxis_title='Avg Moving Pace (mm:ss)',
        bargap=0,
        barmode='overlay',
        xaxis=dict(tickvals=x_positions, ticktext=df['Split']),
        yaxis=dict(tickvals=y_ticks, ticktext=y_ticktext),
    )

    return fig
