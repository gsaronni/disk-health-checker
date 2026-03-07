# Migration Guide - Old to New Version

## What Changed

### OLD VERSION (Hardcoded)
```bash
# Had to edit the script itself
DISK_1_DEV="/dev/sdf"
DISK_1_NAME="Avicenna"
DISK_1_PATTERN="Temperature"

DISK_2_DEV="/dev/sdh"
DISK_2_NAME="Zimrilim"
DISK_2_PATTERN="Temp"
```

### NEW VERSION (Config File)
```bash
# Just edit disks.conf
/dev/sdf,Avicenna,Temperature
/dev/sdh,Zimrilim,Temp
```

---

## What Was Removed

**Lines 21-28 (Old hardcoded config):**
```bash
# Format: DISK_<n>_DEV and DISK_<n>_PATTERN
DISK_1_DEV="/dev/sdf"
DISK_1_NAME="Avicenna"
DISK_1_PATTERN="Temperature"

DISK_2_DEV="/dev/sdh"
DISK_2_NAME="Zimrilim"
DISK_2_PATTERN="Temp"
```

**Lines 70-75 (Old hardcoded header):**
```bash
if [ ! -f "$LOGFILE" ]; then
    echo "Timestamp,${DISK_1_NAME}_Temperature,${DISK_2_NAME}_Temperature" > "$LOGFILE"
    echo "Starting new temperature log..."
else
    echo "Resuming temperature logging..."
fi
```

**Lines 85-95 (Old hardcoded logging):**
```bash
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
```

---

## What Was Added

**Lines 10-51 (Config file reading):**
```bash
CONFIG_FILE="disks.conf"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    exit 1
fi

# Read disks from config file into arrays
declare -a DEVICES
declare -a NAMES
declare -a PATTERNS

while IFS=',' read -r device name pattern; do
    [[ "$device" =~ ^#.*$ ]] && continue  # Skip comments
    [[ -z "$device" ]] && continue         # Skip empty lines
    
    device=$(echo "$device" | xargs)       # Trim whitespace
    name=$(echo "$name" | xargs)
    pattern=$(echo "$pattern" | xargs)
    
    DEVICES+=("$device")
    NAMES+=("$name")
    PATTERNS+=("$pattern")
done < "$CONFIG_FILE"

# Display what was found
echo "Found ${#DEVICES[@]} disk(s) to monitor:"
for i in "${!DEVICES[@]}"; do
    echo "  - ${NAMES[$i]} (${DEVICES[$i]})"
done
```

**Lines 88-93 (Dynamic header generation):**
```bash
# Build CSV header dynamically
HEADER="Timestamp"
for name in "${NAMES[@]}"; do
    HEADER="${HEADER},${name}_Temperature"
done
echo "$HEADER" > "$LOGFILE"
```

**Lines 107-143 (Dynamic temperature collection):**
```bash
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

# Check if at least one valid temp
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
fi
```

---

## Key Benefits

### Before (Limited to 2 disks):
- Had to edit script for different disks
- Fixed to exactly 2 disks
- No easy way to add/remove disks

### After (Unlimited disks):
- Edit `disks.conf` only
- Supports 1 to N disks
- Add/remove disks without touching code

---

## How to Use

1. **Edit `disks.conf`** with your disks:
   ```
   /dev/sda,SystemDrive,Temperature_Celsius
   /dev/sdb,BackupDrive,Temp
   /dev/sdc,DataDrive,Temperature_Celsius
   ```

2. **Run the script:**
   ```bash
   sudo ./monitor-temp.sh
   ```

3. **Output shows what it found:**
   ```
   Found 3 disk(s) to monitor:
     - SystemDrive (/dev/sda)
     - BackupDrive (/dev/sdb)
     - DataDrive (/dev/sdc)
   
   Logging every 10 seconds. Press Ctrl+C to stop.
   14:30:15 - SystemDrive: 35°C BackupDrive: 34°C DataDrive: 36°C
   ```

---

## Backwards Compatibility

**The old CSV files still work!** The analyze-temp.py script reads column headers dynamically, so it works with both:
- Old: `Timestamp,Avicenna_Temperature,Zimrilim_Temperature`
- New: `Timestamp,SystemDrive_Temperature,BackupDrive_Temperature,DataDrive_Temperature`
