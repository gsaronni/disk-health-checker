import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()

# Read your data
data = pd.read_csv('temperature_log.csv', parse_dates=['Timestamp'])
data['Avicenna_Temperature'] = data['Avicenna_Temperature'].astype(float)
data['Zimrilim_Temperature'] = data['Zimrilim_Temperature'].astype(float)

# Time range
start_time = data['Timestamp'].min()
end_time = data['Timestamp'].max()
duration = end_time - start_time

# Header info
console.print(Panel.fit(f"[bold blue]Drive Temperature Monitoring[/bold blue]\n"
                       f"Period: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}\n"
                       f"Duration: {duration} | Readings: {len(data):,}"))

# Enhanced stats function
def analyze_drive(temp_col):
    temps = data[temp_col]
    max_temp = temps.max()
    
    # Find longest streak at max temp
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
        'max_streak_seconds': max_streak,
        'time_at_max': (temps == max_temp).sum(),
        'time_above_35': (temps > 35).sum(),
        'time_above_36': (temps > 36).sum(),
    }

# Create proper line graph with temperature scale
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

# Sample data for graphs (every 200th point for better resolution)
sample_interval = max(1, len(data) // 100)
sampled_data = data.iloc[::sample_interval]

# Create both graphs
avicenna_graph = create_temp_graph(
    sampled_data['Avicenna_Temperature'].tolist(), 
    "Avicenna Temperature", 
    "red"
)

zimrilim_graph = create_temp_graph(
    sampled_data['Zimrilim_Temperature'].tolist(), 
    "Zimrilim Temperature", 
    "yellow"
)

# Display graphs side by side
console.print(Columns([avicenna_graph, zimrilim_graph]))

# Analyze both drives
avicenna_stats = analyze_drive('Avicenna_Temperature')
zimrilim_stats = analyze_drive('Zimrilim_Temperature')

# Main stats table
stats_table = Table(title="Temperature Analysis", show_header=True, header_style="bold magenta")
stats_table.add_column("Metric", style="cyan", width=20)
stats_table.add_column("Avicenna", style="red", justify="right")
stats_table.add_column("Zimrilim", style="yellow", justify="right")

stats_table.add_row("Average", f"{avicenna_stats['avg']:.1f}°C", f"{zimrilim_stats['avg']:.1f}°C")
stats_table.add_row("Minimum", f"{avicenna_stats['min']:.0f}°C", f"{zimrilim_stats['min']:.0f}°C")
stats_table.add_row("Maximum", f"{avicenna_stats['max']:.0f}°C", f"{zimrilim_stats['max']:.0f}°C")
stats_table.add_row("Std Deviation", f"{avicenna_stats['std']:.1f}°C", f"{zimrilim_stats['std']:.1f}°C")
stats_table.add_row("Time at Max", f"{avicenna_stats['time_at_max']}s", f"{zimrilim_stats['time_at_max']}s")
stats_table.add_row("Max Temp Streak", f"{avicenna_stats['max_streak_seconds']}s", f"{zimrilim_stats['max_streak_seconds']}s")
stats_table.add_row("Time > 35°C", f"{avicenna_stats['time_above_35']}s", f"{zimrilim_stats['time_above_35']}s")
stats_table.add_row("Time > 36°C", f"{avicenna_stats['time_above_36']}s", f"{zimrilim_stats['time_above_36']}s")

console.print(f"\n")
console.print(stats_table)

# Temperature distribution
console.print(f"\n[bold]Temperature Distribution:[/bold]")
for drive, temps in [("Avicenna", data['Avicenna_Temperature']), ("Zimrilim", data['Zimrilim_Temperature'])]:
    temp_counts = temps.value_counts().sort_index()
    console.print(f"[bold]{drive}:[/bold] ", end="")
    for temp, count in temp_counts.items():
        pct = (count / len(temps)) * 100
        if pct > 5:  # Only show temps that happen >5% of the time
            console.print(f"{temp:.0f}°C({pct:.1f}%) ", end="")
    console.print()
