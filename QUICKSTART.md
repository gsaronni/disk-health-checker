# Quick Setup Guide

## Health Checker — no config, works immediately

```bash
sudo bin/disk-health-checker.py           # full report
sudo bin/disk-health-checker.py -v        # verbose (all attributes)
sudo bin/disk-health-checker.py -q        # summary only
sudo bin/disk-health-checker.py --json    # structured snapshot to stdout
```

`rich` is optional (`pip3 install rich --break-system-packages`) — the script falls back to plain text with the same structure if it's not installed.

---

## Temperature Monitor — 5-Minute Setup

### 1. Find Your Disks

```bash
lsblk
sudo smartctl -i /dev/sda
```

### 2. Identify Temperature Attribute Name

```bash
sudo smartctl -a /dev/sda | grep -i temp

# Common patterns:
# Temperature_Celsius   (Seagate, WD)
# Temp                  (Samsung SSD)
# Current Drive Temperature (Intel SSD)
```

### 3. Configure Disks

```bash
cp etc/disks.conf.template etc/disks.conf
$EDITOR etc/disks.conf
```

Format is `device_path,friendly_name,grep_pattern`, one disk per line:

```
/dev/sda,SystemDrive,Temperature_Celsius
/dev/sdb,BackupDrive,Temp
```

### 4. Start Monitoring

```bash
sudo bin/monitor-temp.sh
```

Let it run for at least 10-15 minutes to collect meaningful data. Output goes to `temperature_log.csv` in the directory you ran it from (gitignored — this is generated data, not something to commit).

### 5. Analyze Results (optional)

```bash
pip3 install -r analysis/requirements.txt --break-system-packages
python3 analysis/analyze-temp.py
```

Skip this step for quick spot-checks — it's an optional extra, not required for logging to work.

---

## Common `etc/disks.conf` Setups

**Single SSD + Single HDD:**
```
/dev/sda,NVMe_SSD,Temp
/dev/sdb,Backup_HDD,Temperature_Celsius
```

**Two SSDs:**
```
/dev/sda,System_SSD,Temp
/dev/sdb,Data_SSD,Temp
```

**RAID array (any number of disks):**
```
/dev/sda,RAID_Disk1,Temperature_Celsius
/dev/sdb,RAID_Disk2,Temperature_Celsius
/dev/sdc,RAID_Disk3,Temperature_Celsius
```

---

## Troubleshooting

**"Could not read temperatures"**
- Wrong device path? Check with `lsblk`
- Wrong grep pattern? Check with `sudo smartctl -a /dev/sdX | grep -i temp`
- Disk spun down? Wake it: `sudo hdparm -C /dev/sdX`

**"Permission denied"**
- SMART data needs root: `sudo bin/monitor-temp.sh`

**Script won't start**
- Executable bit: `chmod +x bin/monitor-temp.sh bin/disk-health-checker.py`
- Shebang check: first line of `monitor-temp.sh` should be `#!/bin/bash`

**`disk-health-checker.py` can't import `smart_parser`**
- It resolves `lib/` relative to its own location (`bin/../lib`), so it must stay two levels under the repo root as laid out in the Project Structure section of the main README — don't run a copy of just `bin/disk-health-checker.py` on its own without `lib/` alongside it.

---

## Tips

- **Logging interval:** 10s default, edit `INTERVAL=10` in `bin/monitor-temp.sh`
- **Log rotation:** 50MB default, edit `MAX_FILE_SIZE=50000000`
- **Stop logging:** Ctrl+C (clean shutdown, trapped)
- **Background logging:** `sudo bin/monitor-temp.sh > /dev/null 2>&1 &`
- **Health check in a cron/monitoring context:** rely on the exit code (`0`/`1`/`2`), not stdout parsing — that's what it's for