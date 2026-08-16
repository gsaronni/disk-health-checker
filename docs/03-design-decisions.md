# Design Decisions

> Architecture choices and their rationale

---

## Language Selection: Python vs Bash

### The Decision
**Chose Python** for implementation despite Bash being the "native" choice for system administration scripts.

### Trade-off Analysis

**Python Advantages:**
```
✅ Rich library ecosystem (terminal formatting)
✅ Better string parsing (regex, structured data)
✅ Data structures (dictionaries for rules)
✅ Exception handling (timeout, errors)
✅ Maintainability (easier to understand 6 months later)
✅ Type hints possible (dataclasses)
```

**Python Disadvantages:**
```
❌ External dependency (rich library)
❌ Requires pip install
❌ Slightly slower startup (~100ms)
❌ Not always installed on minimal systems
```

**Bash Advantages:**
```
✅ Always available on Linux
✅ No dependencies
✅ Native process management
✅ Instant startup
```

**Bash Disadvantages:**
```
❌ Painful string parsing
❌ No structured data (arrays are primitive)
❌ Error handling is arcane
❌ Hard to read/maintain complex logic
❌ No good terminal formatting libraries
```

### Why Python Won

**Primary Reason:** Maintainability > Portability

This is a homelab tool, not a distribution package. All my systems have Python 3.12+. The `rich` library dependency is trivial compared to the code quality improvement.

**Real Example:**

**Bash parsing (painful):**
```bash
smartctl -A /dev/sda | awk '/Load_Cycle_Count/ {print $4}'
# What if format changes?
# What if attribute name has spaces?
# How to store for later comparison?
```

**Python parsing (clean):**
```python
attr = attributes[193]  # Load_Cycle_Count
if attr.value < 5:
    status = "CRITICAL"
```

### Alternative Considered: Go

**Pros:** Single binary, fast, good parsing  
**Cons:** Overkill for 400-line script, slower development

**Verdict:** Python is the sweet spot for this use case.

---

## Configuration Strategy: Hardcoded vs Config File

### The Decision
**Hardcoded attribute rules** with no external configuration file.

### Rationale

**Who uses this tool?** Me (and potentially other homelabbers)

**Do users need custom thresholds?** No. SMART attribute thresholds are based on:
- Manufacturer specifications
- Industry standards (Backblaze studies)
- Physical failure mechanics

**Example:** Reallocated Sectors = 10 is universally bad. There's no scenario where "actually I want 20 reallocated sectors to be OK."

### Benefits of Hardcoded Rules

```
✅ Single source of truth (the code)
✅ No config file parsing needed
✅ No user error (invalid thresholds)
✅ Easier to version control
✅ Self-documenting (rules are in code with comments)
```

### When Config Files Make Sense

If this becomes a multi-tenant tool used by enterprises, then:
- Different risk tolerances (conservative vs aggressive)
- Warranty considerations (replace at 80% vs 95%)
- Compliance requirements (HIPAA, financial services)

**Current scope:** Personal homelab → Hardcoded is correct choice

### Future: Optional Override (Phase B)

If needed later:
```python
# Default rules (hardcoded)
ATTRIBUTE_RULES = {...}

# Optional override
if Path("~/.disk-health/config.yaml").exists():
    custom_rules = load_config()
    ATTRIBUTE_RULES.update(custom_rules)
```

---

## Exit Code Strategy

### The Decision
```python
0 = All disks healthy
1 = Warnings detected (action in 1-4 weeks)
2 = Critical issues (replace within 24-48h)
```

### Why This Matters

**Automation Integration:**
```bash
# Cron job monitoring
if ! ./disk-health-checker.py; then
    send-alert "Disk warning on $(hostname)"
fi

# Emergency shutdown
if ./disk-health-checker.py; then
    rsync-backup-and-shutdown
else
    echo "Disk issues detected - manual intervention required"
    exit 1
fi
```

### Alternative Considered: More Granular Codes

```python
0 = All healthy
1 = Monitor (info only)
2 = Warning (1-4 weeks)
3 = Critical (24-48h)
4 = Failed (immediate)
```

**Why rejected:** Too complex. Two levels (warning/critical) are sufficient.

### Standard Compliance

Following Unix conventions:
- Exit 0 = success
- Exit 1 = generic error
- Exit 2 = misuse/severe error

Our mapping:
- 0 = success (all healthy)
- 1 = warning (soft error)
- 2 = critical (hard error)

---

## Disk Discovery Strategy

### The Decision
**Auto-discover** all physical disks, filter out logical volumes.

### Implementation
```python
# SATA/SAS disks
/dev/sd[a-z]

# NVMe disks
/dev/nvme[0-9]n[0-9]
```

**Explicitly exclude:**
- Partitions (`/dev/sda1`)
- Loop devices (`/dev/loop0`)
- Device mapper (`/dev/mapper/`, `/dev/dm-*`)
- RAM disks (`/dev/ram*`)
- Optical drives (`/dev/sr*`)

### Why Not Support Partitions?

**SMART data exists only at physical disk level.**

Checking `/dev/sda1` would just query `/dev/sda` anyway. Including partitions would:
- Clutter output (6 partitions = 6 duplicate entries)
- Confuse users (why same data 6 times?)
- Slow down execution (unnecessary smartctl calls)

### Edge Case: Multipath Devices

Enterprise servers use multipath: `/dev/sda` and `/dev/sdb` point to same physical disk.

**Current handling:** Not supported (homelab doesn't have multipath)

**Future enhancement:** Detect via `lsblk` or `multipath -ll`

---

## Timeout Handling

### The Decision
**10-second timeout** per disk with graceful skip.

### Why Timeouts Matter

**Real scenario:** Frozen disk controller

```bash
$ smartctl -a /dev/sdc
# Hangs forever, no output
# SSH session frozen
# Ctrl+C doesn't work
# Must kill SSH session
```

**With timeout:**
```python
try:
    result = subprocess.run(
        ["smartctl", "-a", device],
        timeout=10
    )
except subprocess.TimeoutExpired:
    console.print(f"⏱  Timeout reading {device}")
    return None  # Skip this disk, continue
```

### Why 10 Seconds?

**Normal smartctl execution:**
- Fast disk: 0.5-1s
- Slow disk: 2-3s
- Very slow disk: 5s

**10 seconds = 2x slowest normal case** (safety margin)

### Alternative: No Timeout

**Risk:** One bad disk hangs entire script  
**Impact:** Cannot check other disks  
**Acceptable?** No

---

## Output Formatting: Rich Library

### The Decision
Use Python `rich` library for colored terminal output.

### Alternatives Considered

**Option 1: Raw ANSI Codes**
```python
RED = "\033[91m"
GREEN = "\033[92m"
print(f"{RED}Critical{RESET}")
```

**Problems:**
- Breaks on non-color terminals
- No automatic width detection
- Hard to read/maintain

**Option 2: No Colors**
```
CRITICAL: /dev/sda - Load_Cycle_Count
```

**Problems:**
- Hard to scan visually
- No hierarchy (everything looks same)

**Option 3: Rich Library**
```python
console.print("[red]🚨 Critical[/red]")
```

**Advantages:**
- Auto-detects terminal capabilities
- Responsive width handling
- Beautiful panels/tables
- Tree structures
- Progress bars (future use)

### Trade-off

**Dependency cost:** `pip3 install rich` (5MB)  
**Value gained:** Professional output, better UX, faster development

**Verdict:** Worth it.

---

## Error Handling Philosophy

### The Decision
**Graceful degradation** - never crash, always provide partial results.

### Scenarios Handled

**1. Permission Denied**
```python
if os.geteuid() != 0:
    console.print("[red]ERROR: Must run as root[/red]")
    sys.exit(1)
```

**2. smartctl Not Installed**
```python
except FileNotFoundError:
    console.print("[red]ERROR: smartctl not found[/red]")
    sys.exit(1)
```

**3. Disk Disappeared Mid-Scan**
```python
except Exception as e:
    console.print(f"[yellow]⚠  Error reading {device}: {e}[/yellow]")
    return None  # Skip, continue with other disks
```

**4. SMART Not Supported**
```python
if not smart_enabled:
    console.print(f"[yellow]⚠  {device}: SMART not supported[/yellow]")
    return None
```

### Philosophy: Fail Fast vs Fail Gracefully

**Fail Fast:** Critical errors only
- No root permissions → exit (can't read any disks)
- smartctl missing → exit (tool can't function)

**Fail Gracefully:** Recoverable errors
- One disk timeout → skip, check others
- One disk no SMART → skip, check others
- Parsing error → skip attribute, show what we can

### Why This Matters

**Scenario:** 6 disks, one has frozen controller

**Fail fast approach:**
```
Timeout on /dev/sdc
ERROR: Cannot complete check
[Script exits]
```
Result: No information about other 5 disks

**Fail gracefully approach:**
```
⏱  Timeout reading /dev/sdc (skipping)
✅ /dev/sda - Healthy
✅ /dev/sdb - Healthy
⚠️  /dev/sdd - Warning
...
```
Result: Useful information about 5 disks, awareness of problem disk

---

## Attribute Rules Engine

### The Decision
**Dataclass-based rules** with context-aware logic.

### Architecture

```python
@dataclass
class AttributeRule:
    name: str
    check_normalized: bool    # Check VALUE field
    check_raw: bool           # Check RAW_VALUE field
    normalized_threshold: int
    raw_threshold: int
    explanation_critical: str
    action_critical: str
    hdd_only: bool           # Skip for SSDs
    ssd_only: bool           # Skip for HDDs
```

### Why This Design?

**Flexibility:** Different attributes need different checks
- Reallocated Sectors: RAW value matters (any > 0 is bad)
- Load_Cycle_Count: Normalized VALUE matters
- Temperature: Informational only (no threshold)

**Maintainability:** Adding new rules is trivial
```python
ATTRIBUTE_RULES[999] = AttributeRule(
    name="New_Attribute",
    check_raw=True,
    raw_threshold=50,
    explanation="What this means",
    action="What to do"
)
```

**Type Safety:** Dataclass provides structure
```python
# This would fail at parse time:
AttributeRule(
    name="Test",
    check_raw="yes"  # ❌ TypeError: expected bool
)
```

---

## Severity Classification

### The Decision
**Three levels:** HEALTHY, WARNING, CRITICAL

### Mapping Strategy

**CRITICAL = Immediate Action Required (24-48h)**
- Reallocated Sectors > 10
- Pending Sectors > 0
- Load_Cycle_Count VALUE < 5
- Spin Retry Count > 0

**WARNING = Action Needed (1-4 weeks)**
- Reallocated Sectors 1-10
- Load_Cycle_Count VALUE 5-20
- Seek Error Rate declining
- Command Timeout increasing

**HEALTHY = No Action**
- All attributes within normal range
- No errors logged
- SMART self-test passed

### Why Not More Levels?

**Considered:**
- INFO (FYI only)
- MONITOR (watch closely)
- WARNING (action soon)
- CRITICAL (action now)
- FAILED (too late)

**Problem:** Too granular. Users want binary decision:
1. Do I need to do something? (Yes/No)
2. How urgent? (Days or weeks)

**Three levels map cleanly:**
- HEALTHY → Do nothing
- WARNING → Order replacement, plan migration
- CRITICAL → Drop everything, backup now

---

## Reporting Strategy: Detailed vs Summary

### The Decision
**Default: Detailed reports** with `-q` for summary

### Rationale

When running manually (primary use case), user wants:
- Which disks have issues
- What the issues are
- Why they matter
- What to do

When running in cron/automation, user wants:
- Quick status (healthy/warning/critical)
- Which disks need attention
- Exit code for scripting

### Output Modes

**Default:**
```
❌ /dev/sda - ST500LT012-1DG142 (500 GB)
════════════════════════════════════════
Type: HDD | Power-On: 31,029h (3.5 years) | Temp: 25°C
SMART Health: PASSED | Our Analysis: CRITICAL

🚨 Load_Cycle_Count (VALUE=1)
   ├─ Head parking mechanism exhausted
   └─ Action: Replace within 1-4 weeks

Summary: 2 healthy, 1 warning, 1 critical
```

**Quiet (`-q`):**
```
Summary: 2 healthy, 1 warning, 1 critical
Action Required:
  🚨 /dev/sda: REPLACE WITHIN 24-48H
```

**Verbose (`-v`):**
```
[All of default output]
+
[Table of all monitored attributes]
```

---

## Phase B Status (v1.1.0 update)

### JSON Export Format — ✅ Shipped

Implemented as `--json` (stdout) and `--json-out FILE`, bypassing rendering entirely rather than adding a `--format` flag to the normal report path. Output shape matches the original plan closely:
```json
{
  "timestamp": "2026-08-14T13:48:16",
  "hostname": "zblade",
  "disks": [
    {
      "device": "/dev/sda",
      "model": "...",
      "overall_status": "CRITICAL",
      "issues": [...]
    }
  ]
}
```

**Scope decision:** this is a single snapshot, not a history mechanism. No automatic file management, no retention policy — that's the deferred piece below. The intent is occasional spot-checks you can `jq` or diff by hand, not a background monitoring pipeline. Building the pipeline (Prometheus + Grafana, reusing infra already running on zblade) is a separate, later decision, not bundled into this tool.

### Historical Storage — deferred, not abandoned

`~/.disk-health/*.json` with retention is still a reasonable Phase C idea, but explicitly not built now. `--json-out` gives you the building block (a timestamped file) without committing to a storage/retention scheme before there's a real need for one.

### Diff Mode — deferred

Same reasoning — trivial to add once there's an actual archive of JSON snapshots to diff against, premature before that exists.

### NVMe Support — ✅ Shipped

Originally NVMe disks fell through the SATA-table parser silently (empty `attributes` dict, always reported healthy — a real gap on any NVMe-primary host). `lib/smart_parser.py` now dispatches by device path to a dedicated NVMe parser reading the named `SMART/Health Information` fields (Critical Warning, Available Spare, Percentage Used, Media/Data Integrity Errors) instead of the numbered attribute table, with its own rule set in `analyze_nvme_disk()`.

### `rich` Dependency — softened

The original "worth it" verdict on `rich` (see above) still holds for the primary use case — but it's now an optional import with a plain-text fallback that reproduces the same structure (headers, per-issue blocks, summary table) without color. This matters specifically for running the checker on infrastructure you don't control the Python environment on, where you can't guarantee `pip install rich` succeeds.

---

## Conclusion

Every design decision was made with these priorities:
1. **Correctness** - Accurate SMART interpretation
2. **Usability** - Clear, actionable output
3. **Reliability** - Graceful error handling
4. **Maintainability** - Clean, documented code

**Next:** [SMART Attributes Explained →](04-smart-attributes-explained.md)