# Quick Setup Guide

## 5-Minute Setup

### 1. Find Your Disks

```bash
# List all disks
lsblk

# Check if disk has SMART support
sudo smartctl -i /dev/sda
```

### 2. Identify Temperature Attribute Name

```bash
# Look for temperature line
sudo smartctl -a /dev/sda | grep -i temp

# Common patterns you'll see:
# Temperature_Celsius
# Current Drive Temperature  
# Temp
```

### 3. Edit Configuration

Open `monitor-temp.sh` and update lines 10-17:

```bash
# Example for two SATA drives
DISK_1_DEV="/dev/sda"
DISK_1_NAME="SystemDrive"
DISK_1_PATTERN="Temperature_Celsius"

DISK_2_DEV="/dev/sdb"
DISK_2_NAME="BackupDrive"  
DISK_2_PATTERN="Temperature_Celsius"
```

### 4. Install Python Dependencies

```bash
pip3 install pandas rich
```

### 5. Start Monitoring

```bash
sudo ./monitor-temp.sh
```

Let it run for at least 10-15 minutes to collect meaningful data.

### 6. Analyze Results

```bash
python3 analyze-temp.py
```

---

## Common Setups

### Single SSD + Single HDD
```bash
DISK_1_DEV="/dev/sda"
DISK_1_NAME="NVMe_SSD"
DISK_1_PATTERN="Temp"

DISK_2_DEV="/dev/sdb"
DISK_2_NAME="Backup_HDD"
DISK_2_PATTERN="Temperature_Celsius"
```

### Two SSDs
```bash
DISK_1_DEV="/dev/sda"
DISK_1_NAME="System_SSD"
DISK_1_PATTERN="Temp"

DISK_2_DEV="/dev/sdb"
DISK_2_NAME="Data_SSD"
DISK_2_PATTERN="Temp"
```

### Two HDDs (RAID setup)
```bash
DISK_1_DEV="/dev/sda"
DISK_1_NAME="RAID_Disk1"
DISK_1_PATTERN="Temperature_Celsius"

DISK_2_DEV="/dev/sdb"
DISK_2_NAME="RAID_Disk2"
DISK_2_PATTERN="Temperature_Celsius"
```

---

## Troubleshooting

**"Could not read temperatures"**
- Wrong device path? Check with `lsblk`
- Wrong grep pattern? Check with `sudo smartctl -a /dev/sdX | grep -i temp`
- Disk spun down? Wake it up: `sudo hdparm -C /dev/sdX`

**"Permission denied"**
- Need sudo: `sudo ./monitor-temp.sh`

**Script won't start**
- Make executable: `chmod +x monitor-temp.sh`
- Check shebang: First line should be `#!/bin/bash`

---

## Tips

- **Logging interval:** Default is 10 seconds. Edit `INTERVAL=10` in the script
- **Log file size:** Default rotation at 50MB. Edit `MAX_FILE_SIZE=50000000`
- **Stop logging:** Press Ctrl+C (will save cleanly)
- **Background logging:** `sudo ./monitor-temp.sh > /dev/null 2>&1 &`
