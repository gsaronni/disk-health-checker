import pandas as pd
import matplotlib.pyplot as plt

# Read the log file
data = pd.read_csv('temperature_log.csv', parse_dates=['Timestamp'])

# Calculate the average temperature
data['Avicenna_Temperature'] = data['Avicenna_Temperature'].astype(float)
data['Zimrilim_Temperature'] = data['Zimrilim_Temperature'].astype(float)

# Plotting
plt.figure(figsize=(10, 5))
plt.plot(data['Timestamp'], data['Avicenna_Temperature'], label='Avicenna Temperature', color='blue')
plt.plot(data['Timestamp'], data['Zimrilim_Temperature'], label='Zimrilim Temperature', color='orange')
plt.xlabel('Timestamp')
plt.ylabel('Temperature (°C)')
plt.title('Temperature Monitoring')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

