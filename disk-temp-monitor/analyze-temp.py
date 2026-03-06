#!/usr/bin/env python3
"""
Disk Temperature Analysis Tool
Visualizes temperature trends from monitor-temp.sh log files
"""

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()


def analyze_drive(data, temp_col):
    """Calculate statistics for a drive's temperature data"""
    temps = data[temp_col]
    max_temp = temps.max()
    
    # Find longest streak at max temperature
    is_max = temps == max_temp
    max_streak = 0
    current_streak = 0
    
    for at_max in is_max:
        if at_max:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    
    return {
        'avg': temps.mean(),
        'min': temps.min(),
        'max': temps.max(),
        'std': temps.std(),
        'max_streak_readings': max_streak,
        'time_at_max': (temps == max_temp).sum(),
        'time_above_35': (temps > 35).sum(),
        'time_above_36': (temps > 36).sum(),
    }


def create_temp_graph(values, title, color="white", width=50, height=12):
    """Create a line graph showing actual temperature values"""
    if len(values) == 0:
        return Panel("No data", title=title)
    
    # Sample data to fit width
    if len(values) > width:
        step = len(values) // width
        values = values[::step][:width]
    
    min_temp = min(values)
    max_temp = max(values)
    temp_range = max_temp - min_temp if max_temp != min_temp else 1
    
    # Create graph lines
    lines = []
    
    # Temperature scale on left, graph on right
    for row in range(height):
        # Calculate temperature for this row
        row_temp = max_temp - (row / (height - 1)) * temp_range
        
        # Temperature scale
        temp_label = f"{row_temp:4.1f}°C │"
        
        # Graph line
        graph_line = ""
        for i, temp in enumerate(values):
            # Normalize temperature to row position
            normalized_pos = (max_temp - temp) / temp_range * (height - 1)
            
            if abs(normalized_pos - row) < 0.5:
                graph_line += "●"  # Data point
            elif i > 0:
                # Check if line should pass through this point
                prev_temp = values[i-1]
                prev_pos = (max_temp - prev_temp) / temp_range * (height - 1)
                
                if (min(normalized_pos, prev_pos) <= row <= max(normalized_pos, prev_pos)):
                    graph_line += "─"  # Line connector
                else:
                    graph_line += " "
            else:
                graph_line += " "
        
        lines.append(f"[{color}]{temp_label}{graph_line}[/{color}]")
    
    # Add bottom axis
    bottom_line = "     └" + "─" * len(values)
    lines.append(f"[{color}]{bottom_line}[/{color}]")
    
    return Panel("\n".join(lines), title=f"[{color}]{title}[/{color}]")


def main():
    # Read the log file
    try:
        data = pd.read_csv('temperature_log.csv', parse_dates=['Timestamp'])
    except FileNotFoundError:
        console.print("[red]Error: temperature_log.csv not found[/red]")
        console.print("Run monitor-temp.sh first to collect data")
        return
    
    # Get column names (they vary based on disk names)
    temp_cols = [col for col in data.columns if col.endswith('_Temperature')]
    
    if len(temp_cols) < 2:
        console.print("[red]Error: Expected 2 temperature columns in CSV[/red]")
        return
    
    # Convert to float
    for col in temp_cols:
        data[col] = data[col].astype(float)
    
    # Time range
    start_time = data['Timestamp'].min()
    end_time = data['Timestamp'].max()
    duration = end_time - start_time
    
    # Header info
    console.print(Panel.fit(
        f"[bold blue]Drive Temperature Monitoring[/bold blue]\n"
        f"Period: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}\n"
        f"Duration: {duration} | Readings: {len(data):,}"
    ))
    
    # Sample data for graphs (every Nth point for better resolution)
    sample_interval = max(1, len(data) // 100)
    sampled_data = data.iloc[::sample_interval]
    
    # Create graphs for both drives
    drive1_name = temp_cols[0].replace('_Temperature', '')
    drive2_name = temp_cols[1].replace('_Temperature', '')
    
    graph1 = create_temp_graph(
        sampled_data[temp_cols[0]].tolist(), 
        f"{drive1_name} Temperature", 
        "red"
    )
    
    graph2 = create_temp_graph(
        sampled_data[temp_cols[1]].tolist(), 
        f"{drive2_name} Temperature", 
        "yellow"
    )
    
    # Display graphs side by side
    console.print(Columns([graph1, graph2]))
    
    # Analyze both drives
    stats1 = analyze_drive(data, temp_cols[0])
    stats2 = analyze_drive(data, temp_cols[1])
    
    # Main stats table
    stats_table = Table(title="Temperature Analysis", show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan", width=20)
    stats_table.add_column(drive1_name, style="red", justify="right")
    stats_table.add_column(drive2_name, style="yellow", justify="right")
    
    stats_table.add_row("Average", f"{stats1['avg']:.1f}°C", f"{stats2['avg']:.1f}°C")
    stats_table.add_row("Minimum", f"{stats1['min']:.0f}°C", f"{stats2['min']:.0f}°C")
    stats_table.add_row("Maximum", f"{stats1['max']:.0f}°C", f"{stats2['max']:.0f}°C")
    stats_table.add_row("Std Deviation", f"{stats1['std']:.1f}°C", f"{stats2['std']:.1f}°C")
    stats_table.add_row("Time at Max", f"{stats1['time_at_max']} readings", f"{stats2['time_at_max']} readings")
    stats_table.add_row("Max Temp Streak", f"{stats1['max_streak_readings']} readings", f"{stats2['max_streak_readings']} readings")
    stats_table.add_row("Readings > 35°C", f"{stats1['time_above_35']}", f"{stats2['time_above_35']}")
    stats_table.add_row("Readings > 36°C", f"{stats1['time_above_36']}", f"{stats2['time_above_36']}")
    
    console.print(f"\n")
    console.print(stats_table)
    
    # Temperature distribution
    console.print(f"\n[bold]Temperature Distribution:[/bold]")
    for col in temp_cols:
        drive_name = col.replace('_Temperature', '')
        temps = data[col]
        temp_counts = temps.value_counts().sort_index()
        console.print(f"[bold]{drive_name}:[/bold] ", end="")
        for temp, count in temp_counts.items():
            pct = (count / len(temps)) * 100
            if pct > 5:  # Only show temps that happen >5% of the time
                console.print(f"{temp:.0f}°C({pct:.1f}%) ", end="")
        console.print()


if __name__ == "__main__":
    main()
