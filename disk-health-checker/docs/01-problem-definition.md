# Problem Definition


## The Challenge

### Existing Monitoring Setup

I already run **Scrutiny** on my main server for web-based disk health monitoring:
- Historical SMART data tracking
- Email alerts for failures
- Beautiful dashboard with graphs
- Excellent for always-on systems

### Why Scrutiny Wasn't Enough

**1. Offline Backup Server **
- Boots only ~12 days/year for monthly backups
- Scrutiny requires web stack + database
- Overkill for occasional health checks
- Need immediate assessment on boot

**2. SSH-Only Maintenance**
- Remote access via Netbird mesh VPN
- No convenient way to check Scrutiny remotely
- Terminal-based workflow preferred
- Web UI adds unnecessary steps

**3. Interpretation Gap**
- Scrutiny shows raw SMART data
- Still requires knowledge to interpret
- No concrete action recommendations
- "Test thoroughly" - what does that even mean?

**4. Emergency Diagnostics**
- When disk warning appears in logs
- Need quick health check before shutdown
- Web UI too slow during maintenance windows

---

## Existing Solutions Evaluated

### Option 1: smartctl (Raw Output)

```bash
$ smartctl -a /dev/sda
```

**Problems:**
- Cryptic output (194 attributes to parse)
- Requires deep SMART knowledge
- No interpretation of values
- No actionable recommendations

**Example Issue:**
```
193 Load_Cycle_Count  0x0032   001   001   000    Old_age   Always       -       265440
```
What does VALUE=1 mean? Is this critical? Should I replace the disk?

---

### Option 2: Scrutiny CLI Mode

Scrutiny doesn't have a proper CLI mode. API exists but requires:
- Running web stack
- JSON parsing
- Still lacks interpretation layer

---

### Option 3: Existing GitHub Scripts

Searched for "smart health checker cli" - found various scripts:

**Problems:**
- Most are abandoned (5+ years old)
- Minimal error handling
- Fixed disk paths (assumes /dev/sda, /dev/sdb only)
- No context-aware rules (treats all warnings equally)
- Vague outputs: "Warning: disk health degraded"

**None provided concrete actions:**
- "Monitor closely" - how? When?
- "Test disk" - which test? What's passing criteria?
- "Replace soon" - how soon? Days? Months?

---

## What I Actually Needed

### Functional Requirements

**Disk Discovery**
- Auto-detect all physical disks (SATA, SAS, NVMe)
- Filter out partitions, loopback, dm-crypt volumes
- Handle missing/unplugged disks gracefully

**Health Analysis**
- Parse top 10 critical SMART attributes
- Context-aware rules (HDD vs SSD vs NVMe)
- Severity scoring (healthy, warning, critical)

**Actionable Output**
- Concrete recommendations with timelines
- "Replace within 24-48h" not "test thoroughly"
- Specific commands when tests needed
- Pass/fail criteria for validation tests

**Operational Integration**
- Exit codes for automation (0/1/2)
- Quick glance mode (summary only)
- Verbose mode for deep-dive
- Handles errors without crashing

### Non-Functional Requirements

**Performance**
- Run in < 30 seconds for 6 disks
- Timeout protection (10s per disk)
- No hanging on frozen controllers

**Usability**
- Colored output for quick scanning
- Works over SSH (no GUI needed)
- Clear error messages
- Helpful --help documentation

**Maintainability**
- Single Python file (easy to deploy)
- Minimal dependencies (just `rich`)
- Well-commented code
- Extensible attribute rules

---

## The Real Incident That Triggered This

**January 8, 2026 - Backup Boot**

Booted Backup server for monthly backup. Scrutiny had logged a warning about `/dev/sda` weeks ago, but I hadn't checked the web UI.

During boot, I wanted to quickly verify disk health before trusting it with backup data.

**Problem:** 
- Scrutiny web UI not accessible (Backup on different network)
- Running `smartctl -a /dev/sda` gave me this:

```
193 Load_Cycle_Count  0x0032   001   001   000    Old_age   Always       -       265440
```

**Questions I had:**
1. Is VALUE=1 bad? (spoiler: yes, very bad)
2. What's a Load Cycle Count anyway?
3. Should I backup to this disk or not?
4. Do I have days, weeks, or hours left?

**I spent 30 minutes researching:**
- Googling "Load_Cycle_Count VALUE 1"
- Reading Seagate datasheets
- Cross-referencing with Scrutiny web UI
- Still uncertain about urgency

**This delay was unacceptable.** I needed a tool that would tell me immediately:

```
🚨 Load_Cycle_Count (VALUE=1)
   ├─ Head parking mechanism exhausted - mechanical failure imminent
   └─ Action: Replace within 1-4 weeks
```

That's when I decided to build this tool.

---

## Success Criteria

A successful tool must:

1. ✅ Run on any Linux system with smartctl installed
2. ✅ Discover all disks automatically
3. ✅ Provide immediate health assessment (< 1 minute)
4. ✅ Give concrete actions with timelines
5. ✅ Work offline (no web stack required)
6. ✅ Integrate with automation (proper exit codes)
7. ✅ Handle edge cases gracefully (missing disks, timeouts, no SMART)

**Specific example:** 
For the Backup Server `/dev/sda` case, the tool should output:
- Identify Load_Cycle_Count VALUE=1 as CRITICAL
- Explain what this means in plain English
- Recommend specific timeline (1-4 weeks)
- Suggest validation tests if uncertain

**Not acceptable:**
- "Disk health degraded"
- "Monitor closely"
- "Run tests"
- Raw SMART attribute dumps

---

## Out of Scope (Phase A)

**Explicitly NOT building:**
- Historical tracking (Scrutiny does this well)
- Web dashboard (Scrutiny exists)
- Email alerts (Scrutiny handles this)
- Predictive failure analysis (too complex)
- RAID health monitoring (different problem)

**Focus:** Fast, offline, actionable CLI health checks.

---

**Next:** [AI Collaboration Process →](02-ai-collaboration-process.md)
