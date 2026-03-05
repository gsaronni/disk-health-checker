#!/usr/bin/env python3
"""
__version__ = "1.0.0-alpha"
__author__ = "Gabriele Saronni"
__description__ = "SMART disk health analyzer - AI-assisted development"
__github__ = "https://github.com/gsaronni/disk-health-checker"

Disk Health Checker - SMART Analysis Tool
Analyzes disk health via smartctl and provides actionable recommendations

Usage:
    sudo ./disk-health-checker.py           # Check all disks
    sudo ./disk-health-checker.py -v        # Verbose mode
    sudo ./disk-health-checker.py -q        # Quiet (summary only)
    sudo ./disk-health-checker.py --critical # Critical issues only

Exit Codes:
    0 = All disks healthy
    1 = Warnings detected (action needed in 1-4 weeks)
    2 = Critical issues (replace within 24-48h)
"""

import os
import sys
import re
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("ERROR: rich library not installed")
    print("Install with: pip3 install rich")
    sys.exit(1)

console = Console()

# ============================================================================
# SMART ATTRIBUTE RULES DATABASE
# ============================================================================

@dataclass
class AttributeRule:
    """Rule definition for SMART attribute analysis"""
    name: str
    check_normalized: bool = True  # Check VALUE field
    check_raw: bool = False         # Check RAW_VALUE field
    normalized_threshold: int = 10  # Critical if VALUE < this
    normalized_warning: int = 50    # Warning if VALUE < this
    raw_threshold: int = 0          # Critical if RAW > this
    explanation_critical: str = ""
    explanation_warning: str = ""
    action_critical: str = ""
    action_warning: str = ""
    hdd_only: bool = False
    ssd_only: bool = False

ATTRIBUTE_RULES = {
    1: AttributeRule(
        name="Raw_Read_Error_Rate",
        normalized_threshold=10,
        normalized_warning=80,
        explanation_critical="Excessive read errors - data corruption risk imminent",
        explanation_warning="Drive is correcting read errors (normal wear, but monitor)",
        action_critical="IMMEDIATE backup + replace within 24-48h",
        action_warning="Run extended SMART test monthly, verify backups",
        hdd_only=True
    ),
    5: AttributeRule(
        name="Reallocated_Sector_Ct",
        check_raw=True,
        raw_threshold=10,
        explanation_critical="10+ bad sectors remapped - drive is failing",
        explanation_warning="1-10 bad sectors found and remapped",
        action_critical="Replace disk NOW. Data loss imminent.",
        action_warning="Acceptable if stable. Run extended test monthly."
    ),
    7: AttributeRule(
        name="Seek_Error_Rate",
        normalized_threshold=30,
        normalized_warning=70,
        explanation_critical="Head positioning failures - mechanical wear severe",
        explanation_warning="Seek errors increasing (mechanical degradation)",
        action_critical="Replace within 1 week",
        action_warning="Monitor weekly, plan replacement in 1-3 months",
        hdd_only=True
    ),
    9: AttributeRule(
        name="Power_On_Hours",
        check_normalized=False,
        check_raw=False,  # Informational only
        explanation_warning="Disk age reference (not a failure indicator)",
        action_warning=""
    ),
    10: AttributeRule(
        name="Spin_Retry_Count",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Spindle motor struggling to start - imminent failure",
        action_critical="Replace IMMEDIATELY (motor failure)",
        hdd_only=True
    ),
    184: AttributeRule(
        name="End-to-End_Error",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Data path errors detected (firmware/controller issue)",
        action_critical="Replace within 48h - data integrity compromised"
    ),
    187: AttributeRule(
        name="Reported_Uncorrect",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Uncorrectable errors detected",
        action_critical="Backup immediately, replace within 24h"
    ),
    188: AttributeRule(
        name="Command_Timeout",
        normalized_threshold=1,
        normalized_warning=50,
        explanation_critical="Massive command timeouts (cable/power/controller failure)",
        explanation_warning="Some command timeouts detected",
        action_critical="Check SATA cable, PSU rails, controller. If OK → replace disk",
        action_warning="Monitor. Try different SATA cable first."
    ),
    193: AttributeRule(
        name="Load_Cycle_Count",
        normalized_threshold=5,
        normalized_warning=20,
        explanation_critical="Head parking mechanism exhausted - mechanical failure imminent",
        explanation_warning="Approaching head parking cycle limit",
        action_critical="Replace within 1-4 weeks",
        action_warning="Disable APM (hdparm -B 255) or plan replacement",
        hdd_only=True
    ),
    197: AttributeRule(
        name="Current_Pending_Sector",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Sectors waiting to be remapped - active failure",
        action_critical="Backup NOW. Replace within 24h."
    ),
    198: AttributeRule(
        name="Offline_Uncorrectable",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Uncorrectable sectors found during offline scan",
        action_critical="Replace within 48h"
    ),
    194: AttributeRule(
        name="Temperature_Celsius",
        check_normalized=False,
        check_raw=False,  # Informational
        explanation_warning="Disk temperature (monitoring only)",
        action_warning=""
    ),
}

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SmartAttribute:
    """SMART attribute data"""
    id: int
    name: str
    flag: str
    value: int
    worst: int
    thresh: int
    type: str
    updated: str
    when_failed: str
    raw_value: str

@dataclass
class DiskInfo:
    """Disk information and health status"""
    device: str
    model: str
    serial: str
    capacity: str
    disk_type: str  # HDD, SSD, NVMe
    rotation_rate: str
    smart_enabled: bool
    smart_health: str
    attributes: Dict[int, SmartAttribute]
    overall_status: str  # HEALTHY, WARNING, CRITICAL
    issues: List[Dict]
    power_on_hours: int = 0
    temperature: int = 0

# ============================================================================
# DISK DISCOVERY
# ============================================================================

def discover_disks() -> List[str]:
    """Discover all physical disks (exclude partitions, loop, dm-crypt)"""
    disks = []
    
    # Find SATA/SAS disks (sd*)
    for device in Path("/dev").glob("sd[a-z]"):
        disks.append(str(device))
    
    # Find NVMe disks
    for device in Path("/dev").glob("nvme[0-9]n[0-9]"):
        disks.append(str(device))
    
    return sorted(disks)

# ============================================================================
# SMART DATA PARSING
# ============================================================================

def run_smartctl(device: str, timeout: int = 10) -> Optional[str]:
    """Run smartctl with timeout and error handling"""
    try:
        result = subprocess.run(
            ["smartctl", "-a", device],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⏱  Timeout reading {device} (>{timeout}s)[/yellow]")
        return None
    except FileNotFoundError:
        console.print("[red]ERROR: smartctl not found. Install smartmontools[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[yellow]⚠  Error reading {device}: {e}[/yellow]")
        return None

def parse_smart_output(device: str, output: str) -> Optional[DiskInfo]:
    """Parse smartctl output into structured data"""
    
    # Extract basic info
    model = re.search(r"Device Model:\s+(.+)", output)
    serial = re.search(r"Serial Number:\s+(.+)", output)
    capacity = re.search(r"User Capacity:\s+[\d,]+ bytes \[(.+?)\]", output)
    rotation = re.search(r"Rotation Rate:\s+(.+)", output)
    smart_enabled = "SMART support is: Enabled" in output
    smart_health = re.search(r"SMART overall-health.*:\s+(\w+)", output)
    
    if not smart_enabled:
        console.print(f"[yellow]⚠  {device}: SMART not supported - skipping[/yellow]")
        return None
    
    # Determine disk type
    disk_type = "HDD"
    rotation_rate = "Unknown"
    if rotation:
        rotation_rate = rotation.group(1)
        if "Solid State Device" in rotation_rate or "SSD" in rotation_rate:
            disk_type = "SSD"
    if "nvme" in device:
        disk_type = "NVMe"
        rotation_rate = "N/A (NVMe)"
    
    # Parse SMART attributes table
    attributes = {}
    attr_section = re.search(
        r"ID# ATTRIBUTE_NAME.*?\n(.*?)(?:\n\n|SMART Error Log)",
        output,
        re.DOTALL
    )
    
    if attr_section:
        for line in attr_section.group(1).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 10 and parts[0].isdigit():
                attr_id = int(parts[0])
                attributes[attr_id] = SmartAttribute(
                    id=attr_id,
                    name=parts[1],
                    flag=parts[2],
                    value=int(parts[3]),
                    worst=int(parts[4]),
                    thresh=int(parts[5]),
                    type=parts[6],
                    updated=parts[7],
                    when_failed=parts[8],
                    raw_value=' '.join(parts[9:])
                )
    
    # Extract power-on hours and temperature
    power_on_hours = 0
    temperature = 0
    if 9 in attributes:
        try:
            power_on_hours = int(attributes[9].raw_value.split()[0])
        except (ValueError, IndexError):
            pass
    if 194 in attributes:
        try:
            temperature = int(attributes[194].raw_value.split()[0])
        except (ValueError, IndexError):
            pass
    
    return DiskInfo(
        device=device,
        model=model.group(1) if model else "Unknown",
        serial=serial.group(1) if serial else "Unknown",
        capacity=capacity.group(1) if capacity else "Unknown",
        disk_type=disk_type,
        rotation_rate=rotation_rate,
        smart_enabled=smart_enabled,
        smart_health=smart_health.group(1) if smart_health else "UNKNOWN",
        attributes=attributes,
        overall_status="HEALTHY",
        issues=[],
        power_on_hours=power_on_hours,
        temperature=temperature
    )

# ============================================================================
# HEALTH ANALYSIS
# ============================================================================

def detect_manufacturer(model: str) -> str:
    """Detect disk manufacturer from model string"""
    if model.startswith("ST"):
        return "Seagate"
    elif model.startswith("WDC") or model.startswith("WD"):
        return "Western Digital"
    elif model.startswith("TOSHIBA") or model.startswith("Toshiba"):
        return "Toshiba"
    elif "Samsung" in model:
        return "Samsung"
    elif "Crucial" in model or "Micron" in model:
        return "Micron"
    elif model.startswith("HGST") or model.startswith("Hitachi"):
        return "HGST/Hitachi"
    return "Unknown"

def analyze_disk(disk: DiskInfo) -> None:
    """Analyze disk attributes and populate issues list"""
    
    manufacturer = detect_manufacturer(disk.model)
    
    for attr_id, rule in ATTRIBUTE_RULES.items():
        if attr_id not in disk.attributes:
            continue
        
        attr = disk.attributes[attr_id]
        
        # Skip disk-type specific checks
        if rule.hdd_only and disk.disk_type != "HDD":
            continue
        if rule.ssd_only and disk.disk_type != "SSD":
            continue
        
        # Check normalized value
        if rule.check_normalized:
            # Special handling for Seagate Raw_Read_Error_Rate (ID 1)
            # Seagate enterprise drives start at 80-90, not 100
            # Check headroom from threshold instead of absolute value
            if attr_id == 1 and manufacturer == "Seagate":
                headroom = attr.value - attr.thresh
                if headroom < 10:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value} (headroom: {headroom} from THRESH={attr.thresh})",
                        "explanation": "Approaching failure threshold - excessive read errors",
                        "action": rule.action_critical
                    })
                    disk.overall_status = "CRITICAL"
                elif headroom < 20:
                    disk.issues.append({
                        "severity": "WARNING",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value} (headroom: {headroom} from THRESH={attr.thresh})",
                        "explanation": "Read error rate increasing but still acceptable for Seagate",
                        "action": "Monitor monthly, verify backups exist"
                    })
                    if disk.overall_status == "HEALTHY":
                        disk.overall_status = "WARNING"
                # If headroom >= 20, it's healthy - don't flag it
            else:
                # Standard normalized value checks for other attributes
                if attr.value <= rule.normalized_threshold:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value}",
                        "explanation": rule.explanation_critical,
                        "action": rule.action_critical
                    })
                    disk.overall_status = "CRITICAL"
                elif attr.value <= rule.normalized_warning and disk.overall_status != "CRITICAL":
                    disk.issues.append({
                        "severity": "WARNING",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value}",
                        "explanation": rule.explanation_warning,
                        "action": rule.action_warning
                    })
                    if disk.overall_status == "HEALTHY":
                        disk.overall_status = "WARNING"
        
        # Check raw value
        if rule.check_raw:
            try:
                raw_val = int(attr.raw_value.split()[0])
                if raw_val > rule.raw_threshold:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"RAW={raw_val}",
                        "explanation": rule.explanation_critical,
                        "action": rule.action_critical
                    })
                    disk.overall_status = "CRITICAL"
            except (ValueError, IndexError):
                pass

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_disk_report(disk: DiskInfo, verbose: bool = False) -> None:
    """Print detailed disk report"""
    
    # Status emoji and color
    status_map = {
        "HEALTHY": ("✅", "green"),
        "WARNING": ("⚠️ ", "yellow"),
        "CRITICAL": ("❌", "red")
    }
    emoji, color = status_map.get(disk.overall_status, ("❓", "white"))
    
    # Header
    header = f"{disk.device} - {disk.model} ({disk.capacity})"
    console.print(f"\n[bold]{emoji} {header}[/bold]")
    console.rule(style=color)
    
    # Basic info
    age_years = disk.power_on_hours / 8760
    console.print(f"Type: {disk.disk_type} | Power-On: {disk.power_on_hours:,}h ({age_years:.1f} years) | Temp: {disk.temperature}°C")
    console.print(f"SMART Health: [{color}]{disk.smart_health}[/{color}] | Our Analysis: [{color}]{disk.overall_status}[/{color}]")
    
    # Issues
    if disk.issues:
        console.print()
        for issue in disk.issues:
            sev_color = "red" if issue["severity"] == "CRITICAL" else "yellow"
            console.print(f"[{sev_color}]{'🚨' if issue['severity'] == 'CRITICAL' else '⚠️ '} {issue['attribute']} ({issue['value']})[/{sev_color}]")
            console.print(f"   ├─ {issue['explanation']}")
            console.print(f"   └─ Action: {issue['action']}")
    else:
        console.print("[green]✓ All monitored attributes healthy[/green]")
    
    # Verbose: show all attributes
    if verbose and disk.attributes:
        console.print("\n[dim]Monitored Attributes:[/dim]")
        for attr_id in sorted(ATTRIBUTE_RULES.keys()):
            if attr_id in disk.attributes:
                attr = disk.attributes[attr_id]
                console.print(f"  {attr.name:25s} VALUE={attr.value:3d} RAW={attr.raw_value}")

def print_summary(disks: List[DiskInfo]) -> int:
    """Print overall summary and return exit code"""
    
    healthy = sum(1 for d in disks if d.overall_status == "HEALTHY")
    warning = sum(1 for d in disks if d.overall_status == "WARNING")
    critical = sum(1 for d in disks if d.overall_status == "CRITICAL")
    
    console.print("\n")
    console.rule("[bold]SUMMARY[/bold]")
    
    summary_table = Table(show_header=False, box=box.SIMPLE)
    summary_table.add_column(style="bold")
    summary_table.add_column()
    
    summary_table.add_row("✅ Healthy", f"{healthy} disk(s)")
    summary_table.add_row("⚠️  Warning", f"{warning} disk(s)")
    summary_table.add_row("❌ Critical", f"{critical} disk(s)")
    
    console.print(summary_table)
    
    # Action items
    critical_disks = [d for d in disks if d.overall_status == "CRITICAL"]
    warning_disks = [d for d in disks if d.overall_status == "WARNING"]
    
    if critical_disks or warning_disks:
        console.print("\n[bold]Action Required:[/bold]")
        for disk in critical_disks:
            console.print(f"  🚨 {disk.device}: REPLACE WITHIN 24-48H")
        for disk in warning_disks:
            console.print(f"  ⚠️  {disk.device}: Monitor/test, replace in 1-4 weeks")
    
    # Determine exit code
    if critical:
        return 2
    elif warning:
        return 1
    else:
        return 0

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Disk Health Checker - SMART Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo ./disk-health-checker.py           # Check all disks
  sudo ./disk-health-checker.py -v        # Verbose (show all attributes)
  sudo ./disk-health-checker.py -q        # Quiet (summary only)
  sudo ./disk-health-checker.py --critical # Critical issues only

Exit Codes:
  0 = All disks healthy
  1 = Warnings detected
  2 = Critical issues found
        """
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all SMART attributes")
    parser.add_argument("-q", "--quiet", action="store_true", help="Summary only")
    parser.add_argument("--critical", action="store_true", help="Show only critical issues")
    
    args = parser.parse_args()
    
    # Root check
    if os.geteuid() != 0:
        console.print("[red]ERROR: Must run as root (use sudo)[/red]")
        sys.exit(1)
    
    # Header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    console.print(Panel.fit(
        f"[bold]DISK HEALTH REPORT[/bold]\n{timestamp}",
        border_style="blue"
    ))
    
    # Discover and analyze disks
    disk_paths = discover_disks()
    console.print(f"\n🔍 Found {len(disk_paths)} disk(s): {', '.join(disk_paths)}\n")
    
    disks = []
    for device in disk_paths:
        output = run_smartctl(device)
        if output:
            disk_info = parse_smart_output(device, output)
            if disk_info:
                analyze_disk(disk_info)
                disks.append(disk_info)
    
    # Filter and display
    if args.critical:
        disks = [d for d in disks if d.overall_status == "CRITICAL"]
    
    if not args.quiet:
        for disk in disks:
            format_disk_report(disk, verbose=args.verbose)
    
    # Summary
    exit_code = print_summary(disks)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()