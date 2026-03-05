# Quick Generic Landing Page for Disk Utilities Repo

```markdown
# Disk Monitoring Utilities

> Practical CLI tools for disk health monitoring and temperature tracking in homelab environments.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What's This?

Two complementary tools for keeping your disks alive:

### 🏥 [Disk Health Checker](./disk-health-checker/)
**SMART attribute analyzer with actionable diagnostics**

Tells you *what's wrong* and *what to do about it* - not just raw SMART dumps.

```bash
sudo ./disk-health-checker.py
# ❌ /dev/sda: REPLACE WITHIN 24-48H (Load_Cycle_Count exhausted)
# ⚠️  /dev/sdc: Monitor weekly, plan replacement in 1-3 months
```

**Use case:** Monthly checkups, pre-backup verification, SSH-only servers

---

### 🌡️ [Temperature Monitor](./disk-temp-monitor/)
**Real-time temperature logging with trend analysis**

Tracks drive temps over time with automatic log rotation and Rich terminal visualizations.

```bash
sudo ./logTempImproved.sh  # Start logging
python3 plotTempRich.py    # Analyze trends
```

**Use case:** Thermal stress testing, cooling system validation, long-running workload monitoring

---

## Quick Start

```bash
git clone https://github.com/yourusername/disk-utilities.git
cd disk-utilities

# Install dependencies
pip3 install rich pandas

# Run health check
cd disk-health-checker
sudo ./disk-health-checker.py

# Start temperature logging
cd ../disk-temp-monitor
sudo ./logTempImproved.sh
```

---

## Why These Exist

I needed CLI tools that work on:
- Offline backup servers (boot 12 days/year)
- SSH-only access (no web UIs)
- Quick diagnostics during maintenance windows

Web-based monitoring (Scrutiny, Grafana) is great for always-on infrastructure. These tools handle the edge cases.

---

## Project Structure

```
disk-utilities/
├── disk-health-checker/     # SMART analysis & diagnostics
│   ├── disk-health-checker.py
│   ├── README.md
│   └── docs/
└── disk-temp-monitor/       # Temperature logging & visualization
    ├── logTempImproved.sh   # Data collection
    ├── plotTempRich.py      # Terminal graphs
    ├── README.md
    └── disks.conf.example
```

---

## Requirements

- Linux with `smartmontools` installed
- Python 3.8+ with `rich` library
- Root/sudo access for SMART data
- Pandas (temperature monitor only)

---

## License

MIT - Use however you want. No warranties. Don't blame me if your disk dies.

---

## Related

Part of my homelab automation toolkit:
- [network-automation-toolkit](https://github.com/yourusername/network-automation-toolkit) - F5 patching, multi-vendor backups
- [homelab-infrastructure](https://github.com/yourusername/homelab-infrastructure) - Docker Compose stacks

---

**Built for homelab nerds who prefer terminals over dashboards.**
```
