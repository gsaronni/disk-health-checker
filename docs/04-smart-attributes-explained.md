# SMART Attributes Explained

> Understanding disk health metrics and what they mean for your data

---

## SMART Overview

**S.M.A.R.T.** = Self-Monitoring, Analysis, and Reporting Technology

Built into disk firmware since the 1990s. Tracks ~200+ internal metrics about disk health. Most attributes follow this format:

```
ID# ATTRIBUTE_NAME     FLAG  VALUE WORST THRESH TYPE     UPDATED  WHEN_FAILED RAW_VALUE
  5 Reallocated_Sector 0x33   100   100    36   Pre-fail Always       -       0
```

### Understanding the Fields

**VALUE** (Normalized)
- Current health on 0-100 scale (usually 100 = perfect)
- Decreases as attribute degrades
- **When VALUE drops below THRESH → disk fails SMART test**

**WORST**
- Lowest VALUE ever recorded
- Helps identify if disk had past failures

**THRESH** (Threshold)
- Manufacturer-defined failure point
- Example: THRESH=36 means disk fails if VALUE < 36

**RAW_VALUE**
- Actual counter/measurement from firmware
- Interpretation varies by manufacturer
- More useful than normalized VALUE for some attributes

**TYPE**
- `Pre-fail`: Predicts imminent failure
- `Old_age`: Normal wear and tear

---

## Critical Attributes (Top 10)

### 🔴 ID 5: Reallocated Sector Count

**What it tracks:** Number of bad sectors remapped to spare area

**How it works:**
1. Disk detects unreadable sector
2. Marks it as bad
3. Remaps reads/writes to spare sector pool
4. Increments this counter

**Why it matters:**
- Disks ship with spare sectors (~1-3% capacity)
- Once remapping starts, more usually follow
- Sign of physical media degradation

**Thresholds:**
```
RAW = 0        → ✅ Healthy (no bad sectors)
RAW = 1-10     → ⚠️  Warning (monitor closely)
RAW > 10       → 🚨 Critical (replace immediately)
```

**Real-world example:**
```
5 Reallocated_Sector_Ct  0x0033  100  100  36  Pre-fail  Always  -  15
                                                                      ^^
```
**15 bad sectors** → This disk is dying. Backup NOW.

---

### 🔴 ID 197: Current Pending Sector

**What it tracks:** Sectors waiting to be remapped (unstable reads)

**How it works:**
1. Disk has trouble reading sector
2. Marks it as "pending" (not yet bad)
3. If next write succeeds → clears pending
4. If next write fails → moves to reallocated list (ID 5)

**Why it matters:**
- Pending = actively failing RIGHT NOW
- Data on pending sectors is at risk
- More urgent than reallocated sectors

**Thresholds:**
```
RAW = 0        → ✅ Healthy
RAW > 0        → 🚨 Critical (backup immediately)
```

**Difference from ID 5:**
- ID 5 = Past failures (already remapped)
- ID 197 = Active failures (happening now)

---

### 🔴 ID 193: Load Cycle Count (HDD only)

**What it tracks:** Number of times read/write heads parked

**How it works:**
1. Disk idle for N seconds (often just 8 seconds!)
2. Heads retract to parking zone
3. Spindle keeps spinning
4. Next I/O → heads reposition → increment counter

**Why it matters:**
- Head actuator mechanism has finite lifetime
- Laptop drives rated for ~300,000-600,000 cycles
- Aggressive power management causes rapid wear

**Thresholds:**
```
VALUE > 20     → ✅ Healthy
VALUE 5-20     → ⚠️  Warning (approaching limit)
VALUE < 5      → 🚨 Critical (mechanism exhausted)
```

**Real-world example:**
```
193 Load_Cycle_Count  0x0032  001  001  000  Old_age  Always  -  265440
                              ^^^
```
**VALUE=1** → Only 1 point above threshold. Mechanical failure imminent.

**Why VALUE=1 is critical:**
- Manufacturer started at VALUE=100
- Each cycle decreases VALUE by ~0.0003
- VALUE=1 means 99% of rated cycles consumed
- Actuator arm is physically worn out

**How to prevent (new disks):**
```bash
# Disable aggressive power management
hdparm -B 255 /dev/sda  # Maximum performance (no parking)
hdparm -S 0 /dev/sda    # Disable spindown
```

---

### 🔴 ID 1: Raw Read Error Rate

**What it tracks:** Frequency of read errors (corrected by firmware)

**How it works:**
1. Disk reads data
2. ECC detects error
3. Retries read (usually succeeds)
4. Increments counter

**Why it matters:**
- Normal disks have some errors (cosmic rays, thermal expansion)
- Excessive errors indicate media degradation
- Early warning before uncorrectable errors appear

**Thresholds:**
```
VALUE > 80     → ✅ Healthy (normal error rate)
VALUE 50-80    → ⚠️  Warning (increasing errors)
VALUE < 50     → 🚨 Critical (excessive errors)
```

**Manufacturer variation:**
- Seagate: RAW_VALUE uses vendor-specific formula (ignore)
- Western Digital: RAW_VALUE is actual error count
- **Always use normalized VALUE, not RAW**

---

### 🔴 ID 7: Seek Error Rate (HDD only)

**What it tracks:** Frequency of head positioning errors

**How it works:**
1. Controller tells heads: "move to track 12345"
2. Heads move, check position
3. If wrong track → retry → increment counter

**Why it matters:**
- Mechanical wear of actuator mechanism
- Precursor to Load_Cycle_Count exhaustion
- Sign of head crash risk

**Thresholds:**
```
VALUE > 70     → ✅ Healthy
VALUE 30-70    → ⚠️  Warning (mechanical wear)
VALUE < 30     → 🚨 Critical (immediate failure risk)
```

---

### 🔴 ID 10: Spin Retry Count (HDD only)

**What it tracks:** Number of times spindle motor failed to start

**How it works:**
1. Power on
2. Motor attempts to spin platters
3. If fails → retry
4. Increment counter

**Why it matters:**
- Spindle motor failure = complete disk failure
- No motor = no data access
- ANY value > 0 is critical

**Thresholds:**
```
RAW = 0        → ✅ Healthy
RAW > 0        → 🚨 Critical (motor failing, replace NOW)
```

---

### 🔴 ID 184: End-to-End Error

**What it tracks:** Parity errors between host and disk

**How it works:**
1. Data sent from host with checksum
2. Disk receives data, verifies checksum
3. If mismatch → increment counter

**Why it matters:**
- Indicates data path corruption
- Could be disk, cable, controller, or RAM
- Data integrity compromised

**Thresholds:**
```
RAW = 0        → ✅ Healthy
RAW > 0        → 🚨 Critical (data corruption risk)
```

**Troubleshooting steps:**
1. Swap SATA cable
2. Try different SATA port
3. If persists → disk is bad

---

### 🔴 ID 187: Reported Uncorrectable Errors

**What it tracks:** Sectors that cannot be read despite retries

**How it works:**
1. Read sector
2. ECC detects error
3. Retry multiple times
4. All retries fail → uncorrectable
5. Increment counter

**Why it matters:**
- Data is LOST on these sectors
- Cannot be recovered
- More will follow

**Thresholds:**
```
RAW = 0        → ✅ Healthy
RAW > 0        → 🚨 Critical (data loss occurred)
```

---

### 🔴 ID 188: Command Timeout

**What it tracks:** Commands that timed out

**How it works:**
1. Host sends command (read/write)
2. Disk doesn't respond within timeout period
3. Host retries or aborts
4. Increment counter

**Why it matters:**
- Could indicate failing controller
- Could indicate bad cable/power
- Could be firmware bug (common on Seagate)

**Thresholds:**
```
VALUE > 50     → ✅ Healthy
VALUE 10-50    → ⚠️  Warning (investigate)
VALUE < 10     → 🚨 Critical (replace or check cable/PSU)
```

**Troubleshooting:**
```bash
# Check cable first
1. Swap SATA cable with known-good disk
2. Recheck counter after 24h
3. If counter stops → cable issue
4. If counter increases → disk issue
```

**Manufacturer quirk:**
- Seagate ST*LM049 series has firmware bug
- Massive RAW values (billions) but disk works fine
- Check WORST value: if < 50 → real problem

---

### 🔴 ID 198: Offline Uncorrectable

**What it tracks:** Sectors found bad during background scan

**How it works:**
1. Disk runs periodic self-test
2. Scans all sectors
3. Finds sectors that will fail on next read
4. Increments counter

**Why it matters:**
- These sectors haven't been read yet (data not lost yet)
- Will fail when accessed
- Pending disaster

**Thresholds:**
```
RAW = 0        → ✅ Healthy
RAW > 0        → 🚨 Critical (backup before accessing these sectors)
```

---

## Informational Attributes

### ℹ️ ID 9: Power-On Hours

**What it tracks:** Total hours disk has been powered

**Usage:**
- Calculate disk age: `hours / 8760 = years`
- Context for other attributes
- Not a failure predictor itself

**Typical values:**
```
20,000h  = 2.3 years (young)
40,000h  = 4.5 years (middle-aged)
60,000h+ = 6.8 years (old, plan replacement)
```

---

### ℹ️ ID 12: Power Cycle Count

**What it tracks:** Number of full power-off/on cycles

**Why it matters:**
- Some failures happen at power-on (motor stress)
- Laptop drives see more cycles
- Server drives see fewer cycles

**Typical values:**
```
< 1,000   → Mostly always-on (server)
1,000-10,000 → Laptop/desktop use
> 10,000  → Heavily power-cycled (sign of instability?)
```

---

### ℹ️ ID 4: Start/Stop Count

**What it tracks:** Spindle motor start/stop cycles

**Difference from Power Cycle Count:**
- Power cycle = full power off/on
- Start/Stop = spindle spin up/down (may happen while powered)

---

### ℹ️ ID 194: Temperature

**What it tracks:** Current disk temperature (Celsius)

**Safe ranges:**
```
< 35°C   → ✅ Optimal
35-45°C  → ⚠️  Acceptable (airflow check)
45-55°C  → 🚨 Hot (add cooling)
> 55°C   → 🔥 Danger (immediate cooling needed)
```

**Why it matters:**
- High temps accelerate wear
- Thermal expansion causes mechanical stress
- Above 60°C → data corruption risk

---

## SSD-Specific Attributes

### ID 233: Media Wearout Indicator (Intel SSDs)

**What it tracks:** Percentage of rated write endurance remaining

**Thresholds:**
```
VALUE 100-50  → ✅ Healthy (50-100% life left)
VALUE 20-50   → ⚠️  Warning (plan replacement)
VALUE < 20    → 🚨 Critical (replace within weeks)
```

---

### ID 241: Total LBAs Written

**What it tracks:** Total data written to SSD

**Usage:** Calculate wear:
```
TBW = (LBAs written × sector size) / 1,000,000,000,000
Compare to rated endurance (e.g., 600 TBW)
```

---

## NVMe-Specific Attributes

NVMe uses different attribute names:

- **Percentage Used**: Same as SSD Media Wearout
- **Available Spare**: Remaining spare blocks (< 10% = critical)
- **Critical Warning**: Bitmap of failure conditions

---

## Manufacturer-Specific Quirks

### Seagate

**Command Timeout (ID 188):**
- Firmware bug on ST*LM049 series
- RAW values in trillions but disk works
- Check WORST value instead of RAW

**Raw Read Error Rate (ID 1):**
- Uses vendor-specific encoding
- Ignore RAW value, use normalized VALUE

---

### Western Digital

**Raw Read Error Rate (ID 1):**
- RAW value is actual error count
- Can be used directly

---

### Samsung SSDs

**Wear Leveling Count:**
- Tracks flash block usage distribution
- Lower VALUE = more uneven wear

---

## SMART Self-Tests

### Short Test (~2 minutes)
```bash
smartctl -t short /dev/sda
# Wait 2 minutes
smartctl -l selftest /dev/sda
```

**Checks:**
- Electrical systems
- Basic read/write
- Quick surface scan

---

### Long Test (2-6 hours)
```bash
smartctl -t long /dev/sda
# Wait for completion time (shown in command)
smartctl -l selftest /dev/sda
```

**Checks:**
- Full surface scan
- All SMART attributes
- Comprehensive validation

---

### When to Run Tests

**Short test:**
- Monthly maintenance
- After suspicious behavior
- Before trusting used disk

**Long test:**
- Quarterly maintenance
- Before production deployment
- After detecting warnings
- Before RMA (warranty claim)

---

## Interpreting Test Results

```bash
$ smartctl -l selftest /dev/sda

Num  Test_Description    Status                  Remaining  LifeTime(hours)
# 1  Extended offline    Completed without error       00%     31029
# 2  Short offline       Completed without error       00%     30500
# 3  Extended offline    Aborted by host              90%     29800
```

**Status meanings:**
- `Completed without error` → ✅ Good
- `Completed: read failure` → 🚨 Bad sectors found
- `Aborted by host` → Test interrupted (not a failure)
- `Fatal or unknown error` → 🚨 Disk is dying

---

## Red Flags: Multiple Warnings

**Single warning:** Might be fluke, monitor

**Multiple warnings together:**
```
⚠️  Raw Read Error Rate declining
⚠️  Seek Error Rate declining
⚠️  Load Cycle Count high
⚠️  Command Timeout increasing
```

**Interpretation:** Disk is in death spiral. Replace immediately.

---

## Best Practices

### Monitoring Frequency

**Always-on servers:** Weekly SMART checks  
**Backup servers:** Every boot  
**Workstations:** Monthly  

### Action Triggers

**Any RAW > 0 on these IDs:** 5, 10, 197, 198, 187  
**Any VALUE < 10 on these IDs:** 1, 7, 193  
**Temperature > 50°C**  

**→ Immediate backup + replacement planning**

### Backup Strategy

**SMART is not a backup plan:**
- Disks can fail without SMART warnings (controller death, bearing seizure)
- SMART predicts ~70% of failures
- 30% fail suddenly with no warning

**Always maintain:**
- 3 copies of data
- 2 different media types
- 1 offsite backup

---

## Further Reading

- [Backblaze Hard Drive Stats](https://www.backblaze.com/blog/backblaze-drive-stats-for-2023/) - Real failure data from 250k+ disks
- [smartmontools Documentation](https://www.smartmontools.org/wiki/TocDoc) - Official SMART tools guide
- [Wikipedia: S.M.A.R.T.](https://en.wikipedia.org/wiki/S.M.A.R.T.) - Comprehensive attribute reference

---

**Previous:** [Design Decisions ←](03-design-decisions.md)
