#!/bin/bash

# Disk Temperature Monitor - Real-time logging with rotation
# Tracks SMART temperature data for specified disks over time

# Configuration
LOGFILE="temperature_log.csv"
BACKUP_DIR="temp_logs_backup"
MAX_FILE_SIZE=50000000  # 50MB in bytes
INTERVAL=10             # Log every 10 seconds
CONFIG_FILE="disks.conf"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    echo "Create it with format: device_path,friendly_name,grep_pattern"
    echo "Example:"
    echo "  /dev/sda,SystemDrive,Temperature_Celsius"
    echo "  /dev/sdb,BackupDrive,Temp"
    exit 1
fi

# Read disks from config file into arrays
declare -a DEVICES
declare -a NAMES
declare -a PATTERNS

while IFS=',' read -r device name pattern; do
    # Skip comments and empty lines
    [[ "$device" =~ ^#.*$ ]] && continue
    [[ -z "$device" ]] && continue
    
    # Trim whitespace
    device=$(echo "$device" | xargs)
    name=$(echo "$name" | xargs)
    pattern=$(echo "$pattern" | xargs)
    
    DEVICES+=("$device")
    NAMES+=("$name")
    PATTERNS+=("$pattern")
done < "$CONFIG_FILE"

# Check if we found any disks
if [ ${#DEVICES[@]} -eq 0 ]; then
    echo "Error: No disks found in $CONFIG_FILE"
    echo "Make sure file has format: device_path,friendly_name,grep_pattern"
    exit 1
fi

echo "Found ${#DEVICES[@]} disk(s) to monitor:"
for i in "${!DEVICES[@]}"; do
    echo "  - ${NAMES[$i]} (${DEVICES[$i]})"
done
echo ""

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

# Build CSV header dynamically
HEADER="Timestamp"
for name in "${NAMES[@]}"; do
    HEADER="${HEADER},${name}_Temperature"
done

# Create header only if file doesn't exist
if [ ! -f "$LOGFILE" ]; then
    echo "$HEADER" > "$LOGFILE"
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
    
    # Collect temperatures for all disks
    TEMPS=()
    DISPLAY_PARTS=()
    
    for i in "${!DEVICES[@]}"; do
        temp=$(get_temp "${DEVICES[$i]}" "${PATTERNS[$i]}")
        TEMPS+=("$temp")
        DISPLAY_PARTS+=("${NAMES[$i]}: ${temp}°C")
    done
    
    # Build CSV line
    CSV_LINE="$TIMESTAMP"
    for temp in "${TEMPS[@]}"; do
        CSV_LINE="${CSV_LINE},${temp}"
    done
    
    # Check if we got at least one valid temperature
    VALID_TEMP=false
    for temp in "${TEMPS[@]}"; do
        if [ "$temp" != "N/A" ]; then
            VALID_TEMP=true
            break
        fi
    done
    
    # Log and display
    if [ "$VALID_TEMP" = true ]; then
        echo "$CSV_LINE" >> "$LOGFILE"
        echo "$(date +%H:%M:%S) - ${DISPLAY_PARTS[*]}"
    else
        echo "$(date +%H:%M:%S) - Warning: Could not read any temperatures"
    fi
    
    sleep "$INTERVAL"
done
