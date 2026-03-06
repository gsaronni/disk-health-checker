#!/bin/bash

# Configuration
LOGFILE="temperature_log.csv"
BACKUP_DIR="temp_logs_backup"
MAX_FILE_SIZE=50000000  # 50MB in bytes
INTERVAL=10             # Log every 10 seconds instead of 1

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to rotate log file
rotate_log() {
    if [ -f "$LOGFILE" ] && [ $(stat -f%z "$LOGFILE" 2>/dev/null || stat -c%s "$LOGFILE") -gt $MAX_FILE_SIZE ]; then
        BACKUP_NAME="$BACKUP_DIR/temperature_log_$(date +%Y%m%d_%H%M%S).csv"
        echo "Rotating log file to $BACKUP_NAME"
        mv "$LOGFILE" "$BACKUP_NAME"
        gzip "$BACKUP_NAME"  # Compress old logs
    fi
}

# Function to get temperature safely
get_temp() {
    local device=$1
    local grep_pattern=$2
    local temp=$(smartctl -a "$device" 2>/dev/null | grep "$grep_pattern" | awk 'END {print $10}')
    
    # Check if temp is a valid number
    if [[ "$temp" =~ ^[0-9]+$ ]]; then
        echo "$temp"
    else
        echo "N/A"  # Return N/A if can't read temperature
    fi
}

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "Stopping temperature logging..."
    exit 0
}

# Trap Ctrl+C for clean exit
trap cleanup INT

# Create header only if file doesn't exist
if [ ! -f "$LOGFILE" ]; then
    echo "Timestamp,Avicenna_Temperature,Zimrilim_Temperature" > "$LOGFILE"
    echo "Starting new temperature log..."
else
    echo "Resuming temperature logging..."
fi

echo "Logging every ${INTERVAL} seconds. Press Ctrl+C to stop."
echo "Log file: $LOGFILE"

# Main logging loop
while true; do
    # Rotate log if needed
    rotate_log
    
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    AVICENNA_TEMP=$(get_temp "/dev/sdf" "Temperature")
    ZIMRILIM_TEMP=$(get_temp "/dev/sdh" "Temp")
    
    # Only log if we got at least one valid temperature
    if [ "$AVICENNA_TEMP" != "N/A" ] || [ "$ZIMRILIM_TEMP" != "N/A" ]; then
        echo "$TIMESTAMP,$AVICENNA_TEMP,$ZIMRILIM_TEMP" >> "$LOGFILE"
        echo "$(date +%H:%M:%S) - Avicenna: ${AVICENNA_TEMP}°C, Zimrilim: ${ZIMRILIM_TEMP}°C"
    else
        echo "$(date +%H:%M:%S) - Warning: Could not read temperatures"
    fi
    
    sleep "$INTERVAL"
done
