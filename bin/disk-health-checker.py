#!/usr/bin/env python3
"""
__version__ = "1.1.0"
__author__ = "Gabriele Saronni"
__description__ = "SMART disk health analyzer - AI-assisted development"
__github__ = "https://github.com/gsaronni/disk-health-checker"

Disk Health Checker - SMART Analysis Tool
Analyzes disk health via smartctl and provides actionable recommendations.
Covers SATA/SAS (numbered attribute table) and NVMe (named health block).

Usage:
    sudo ./disk-health-checker.py               # Check all disks
    sudo ./disk-health-checker.py -v            # Verbose mode
    sudo ./disk-health-checker.py -q            # Quiet (summary only)
    sudo ./disk-health-checker.py --critical    # Critical issues only
    sudo ./disk-health-checker.py --json        # JSON to stdout, no rendering
    sudo ./disk-health-checker.py --json-out FILE  # JSON to a file

Exit Codes:
    0 = All disks healthy
    1 = Warnings detected (action needed in 1-4 weeks)
    2 = Critical issues (replace within 24-48h)

Dependencies:
    `rich` is optional. If unavailable, output falls back to plain text
    with the same structure (headers, per-issue blocks, summary table),
    just without color/box-drawing. This keeps the script runnable on
    machines you don't control the Python environment on (e.g. a
    Proxmox host without pip access).
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from smart_parser import (  # noqa: E402
    discover_disks,
    run_smartctl,
    parse_smart_output,
    DiskInfo,
)

# ============================================================================
# RICH — OPTIONAL, WITH PLAIN-TEXT FALLBACK
# ============================================================================

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

    _MARKUP_RE = re.compile(r"\[/?[a-zA-Z0-9 _]*\]")

    def _strip(text: str) -> str:
        return _MARKUP_RE.sub("", text)

    class Console:
        def print(self, *args, **kwargs):
            if not args:
                print()
                return
            for arg in args:
                print(_strip(str(arg)) if isinstance(arg, str) else str(arg))

        def rule(self, title: str = "", style=None):
            title = _strip(title)
            width = 72
            if title:
                pad = max(0, width - len(title) - 5)
                print(f"--- {title} " + "-" * pad)
            else:
                print("-" * width)

    class _PlainPanel:
        def __init__(self, text: str):
            self.text = _strip(text)

        def __str__(self):
            lines = self.text.split("\n")
            width = max((len(l) for l in lines), default=0) + 2
            border = "+" + "-" * width + "+"
            body = "\n".join(f"| {l.ljust(width - 1)}|" for l in lines)
            return f"{border}\n{body}\n{border}"

    class Panel:
        @staticmethod
        def fit(text, border_style=None):
            return _PlainPanel(text)

    class Table:
        def __init__(self, *args, show_header=True, header_style=None, box=None,
                     title=None, **kwargs):
            self.show_header = show_header
            self.title = _strip(title) if title else None
            self.columns = []
            self.rows = []

        def add_column(self, header: str = "", **kwargs):
            self.columns.append(_strip(header))

        def add_row(self, *cells):
            self.rows.append([_strip(str(c)) for c in cells])

        def __str__(self):
            widths = list(len(h) for h in self.columns)
            for row in self.rows:
                for i, c in enumerate(row):
                    if i >= len(widths):
                        widths.append(len(c))
                    else:
                        widths[i] = max(widths[i], len(c))
            lines = []
            if self.title:
                lines.append(self.title)
            if self.show_header and any(self.columns):
                header = "  ".join(h.ljust(widths[i]) for i, h in enumerate(self.columns))
                lines.append(header)
                lines.append("-" * len(header))
            for row in self.rows:
                lines.append(
                    "  ".join(
                        c.ljust(widths[i]) if i < len(widths) else c
                        for i, c in enumerate(row)
                    )
                )
            return "\n".join(lines)

    class box:  # noqa: N801 - matches rich's `box` module-as-namespace usage
        SIMPLE = None

console = Console()

# ============================================================================
# SATA/SAS ATTRIBUTE RULES DATABASE
# ============================================================================

from dataclasses import dataclass


@dataclass
class AttributeRule:
    """Rule definition for SATA/SAS SMART attribute analysis."""
    name: str
    check_normalized: bool = True
    check_raw: bool = False
    normalized_threshold: int = 10
    normalized_warning: int = 50
    raw_threshold: int = 0
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
        hdd_only=True,
    ),
    5: AttributeRule(
        name="Reallocated_Sector_Ct",
        check_raw=True,
        raw_threshold=10,
        explanation_critical="10+ bad sectors remapped - drive is failing",
        explanation_warning="1-10 bad sectors found and remapped",
        action_critical="Replace disk NOW. Data loss imminent.",
        action_warning="Acceptable if stable. Run extended test monthly.",
    ),
    7: AttributeRule(
        name="Seek_Error_Rate",
        normalized_threshold=30,
        normalized_warning=70,
        explanation_critical="Head positioning failures - mechanical wear severe",
        explanation_warning="Seek errors increasing (mechanical degradation)",
        action_critical="Replace within 1 week",
        action_warning="Monitor weekly, plan replacement in 1-3 months",
        hdd_only=True,
    ),
    9: AttributeRule(
        name="Power_On_Hours",
        check_normalized=False,
        check_raw=False,
        explanation_warning="Disk age reference (not a failure indicator)",
    ),
    10: AttributeRule(
        name="Spin_Retry_Count",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Spindle motor struggling to start - imminent failure",
        action_critical="Replace IMMEDIATELY (motor failure)",
        hdd_only=True,
    ),
    184: AttributeRule(
        name="End-to-End_Error",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Data path errors detected (firmware/controller issue)",
        action_critical="Replace within 48h - data integrity compromised",
    ),
    187: AttributeRule(
        name="Reported_Uncorrect",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Uncorrectable errors detected",
        action_critical="Backup immediately, replace within 24h",
    ),
    188: AttributeRule(
        name="Command_Timeout",
        normalized_threshold=1,
        normalized_warning=50,
        explanation_critical="Massive command timeouts (cable/power/controller failure)",
        explanation_warning="Some command timeouts detected",
        action_critical="Check SATA cable, PSU rails, controller. If OK -> replace disk",
        action_warning="Monitor. Try different SATA cable first.",
    ),
    193: AttributeRule(
        name="Load_Cycle_Count",
        normalized_threshold=5,
        normalized_warning=20,
        explanation_critical="Head parking mechanism exhausted - mechanical failure imminent",
        explanation_warning="Approaching head parking cycle limit",
        action_critical="Replace within 1-4 weeks",
        action_warning="Disable APM (hdparm -B 255) or plan replacement",
        hdd_only=True,
    ),
    197: AttributeRule(
        name="Current_Pending_Sector",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Sectors waiting to be remapped - active failure",
        action_critical="Backup NOW. Replace within 24h.",
    ),
    198: AttributeRule(
        name="Offline_Uncorrectable",
        check_raw=True,
        raw_threshold=0,
        explanation_critical="Uncorrectable sectors found during offline scan",
        action_critical="Replace within 48h",
    ),
    194: AttributeRule(
        name="Temperature_Celsius",
        check_normalized=False,
        check_raw=False,
        explanation_warning="Disk temperature (monitoring only)",
    ),
}

# ============================================================================
# ANALYSIS — SATA/SAS
# ============================================================================

def detect_manufacturer(model: str) -> str:
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


def analyze_sata_disk(disk: DiskInfo) -> None:
    manufacturer = detect_manufacturer(disk.model)

    for attr_id, rule in ATTRIBUTE_RULES.items():
        if attr_id not in disk.attributes:
            continue
        attr = disk.attributes[attr_id]

        if rule.hdd_only and disk.disk_type != "HDD":
            continue
        if rule.ssd_only and disk.disk_type != "SSD":
            continue

        if rule.check_normalized:
            if attr_id == 1 and manufacturer == "Seagate":
                headroom = attr.value - attr.thresh
                if headroom < 10:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value} (headroom: {headroom} from THRESH={attr.thresh})",
                        "explanation": "Approaching failure threshold - excessive read errors",
                        "action": rule.action_critical,
                    })
                    disk.overall_status = "CRITICAL"
                elif headroom < 20:
                    disk.issues.append({
                        "severity": "WARNING",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value} (headroom: {headroom} from THRESH={attr.thresh})",
                        "explanation": "Read error rate increasing but still acceptable for Seagate",
                        "action": "Monitor monthly, verify backups exist",
                    })
                    if disk.overall_status == "HEALTHY":
                        disk.overall_status = "WARNING"
            else:
                if attr.value <= rule.normalized_threshold:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value}",
                        "explanation": rule.explanation_critical,
                        "action": rule.action_critical,
                    })
                    disk.overall_status = "CRITICAL"
                elif attr.value <= rule.normalized_warning and disk.overall_status != "CRITICAL":
                    disk.issues.append({
                        "severity": "WARNING",
                        "attribute": attr.name,
                        "value": f"VALUE={attr.value}",
                        "explanation": rule.explanation_warning,
                        "action": rule.action_warning,
                    })
                    if disk.overall_status == "HEALTHY":
                        disk.overall_status = "WARNING"

        if rule.check_raw:
            try:
                raw_val = int(attr.raw_value.split()[0])
                if raw_val > rule.raw_threshold:
                    disk.issues.append({
                        "severity": "CRITICAL",
                        "attribute": attr.name,
                        "value": f"RAW={raw_val}",
                        "explanation": rule.explanation_critical,
                        "action": rule.action_critical,
                    })
                    disk.overall_status = "CRITICAL"
            except (ValueError, IndexError):
                pass


# ============================================================================
# ANALYSIS — NVMe
# ============================================================================

def analyze_nvme_disk(disk: DiskInfo) -> None:
    """NVMe has no numbered attribute table — rules key off named fields instead."""
    if disk.nvme is None:
        return
    n = disk.nvme

    if n.critical_warning != 0:
        disk.issues.append({
            "severity": "CRITICAL",
            "attribute": "Critical_Warning",
            "value": f"bitmap=0x{n.critical_warning:x}",
            "explanation": "Controller reports a critical condition (spare/temp/reliability/read-only/backup-device)",
            "action": "Run `smartctl -a` for the specific bit meaning, back up immediately",
        })
        disk.overall_status = "CRITICAL"

    if n.available_spare_pct <= n.available_spare_threshold_pct:
        disk.issues.append({
            "severity": "CRITICAL",
            "attribute": "Available_Spare",
            "value": f"{n.available_spare_pct}% (threshold {n.available_spare_threshold_pct}%)",
            "explanation": "Spare blocks exhausted - drive is at end of write-endurance life",
            "action": "Replace disk NOW. Data loss imminent.",
        })
        disk.overall_status = "CRITICAL"

    if n.percentage_used_pct >= 100:
        disk.issues.append({
            "severity": "CRITICAL",
            "attribute": "Percentage_Used",
            "value": f"{n.percentage_used_pct}%",
            "explanation": "Rated write endurance exceeded (vendor estimate, not a hard cutoff)",
            "action": "Replace within 1-4 weeks",
        })
        disk.overall_status = "CRITICAL"
    elif n.percentage_used_pct >= 90 and disk.overall_status != "CRITICAL":
        disk.issues.append({
            "severity": "WARNING",
            "attribute": "Percentage_Used",
            "value": f"{n.percentage_used_pct}%",
            "explanation": "Approaching rated write endurance",
            "action": "Plan replacement, verify backups",
        })
        if disk.overall_status == "HEALTHY":
            disk.overall_status = "WARNING"

    if n.media_errors > 0:
        disk.issues.append({
            "severity": "CRITICAL",
            "attribute": "Media_and_Data_Integrity_Errors",
            "value": f"{n.media_errors}",
            "explanation": "Uncorrectable media errors - data integrity at risk",
            "action": "Backup immediately, replace within 24-48h",
        })
        disk.overall_status = "CRITICAL"


def analyze_disk(disk: DiskInfo) -> None:
    if disk.disk_type == "NVMe":
        analyze_nvme_disk(disk)
    else:
        analyze_sata_disk(disk)


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def format_disk_report(disk: DiskInfo, verbose: bool = False) -> None:
    status_map = {
        "HEALTHY": ("[OK]", "green"),
        "WARNING": ("[!]", "yellow"),
        "CRITICAL": ("[X]", "red"),
    }
    emoji, color = status_map.get(disk.overall_status, ("[?]", "white"))

    header = f"{disk.device} - {disk.model} ({disk.capacity})"
    console.print(f"\n[bold]{emoji} {header}[/bold]")
    console.rule(style=color)

    age_years = disk.power_on_hours / 8760 if disk.power_on_hours else 0
    console.print(
        f"Type: {disk.disk_type} | Power-On: {disk.power_on_hours:,}h "
        f"({age_years:.1f} years) | Temp: {disk.temperature}C"
    )
    console.print(
        f"SMART Health: [{color}]{disk.smart_health}[/{color}] | "
        f"Our Analysis: [{color}]{disk.overall_status}[/{color}]"
    )

    if disk.issues:
        console.print()
        for issue in disk.issues:
            sev_color = "red" if issue["severity"] == "CRITICAL" else "yellow"
            marker = "!!" if issue["severity"] == "CRITICAL" else "! "
            console.print(f"[{sev_color}]{marker} {issue['attribute']} ({issue['value']})[/{sev_color}]")
            console.print(f"   |- {issue['explanation']}")
            console.print(f"   `- Action: {issue['action']}")
    else:
        console.print("[green]All monitored attributes healthy[/green]")

    if verbose:
        if disk.attributes:
            console.print("\n[dim]Monitored Attributes:[/dim]")
            for attr_id in sorted(ATTRIBUTE_RULES.keys()):
                if attr_id in disk.attributes:
                    attr = disk.attributes[attr_id]
                    console.print(f"  {attr.name:25s} VALUE={attr.value:3d} RAW={attr.raw_value}")
        elif disk.nvme:
            console.print("\n[dim]NVMe Health Fields:[/dim]")
            for key, val in asdict(disk.nvme).items():
                console.print(f"  {key:32s} {val}")


def print_summary(disks: List[DiskInfo]) -> int:
    healthy = sum(1 for d in disks if d.overall_status == "HEALTHY")
    warning = sum(1 for d in disks if d.overall_status == "WARNING")
    critical = sum(1 for d in disks if d.overall_status == "CRITICAL")

    console.print("\n")
    console.rule("[bold]SUMMARY[/bold]")

    summary_table = Table(show_header=False, box=box.SIMPLE)
    summary_table.add_column(style="bold")
    summary_table.add_column()

    summary_table.add_row("Healthy", f"{healthy} disk(s)")
    summary_table.add_row("Warning", f"{warning} disk(s)")
    summary_table.add_row("Critical", f"{critical} disk(s)")

    console.print(summary_table)

    critical_disks = [d for d in disks if d.overall_status == "CRITICAL"]
    warning_disks = [d for d in disks if d.overall_status == "WARNING"]

    if critical_disks or warning_disks:
        console.print("\n[bold]Action Required:[/bold]")
        for disk in critical_disks:
            console.print(f"  !! {disk.device}: REPLACE WITHIN 24-48H")
        for disk in warning_disks:
            console.print(f"  !  {disk.device}: Monitor/test, replace in 1-4 weeks")

    if critical:
        return 2
    elif warning:
        return 1
    return 0


def disks_to_json(disks: List[DiskInfo]) -> dict:
    """Structured, machine-readable snapshot — for occasional spot checks,
    not continuous history. Pipe through jq or diff two runs by hand."""
    return {
        "timestamp": datetime.now().isoformat(),
        "hostname": os.uname().nodename,
        "disks": [
            {
                "device": d.device,
                "model": d.model,
                "serial": d.serial,
                "capacity": d.capacity,
                "disk_type": d.disk_type,
                "smart_health": d.smart_health,
                "overall_status": d.overall_status,
                "power_on_hours": d.power_on_hours,
                "temperature": d.temperature,
                "issues": d.issues,
            }
            for d in disks
        ],
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Disk Health Checker - SMART Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo ./disk-health-checker.py               # Check all disks
  sudo ./disk-health-checker.py -v            # Verbose (show all attributes)
  sudo ./disk-health-checker.py -q            # Quiet (summary only)
  sudo ./disk-health-checker.py --critical    # Show only critical issues
  sudo ./disk-health-checker.py --json        # JSON to stdout
  sudo ./disk-health-checker.py --json-out /tmp/disks.json

Exit Codes:
  0 = All disks healthy
  1 = Warnings detected
  2 = Critical issues found
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all SMART attributes")
    parser.add_argument("-q", "--quiet", action="store_true", help="Summary only")
    parser.add_argument("--critical", action="store_true", help="Show only critical issues")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout instead of rendering")
    parser.add_argument("--json-out", metavar="FILE", help="Write JSON to FILE instead of stdout")

    args = parser.parse_args()

    if os.geteuid() != 0:
        console.print("[red]ERROR: Must run as root (use sudo)[/red]")
        sys.exit(1)

    disk_paths = discover_disks()

    json_mode = args.json or args.json_out
    if not json_mode:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        console.print(Panel.fit(f"[bold]DISK HEALTH REPORT[/bold]\n{timestamp}", border_style="blue"))
        console.print(f"\nFound {len(disk_paths)} disk(s): {', '.join(disk_paths)}\n")

    disks = []
    for device in disk_paths:
        output = run_smartctl(device)
        if output:
            disk_info = parse_smart_output(device, output)
            if disk_info:
                analyze_disk(disk_info)
                disks.append(disk_info)
        elif not json_mode:
            console.print(f"[yellow]Skipping {device}: no smartctl output (timeout or error)[/yellow]")

    if args.critical:
        disks = [d for d in disks if d.overall_status == "CRITICAL"]

    if json_mode:
        payload = json.dumps(disks_to_json(disks), indent=2)
        if args.json_out:
            Path(args.json_out).write_text(payload + "\n")
        else:
            print(payload)
    else:
        if not args.quiet:
            for disk in disks:
                format_disk_report(disk, verbose=args.verbose)
        exit_code = print_summary(disks)
        sys.exit(exit_code)

    critical = sum(1 for d in disks if d.overall_status == "CRITICAL")
    warning = sum(1 for d in disks if d.overall_status == "WARNING")
    sys.exit(2 if critical else 1 if warning else 0)


if __name__ == "__main__":
    main()