import pandas as pd
import plotext as plt

# Read your data
data = pd.read_csv('temperature_log.csv', parse_dates=['Timestamp'])
data['Avicenna_Temperature'] = data['Avicenna_Temperature'].astype(float)
data['Zimrilim_Temperature'] = data['Zimrilim_Temperature'].astype(float)

print(f"Loaded {len(data)} temperature readings")
print(f"Time range: {data['Timestamp'].min()} to {data['Timestamp'].max()}")

# Create hourly averages for cleaner graph
data['Hour'] = data['Timestamp'].dt.floor('H')
hourly = data.groupby('Hour').agg({
    'Avicenna_Temperature': 'mean',
    'Zimrilim_Temperature': 'mean'
}).reset_index()

print(f"\nHourly averages ({len(hourly)} data points):")

plt.clear_data()
plt.plot(hourly['Avicenna_Temperature'].tolist(), label='Avicenna')
plt.plot(hourly['Zimrilim_Temperature'].tolist(), label='Zimrilim')
plt.title('Hourly Average Temperatures')
plt.xlabel('Hours from start')
plt.ylabel('Temperature (°C)')
plt.plotsize(120, 30)  # Bigger plot
plt.show()

# Also show a simple trend of last 100 readings
print(f"\nLast 100 readings trend:")
recent = data.tail(100)

plt.clear_data()
plt.plot(recent['Avicenna_Temperature'].tolist(), label='Avicenna')
plt.plot(recent['Zimrilim_Temperature'].tolist(), label='Zimrilim')
plt.title('Recent Temperature Trend (Last 100 readings)')
plt.xlabel('Recent samples')
plt.ylabel('Temperature (°C)')
plt.plotsize(120, 25)
plt.show()
