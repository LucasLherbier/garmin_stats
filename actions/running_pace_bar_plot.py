import plotly.graph_objects as go
import pandas as pd
from actions import utils as ut

def plot_pace_bar(split_file_path):
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
