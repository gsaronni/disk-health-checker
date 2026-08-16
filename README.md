# Disk Toolkit

> SMART disk health analysis and temperature trend logging for homelab environments — CLI-first, built for SSH-only and offline-boot servers where a web dashboard doesn't help.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rich (optional)](https://img.shields.io/badge/rich-optional-purple.svg)](https://github.com/Textualize/rich)

---

## The Problem

[Scrutiny](https://github.com/AnalogJ/scrutiny) and similar web dashboards are excellent for always-on infrastructure, but they don't help when:

- A backup server boots only ~12 days/year — a full web stack + database is overkill for an occasional check
- Access is SSH-only over a mesh VPN, with no convenient path to a web UI
- `smartctl -a` output needs deep SMART knowledge to interpret — "VALUE=1" means nothing without context
- You need an answer *now*, during a maintenance window, not after 30 minutes of googling attribute IDs

Full background and the specific incident that triggered this: [`docs/01-problem-definition.md`](docs/01-problem-definition.md).

---

## Two Tools

### 🏥 Disk Health Checker — `bin/disk-health-checker.py`

Point-in-time SMART analysis with **actionable output**, not raw attribute dumps.

```bash
sudo bin/disk-health-checker.py
```
```
/dev/sda - ST500LT012-1DG142 (500 GB)
------------------------------------------------------------------------
Type: HDD | Power-On: 31,029h (3.5 years) | Temp: 25C
SMART Health: PASSED | Our Analysis: CRITICAL

!! Load_Cycle_Count (VALUE=1)
   |- Head parking mechanism exhausted - mechanical failure imminent
   `- Action: Replace within 1-4 weeks

--- SUMMARY ---------------------------------------------------------
Healthy   2 disk(s)
Warning   1 disk(s)
Critical  1 disk(s)

Action Required:
  !! /dev/sda: REPLACE WITHIN 24-48H
```
*(Output shown in plain-text form — colored when `rich` is available. See Requirements below.)*

- Auto-discovers all physical disks: SATA/SAS (numbered attribute table) and NVMe (named health block)
- Context-aware rules per attribute — Reallocated Sectors care about RAW value, Load Cycle Count cares about normalized VALUE, manufacturer quirks handled (Seagate `Raw_Read_Error_Rate` headroom check)
- Exit codes for automation: `0` healthy, `1` warning, `2` critical
- `--json` / `--json-out FILE` for a structured snapshot — not a history mechanism, just something to `jq` or diff by hand when you want it (see [`docs/03-design-decisions.md`](docs/03-design-decisions.md#json-export-format--✅-shipped))
- `rich` is optional — falls back to plain text with the same structure if unavailable, so it runs on hosts you don't control the Python environment on

**Use case:** monthly checkups, pre-backup verification, immediate assessment after a boot on an infrequently-powered server.

### 🌡️ Temperature Monitor — `bin/monitor-temp.sh` + `analysis/analyze-temp.py`

Continuous SMART temperature logging with rotation, plus optional trend visualization.

```bash
sudo bin/monitor-temp.sh
# Found 2 disk(s) to monitor:
#   - Avicenna (/dev/sdf)
#   - Zimrilim (/dev/sdh)
# 14:30:15 - Avicenna: 35°C, Zimrilim: 34°C
```

- Config-driven (`etc/disks.conf`, one line per disk — no editing the script itself)
- Automatic log rotation at 50MB, gzip-compressed
- `analysis/analyze-temp.py` (optional — needs `pandas` + `rich`, see below) renders terminal graphs and statistical summaries from the CSV

**Use case:** thermal stress testing during RAID scrubs/rebuilds, validating cooling changes, long-running workload monitoring.

---

## Project Structure

```
disk-toolkit/
├── bin/
│   ├── disk-health-checker.py   # point-in-time SMART analysis
│   └── monitor-temp.sh          # continuous temperature logger
├── lib/
│   └── smart_parser.py          # shared SATA + NVMe smartctl parsing
├── etc/
│   └── disks.conf.template      # copy to disks.conf, edit for your disks
├── analysis/                    # optional, deferred by design — see below
│   ├── analyze-temp.py
│   └── requirements.txt         # pandas + rich (separate from the core tool)
├── docs/
│   ├── 01-problem-definition.md
│   ├── 02-prompt-engineering.md
│   ├── 03-design-decisions.md
│   ├── 04-smart-attributes-explained.md
│   └── 05-temp-monitor-migration.md
├── examples/
│   └── disk-health-checker/     # sample output screenshots
├── QUICKSTART.md
├── CHANGELOG.md
└── LICENSE
```

**Why `analysis/` is separate:** `analyze-temp.py` needs `pandas` + `rich` and turns "run a script" into "manage a Python environment." For occasional spot-checks that's not worth it — `disk-health-checker.py --json` covers the "verify status in a specific surgical moment" case without an install step. Graphing stays available for when you actually want it, just not part of the default path.

---

## Quick Start

```bash
git clone <your-gitea-or-github-url> disk-toolkit
cd disk-toolkit

# Core dependency (optional — plain-text fallback if skipped)
pip3 install rich --break-system-packages

# Health check — no config needed, auto-discovers disks
sudo bin/disk-health-checker.py

# Temperature logging — needs config first
cp etc/disks.conf.template etc/disks.conf
$EDITOR etc/disks.conf   # one line per disk: /dev/sdX,FriendlyName,GrepPattern
sudo bin/monitor-temp.sh

# Optional: trend graphs from the logged CSV
pip3 install -r analysis/requirements.txt --break-system-packages
python3 analysis/analyze-temp.py
```

Full walkthrough: [`QUICKSTART.md`](QUICKSTART.md).

---

## 💡 AI-Assisted Development Showcase

This project was built through iterative human-AI collaboration, not one-shot code generation. The design decisions — Python over Bash, hardcoded rules over config files, exit code strategy, graceful-degradation error handling — were argued through, not accepted by default. The full process, including a real production bug the AI's initial design missed, is documented:

**[Read the full collaboration process →](docs/02-prompt-engineering.md)**

Highlights:
- **Phase 3 — Fighting Vagueness:** rejecting "test thoroughly" as an output until it became a concrete command with pass/fail criteria
- **[Phase 7 — Real-World Bug Discovery →](docs/02-prompt-engineering.md#phase-7-real-world-bug-discovery):** a manufacturer-specific false positive (Seagate `Raw_Read_Error_Rate`) found in production and fixed with a threshold-relative check instead of a hardcoded cutoff

What this demonstrates: practical problem-solving driven by a real operational incident, critical evaluation of AI output rather than blind acceptance, and domain knowledge (SMART attributes, disk failure modes) that the AI didn't independently have.

---

## SMART Attribute Rules (summary)

| ID | Attribute | Critical Threshold | Action |
|----|-----------|--------------------|--------|
| 5 | Reallocated_Sector_Ct | RAW > 10 | Replace NOW |
| 193 | Load_Cycle_Count | VALUE ≤ 5 | Replace 1-4 weeks |
| 197 | Current_Pending_Sector | RAW > 0 | Backup + replace 24h |
| 188 | Command_Timeout | VALUE ≤ 1 | Check cable/PSU first |

NVMe (no numbered table — named fields instead): Critical Warning bitmap, Available Spare vs. threshold, Percentage Used ≥90%/100%, Media and Data Integrity Errors.

Full reference with failure mechanics and manufacturer quirks: [`docs/04-smart-attributes-explained.md`](docs/04-smart-attributes-explained.md).

---

## Requirements

**Core (`bin/disk-health-checker.py`, `bin/monitor-temp.sh`):**
- Linux with `smartmontools` installed (`apt install smartmontools`)
- Python 3.8+ (3.12+ developed against)
- Root/sudo (SMART data requires privileges)
- `rich` — optional, plain-text fallback if absent

**`analysis/analyze-temp.py` only:**
- `pandas`, `rich` (see `analysis/requirements.txt`)

---

## Roadmap

**Shipped (v1.1.0):**
- ✅ NVMe support (was previously silently unparsed — see [`docs/03-design-decisions.md`](docs/03-design-decisions.md))
- ✅ `--json` / `--json-out` structured output
- ✅ `rich` made optional with plain-text fallback

**Backlog (deliberately deferred, not forgotten):**
- [ ] RAID/multipath device detection (`smartctl -d megaraid,N` and similar) — no RAID in play on current hardware, adding this as a feature when it's actually needed rather than speculatively
- [ ] Historical storage (`~/.disk-health/*.json`) + diff mode
- [ ] Prometheus exporter path (`smartctl_exporter` → existing Prometheus/Grafana stack) instead of a bespoke dashboard

---

## Testing

Validated across SATA HDD, SATA SSD, and NVMe devices, including a known-failing disk (`Load_Cycle_Count` exhaustion, the incident that started this project) and edge cases: missing SMART support, `smartctl` timeouts, permission errors, and the Seagate `Raw_Read_Error_Rate` false-positive case documented in Phase 7.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgments

- [Scrutiny](https://github.com/AnalogJ/scrutiny) — inspiration for attribute interpretation
- [smartmontools](https://www.smartmontools.org/) — the underlying SMART tooling
- [Rich](https://github.com/Textualize/rich) — terminal formatting, when available

---

**Built for homelab infrastructure where a web dashboard isn't the answer.**