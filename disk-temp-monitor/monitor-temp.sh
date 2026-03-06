#!/bin/bash

# Disk Temperature Monitor - Real-time logging with rotation
# Tracks SMART temperature data for specified disks over time

# Configuration
LOGFILE="temperature_log.csv"
BACKUP_DIR="temp_logs_backup"
MAX_FILE_SIZE=50000000  # 50MB in bytes
INTERVAL=10             # Log every 10 seconds

# Read disks from config file
# declare -A DISKS
# while IFS=',' read -r device name pattern; do
#     [[ "$device" =~ ^#.*$ ]] && continue  # Skip comments
#     DISKS["$device"]="$name|$pattern"
# done < disks.conf
#
# # Build CSV header dynamically
# HEADER="Timestamp"
# for device in "${!DISKS[@]}"; do
#     IFS='|' read -r name pattern <<< "${DISKS[$device]}"
#     HEADER="${HEADER},${name}_Temperature"
# done
#
# Format: DISK_<n>_DEV and DISK_<n>_PATTERN
DISK_1_DEV="/dev/sdf"
DISK_1_NAME="Avicenna"
DISK_1_PATTERN="Temperature"

DISK_2_DEV="/dev/sdh"
DISK_2_NAME="Zimrilim"
DISK_2_PATTERN="Temp"

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
    echo "Timestamp,${DISK_1_NAME}_Temperature,${DISK_2_NAME}_Temperature" > "$LOGFILE"
    echo "Starting new temperature log..."
else
    echo "Resuming temperature logging..."
fi

echo "Logging every ${INTERVAL} seconds. Press Ctrl+C to stop."
echo "Log file: $LOGFILE"
echo ""

# Main logging loop
while true; do
    # Rotate log if needed
    rotate_log
    
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    DISK_1_TEMP=$(get_temp "$DISK_1_DEV" "$DISK_1_PATTERN")
    DISK_2_TEMP=$(get_temp "$DISK_2_DEV" "$DISK_2_PATTERN")
    
    # Only log if we got at least one valid temperature
    if [ "$DISK_1_TEMP" != "N/A" ] || [ "$DISK_2_TEMP" != "N/A" ]; then
        echo "$TIMESTAMP,$DISK_1_TEMP,$DISK_2_TEMP" >> "$LOGFILE"
        echo "$(date +%H:%M:%S) - ${DISK_1_NAME}: ${DISK_1_TEMP}°C, ${DISK_2_NAME}: ${DISK_2_TEMP}°C"
    else
        echo "$(date +%H:%M:%S) - Warning: Could not read temperatures"
    fi
    
    sleep "$INTERVAL"
done
