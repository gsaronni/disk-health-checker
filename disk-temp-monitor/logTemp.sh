#!/bin/bash

# Log file
LOGFILE="temperature_log.csv"

# Write header to the log file
echo "Timestamp,Avicenna_Temperature,Zimrilim_Temperature" > $LOGFILE

# Infinite loop to log every second
while true; do
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    AVICENNA_TEMP=$(smartctl -a /dev/sdf | grep Temperature | awk 'END {print $10}')
    ZIMRILIM_TEMP=$(smartctl -a /dev/sdh | grep Temp | awk 'END {print $10}')
    
    # Append the data to the log file
    echo "$TIMESTAMP,$AVICENNA_TEMP,$ZIMRILIM_TEMP" >> $LOGFILE
    
    # Wait for 1 second
    sleep 1
done

