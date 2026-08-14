# Disk Temperature Monitor

> Real-time SMART temperature logging with trend analysis and Rich terminal visualization.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 The Problem

I needed to validate cooling performance during extended disk workloads:

- **Thermal stress testing** - Scrub operations, RAID rebuilds, large file transfers
- **Cooling validation** - After adding case fans or adjusting airflow
- **Long-term trends** - Temperature patterns over days/weeks
- **Multi-disk comparison** - Which drives run hotter under load?

**Existing solutions:**
- `smartctl` requires manual polling - no trend tracking
- Web dashboards (Scrutiny, Grafana) overkill for ad-hoc testing
- Basic `watch` commands provide no historical data

---

## 🛠️ Solution

Two complementary scripts:

### 1. `monitor-temp.sh` - Data Collection
- Polls SMART temperature every 10 seconds
- Automatic log rotation at 50MB
- Clean Ctrl+C handling
- Error validation (handles missing/sleeping disks)

### 2. `analyze-temp.py` - Visualization  
- Rich terminal graphs with temperature scale
- Statistical analysis (avg, min, max, std deviation)
- Detects sustained high-temperature periods
- Distribution analysis (time spent at each temp)

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip3 install pandas rich

# Make scripts executable
chmod +x monitor-temp.sh analyze-temp.py
```

### Configuration

Edit `monitor-temp.sh` lines 10-17 with your disk paths:

```bash
DISK_1_DEV="/dev/sda"
DISK_1_NAME="SystemDrive"
DISK_1_PATTERN="Temperature"

DISK_2_DEV="/dev/sdb"
DISK_2_NAME="BackupDrive"
DISK_2_PATTERN="Temp"
```

**Finding your disk patterns:**
```bash
sudo smartctl -a /dev/sda | grep -i temp
# Look for: Temperature_Celsius, Current Drive Temperature, etc.
```

### Usage

**Start logging:**
```bash
sudo ./monitor-temp.sh
# Logging every 10 seconds. Press Ctrl+C to stop.
# 14:30:15 - SystemDrive: 35°C, BackupDrive: 34°C
```

**Analyze data:**
```bash
python3 analyze-temp.py
```

---

## 📊 Example Output

```
╔══════════════════════════════════════════════════════════════════════╗
║              Drive Temperature Monitoring                            ║
║    Period: 2026-03-05 14:30 to 2026-03-06 08:45                     ║
║    Duration: 18:15:00 | Readings: 6,540                              ║
╚══════════════════════════════════════════════════════════════════════╝

 37.0°C │●─────●●●●●●─────────────────────────────────────
 36.5°C │ ●●●●●        ●●●●●●●●●●●●●●●●●●●●────────────────
 36.0°C │                                    ●●●●●●●●●●●●●●●

┌─────────────────── Temperature Analysis ───────────────────┐
│ Metric             │   SystemDrive │   BackupDrive │
├────────────────────┼───────────────┼───────────────┤
│ Average            │         36.2°C│         35.8°C│
│ Maximum            │           37°C│           37°C│
│ Readings > 35°C    │          4523 │          3892 │
└────────────────────┴───────────────┴───────────────┘
```

---

## 💡 Use Cases

### Thermal Stress Testing
Run during RAID scrub operations:
```bash
# Terminal 1: Start monitoring
sudo ./monitor-temp.sh

# Terminal 2: Start scrub
sudo mdadm --action=check /dev/md0

# Terminal 3: Watch real-time temps
watch -n 5 'tail -1 temperature_log.csv'
```

### Cooling System Validation
Before/after adding case fans:
```bash
# Before: Log for 24 hours
sudo ./monitor-temp.sh

# Add fans, wait 30 min for thermal equilibrium

# After: Analyze difference
python3 analyze-temp.py
```

### Long-term Monitoring
Track seasonal temperature changes:
```bash
# Cron job: Log every hour for a week
0 * * * * /path/to/monitor-temp.sh & sleep 600 && pkill -f monitor-temp.sh
```

---

## 🧬 Evolution

### v1: Basic Prototype (deleted)
**What it did:**
- Logged to CSV every second
- Hardcoded disk paths
- No error handling

**Problems:**
- Logs grew to 100MB+ in hours
- No graceful shutdown (corrupted CSVs)
- Failed silently when disks spun down

### v2: Production-Ready (`monitor-temp.sh`)
**Improvements:**
- Automatic log rotation at 50MB
- Error handling and validation
- Configurable polling interval (10s default)
- Clean Ctrl+C handling with trap
- Progress feedback in terminal

**Lessons learned:**
- Log rotation is essential for long-running monitors
- Validation prevents garbage data from sleeping disks
- User feedback matters (show current temps while logging)

### v3: Analysis Tools (`analyze-temp.py`)
**What changed:**
- Added Rich library for terminal graphs
- Statistical analysis (not just raw dumps)
- Detects sustained high-temp events
- Distribution analysis

**Why it matters:**
- Graphs show trends instantly (vs Excel import)
- Statistical analysis identifies cooling issues
- Works over SSH (no GUI needed)

---

## 🔧 Technical Notes

### Log File Format
```csv
Timestamp,Disk1_Temperature,Disk2_Temperature
2026-03-06 14:30:00,35,34
2026-03-06 14:30:10,35,34
```

### Log Rotation Behavior
- Checks file size before each write
- Rotates at 50MB (configurable)
- Compresses old logs with gzip
- Format: `temperature_log_20260306_143000.csv.gz`

### SMART Attribute Patterns
Different manufacturers use different attribute names:
- **Seagate/WD:** `Temperature_Celsius`
- **Samsung SSD:** `Temp`
- **Intel SSD:** `Current Drive Temperature`

Check your disk: `sudo smartctl -a /dev/sdX | grep -i temp`

### Sampling for Graphs
`analyze-temp.py` samples data for visualization:
- Max 100 points displayed (clear graphs)
- Uses every Nth reading to cover full timespan
- Raw data preserved in CSV

---

## 📋 Requirements

- Linux with `smartmontools` installed
- Python 3.8+
- Root/sudo access (SMART data requires privileges)
- Dependencies: `pandas`, `rich`

**Install smartmontools:**
```bash
# Debian/Ubuntu
sudo apt install smartmontools

# RHEL/CentOS
sudo yum install smartmontools

# Arch
sudo pacman -S smartmontools
```

---

## 🐛 Troubleshooting

### "Could not read temperatures"
- Check disk paths: `ls -l /dev/sd*`
- Verify SMART support: `sudo smartctl -i /dev/sdX`
- Try different grep patterns (see Technical Notes)

### "Permission denied"
- SMART data requires root: `sudo ./monitor-temp.sh`

### Graphs show flat lines
- Data range too narrow (all same temp)
- Check CSV has valid numeric data
- Verify logging interval vs data duration

---

## 📜 License

MIT License - Use however you want. Monitor your disks responsibly.

---

## 🔗 Related Projects

Part of my disk monitoring toolkit:
- [Disk Health Checker](../disk-health-checker/) - SMART attribute analysis
- [Disk Utilities](../) - Collection overview

---

**Built for thermal validation during homelab maintenance.**
