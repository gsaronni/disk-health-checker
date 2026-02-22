# Disk Health Checker

> A production-ready SMART disk analyzer for homelab and enterprise environments.  
> Built through AI-assisted development to demonstrate modern engineering workflows.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rich](https://img.shields.io/badge/rich-13.0+-purple.svg)](https://github.com/Textualize/rich)

---

## 🎯 The Problem

I run a multi-location homelab infrastructure. While [Scrutiny](https://github.com/AnalogJ/scrutiny) provides excellent web-based monitoring, I needed a CLI tool for:

- **Offline backup servers** that boot only 12 days/year
- **SSH-only access** without web UI overhead  
- **Immediate health assessment** during maintenance windows
- **Actionable diagnostics** - not just raw SMART data

**Existing solutions fell short:**
- `smartctl` output requires deep SMART knowledge to interpret
- Web-based tools demand always-on infrastructure
- Most GitHub scripts lack proper health interpretation and concrete recommendations or I just haven't found them.

---

## 🛠️ Solution

A Python-based CLI tool that:

✅ Auto-discovers all physical disks (SATA/SAS/NVMe)  
✅ Parses SMART attributes with context-aware rules  
✅ Provides **concrete actions** ("Replace within 24-48h" vs vague "test thoroughly")  
✅ Color-coded terminal output for quick assessment  
✅ Proper error handling (timeouts, permissions, unsupported devices)  
✅ Exit codes for automation (0=healthy, 1=warnings, 2=critical)  

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/gsaronni/disk-health-checker.git
cd disk-health-checker

# Install dependency
pip3 install rich

# Make executable
chmod +x disk-health-checker.py
```

### Usage

```bash
# Check all disks
sudo ./disk-health-checker.py

# Verbose mode (show all SMART attributes)
sudo ./disk-health-checker.py -v

# Summary only
sudo ./disk-health-checker.py -q

# Critical issues only
sudo ./disk-health-checker.py --critical
```

---

## 📊 Sample Output

```
╔══════════════════════════════════════════════════════╗
║              DISK HEALTH REPORT                      ║
║          2026-02-10 14:30:00 UTC                     ║
╚══════════════════════════════════════════════════════╝

🔍 Found 4 disk(s): /dev/sda, /dev/sdb, /dev/sdc, /dev/sdd

❌ /dev/sda - ST500LT012-1DG142 (500 GB)
════════════════════════════════════════════════════════
Type: HDD | Power-On: 31,029h (3.5 years) | Temp: 25°C
SMART Health: PASSED | Our Analysis: CRITICAL

🚨 Load_Cycle_Count (VALUE=1)
   ├─ Head parking mechanism exhausted - mechanical failure imminent
   └─ Action: Replace within 1-4 weeks

⚠️  Seek_Error_Rate (VALUE=84)
   ├─ Seek errors increasing (mechanical degradation)
   └─ Action: Monitor weekly, plan replacement in 1-3 months

───────────────────────────────────────────────────────
                      SUMMARY
───────────────────────────────────────────────────────
✅ Healthy      2 disk(s)
⚠️  Warning     1 disk(s)
❌ Critical     1 disk(s)

Action Required:
  🚨 /dev/sda: REPLACE WITHIN 24-48H
  ⚠️  /dev/sdc: Monitor/test, replace in 1-4 weeks
```

---

## 💡 AI-Assisted Development Showcase

This project demonstrates a modern engineering workflow using AI as a collaborative tool.

### Development Process

**Phase 1: Requirements Gathering**
- Identified gaps in existing monitoring solutions
- Defined concrete success criteria
- Established non-negotiable constraints (no vague recommendations)

**Phase 2: Collaborative Design**
- Brainstormed architecture options (Python vs Bash, SQLite vs JSON)
- Evaluated trade-offs with AI assistance
- Made informed decisions based on maintainability and operational needs

**Phase 3: Iterative Refinement**
- Rejected vague suggestions ("test thoroughly" → concrete commands with pass/fail criteria)
- Researched SMART attribute meanings and manufacturer-specific quirks
- Validated interpretation logic against real disk failures

**Phase 4: Production Validation**
- Tested across 15 disks (HDD, SSD, NVMe)
- Validated against Scrutiny web dashboard
- Confirmed detection of known failing disk (Load_Cycle_Count exhaustion)

**Phase 5: Production Validation**
- Deployed on live 8-disk infrastructure
- Discovered manufacturer-specific quirk (Seagate Exos)
- Fixed false positive through threshold-relative checking
- Validated with extended SMART tests

**[Read the bug discovery story →](docs/02-ai-collaboration-process.md#phase-5-real-world-bug-discovery)**

### What This Demonstrates

✅ **Practical Problem-Solving** - Built to solve real operational challenges  
✅ **Modern Workflow** - Effective AI collaboration without blind acceptance  
✅ **Critical Thinking** - Challenged vague outputs, demanded specificity  
✅ **Domain Knowledge** - Deep understanding of SMART attributes and disk failure modes  
✅ **Production-Ready** - Proper error handling, logging, exit codes  

**[Read the full collaboration process →](docs/02-ai-collaboration-process.md)**

---

## 🔍 Technical Deep Dive

### Architecture Decisions

**Language Choice: Python over Bash**
- Better parsing capabilities for complex SMART output
- Rich library for terminal formatting
- Easier to maintain and extend
- Trade-off: External dependency vs shell portability

**Hardcoded Rules vs Configuration Files**
- Opinionated approach for consistency
- Reduces user error in threshold configuration
- Easier maintenance (single source of truth)
- Future: Optional config override in Phase B

**Exit Code Strategy**
```python
0 = All disks healthy
1 = Warnings detected (action in 1-4 weeks)
2 = Critical issues (replace within 24-48h)
```
Enables automation: `./disk-health-checker.py && echo "All good" || send-alert`

### SMART Attribute Rules

The tool monitors 10 critical attributes with context-aware thresholds:

| ID | Attribute | Critical Threshold | Action |
|----|-----------|-------------------|--------|
| 5 | Reallocated Sectors | RAW > 10 | Replace NOW |
| 193 | Load Cycle Count | VALUE < 5 | Replace 1-4 weeks |
| 197 | Pending Sectors | RAW > 0 | Backup + replace 24h |
| 188 | Command Timeout | VALUE < 1 | Check cable/PSU |

**[Full attribute reference →](docs/04-smart-attributes-explained.md)**

---

## 🎓 Learning Resources

### Understanding SMART Attributes

- **Load Cycle Count**: Head parking mechanism wear (laptop drives)
- **Reallocated Sectors**: Bad sectors remapped by firmware
- **Seek Error Rate**: Mechanical positioning accuracy
- **Command Timeout**: Cable/controller/firmware issues

**[Detailed explanations with examples →](docs/04-smart-attributes-explained.md)**

### Prompt Engineering Insights

Key strategies that produced quality output:

1. **Context First** - Provided full infrastructure documentation
2. **Iterative Refinement** - "Explain like I'm 5" for complex topics
3. **Concrete Requirements** - Rejected vague suggestions
4. **Collaborative Design** - Brainstormed before coding

**[Read the full process →](docs/02-ai-collaboration-process.md)**

---

## 🧪 Testing

Tested on:
- 15 disks across 4 systems
- Mix of HDD (laptop/desktop), SSD, NVMe
- Encrypted LUKS volumes
- Known failing disk (validated detection)
- Edge cases: missing SMART, timeouts, permission errors

---

## 🔮 Roadmap

### Phase A (Current - v1.0.0-alpha)
✅ Core functionality  
✅ 10 critical SMART attributes  
✅ Colored terminal output  
✅ Proper error handling  
✅ Exit codes for automation  

### Phase B (Planned - v2.0.0)
- [ ] JSON export (`--format json`)
- [ ] Historical tracking (`~/.disk-health/*.json`)
- [ ] Diff mode (`--diff previous.json`)
- [ ] Manufacturer quirks database (Seagate Command_Timeout handling)
- [ ] Optional config file for threshold overrides

### Future Enhancements
- [ ] Integration with monitoring systems (Prometheus exporter)
- [ ] Email/webhook alerts
- [ ] Web dashboard (lightweight alternative to Scrutiny)

---

## 🤝 Contributing

This project serves as a personal learning showcase, but suggestions are welcome!

If you find a bug or have a feature request:
1. Check existing issues
2. Open a new issue with:
   - SMART output (`smartctl -a /dev/sdX`)
   - Expected vs actual behavior
   - Disk model and type

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **Scrutiny** - Inspiration for attribute interpretation
- **smartmontools** - The underlying SMART tooling
- **Rich** - Beautiful terminal formatting
- **Claude AI** - Collaborative development partner

---

## 📚 Related Projects

- [Scrutiny](https://github.com/AnalogJ/scrutiny) - Web-based SMART monitoring
- [smartmontools](https://www.smartmontools.org/) - SMART monitoring utilities
- My homelab automation: [gsaronni/network-automation-toolkit](https://github.com/gsaronni/network-automation-toolkit)

---

**Built with 🧠 AI collaboration | Deployed in production homelab infrastructure**
