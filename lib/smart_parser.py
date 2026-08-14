#!/usr/bin/env python3
"""
smart_parser.py — shared smartctl output parsing.

Handles both SATA/SAS (numbered attribute table) and NVMe (named
"SMART/Health Information" block) output from `smartctl -a`, since
they're structurally different and previously only SATA was parsed.

Used by bin/disk-health-checker.py. Not a standalone tool.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================================
# DISCOVERY / EXECUTION
# ============================================================================

def discover_disks() -> List[str]:
    """Discover all physical disks (exclude partitions, loop, dm-crypt)."""
    disks = []
    for device in Path("/dev").glob("sd[a-z]"):
        disks.append(str(device))
    for device in Path("/dev").glob("nvme[0-9]n[0-9]"):
        disks.append(str(device))
    return sorted(disks)


def run_smartctl(device: str, timeout: int = 10) -> Optional[str]:
    """Run smartctl -a with a timeout. Returns stdout, or None on failure/timeout."""
    try:
        result = subprocess.run(
            ["smartctl", "-a", device],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        print("ERROR: smartctl not found. Install smartmontools", file=sys.stderr)
        sys.exit(1)
    except Exception:
        return None


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SmartAttribute:
    """A single SATA/SAS numbered SMART attribute row."""
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
class NvmeHealth:
    """NVMe health fields. NVMe has no numbered attribute table — smartctl
    reports named fields under 'SMART/Health Information' instead."""
    critical_warning: int = 0
    temperature_c: int = 0
    available_spare_pct: int = 100
    available_spare_threshold_pct: int = 10
    percentage_used_pct: int = 0
    data_units_written: int = 0
    power_on_hours: int = 0
    unsafe_shutdowns: int = 0
    media_errors: int = 0


@dataclass
class DiskInfo:
    device: str
    model: str
    serial: str
    capacity: str
    disk_type: str  # HDD, SSD, NVMe
    rotation_rate: str
    smart_enabled: bool
    smart_health: str
    attributes: Dict[int, SmartAttribute] = field(default_factory=dict)
    nvme: Optional[NvmeHealth] = None
    overall_status: str = "HEALTHY"
    issues: List[Dict] = field(default_factory=list)
    power_on_hours: int = 0
    temperature: int = 0


# ============================================================================
# PARSING
# ============================================================================

def parse_smart_output(device: str, output: str) -> Optional[DiskInfo]:
    """Parse smartctl -a output. Dispatches to SATA or NVMe parser by device path."""
    if "nvme" in device:
        return _parse_nvme(device, output)
    return _parse_sata(device, output)


def _parse_sata(device: str, output: str) -> Optional[DiskInfo]:
    model = re.search(r"Device Model:\s+(.+)", output)
    serial = re.search(r"Serial Number:\s+(.+)", output)
    capacity = re.search(r"User Capacity:\s+[\d,]+ bytes \[(.+?)\]", output)
    rotation = re.search(r"Rotation Rate:\s+(.+)", output)
    smart_enabled = "SMART support is: Enabled" in output
    smart_health = re.search(r"SMART overall-health.*:\s+(\w+)", output)

    if not smart_enabled:
        return None

    disk_type = "HDD"
    rotation_rate = "Unknown"
    if rotation:
        rotation_rate = rotation.group(1).strip()
        if "Solid State Device" in rotation_rate or "SSD" in rotation_rate:
            disk_type = "SSD"

    attributes: Dict[int, SmartAttribute] = {}
    attr_section = re.search(
        r"ID# ATTRIBUTE_NAME.*?\n(.*?)(?:\n\n|SMART Error Log)",
        output,
        re.DOTALL,
    )
    if attr_section:
        for line in attr_section.group(1).strip().split("\n"):
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
                    raw_value=" ".join(parts[9:]),
                )

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
        model=model.group(1).strip() if model else "Unknown",
        serial=serial.group(1).strip() if serial else "Unknown",
        capacity=capacity.group(1) if capacity else "Unknown",
        disk_type=disk_type,
        rotation_rate=rotation_rate,
        smart_enabled=smart_enabled,
        smart_health=smart_health.group(1) if smart_health else "UNKNOWN",
        attributes=attributes,
        power_on_hours=power_on_hours,
        temperature=temperature,
    )


def _parse_nvme(device: str, output: str) -> Optional[DiskInfo]:
    model = re.search(r"Model Number:\s+(.+)", output)
    serial = re.search(r"Serial Number:\s+(.+)", output)
    capacity = re.search(r"Namespace 1 Size/Capacity:\s+([\d,]+\s*\[[^\]]+\])", output)
    smart_health = re.search(
        r"SMART overall-health self-assessment test result:\s+(\w+)", output
    )
    smart_enabled = smart_health is not None or "SMART/Health Information" in output

    if not smart_enabled:
        return None

    def _num(pattern, cast=int, default=0):
        m = re.search(pattern, output)
        if not m:
            return default
        raw = m.group(1).replace(",", "")
        try:
            return cast(raw)
        except ValueError:
            return default

    nvme = NvmeHealth(
        critical_warning=_num(r"Critical Warning:\s+(0x[0-9a-fA-F]+)", lambda v: int(v, 16)),
        temperature_c=_num(r"Temperature:\s+(\d+)\s*Celsius"),
        available_spare_pct=_num(r"Available Spare:\s+(\d+)%", default=100),
        available_spare_threshold_pct=_num(r"Available Spare Threshold:\s+(\d+)%", default=10),
        percentage_used_pct=_num(r"Percentage Used:\s+(\d+)%"),
        data_units_written=_num(r"Data Units Written:\s+([\d,]+)"),
        power_on_hours=_num(r"Power On Hours:\s+([\d,]+)"),
        unsafe_shutdowns=_num(r"Unsafe Shutdowns:\s+([\d,]+)"),
        media_errors=_num(r"Media and Data Integrity Errors:\s+([\d,]+)"),
    )

    return DiskInfo(
        device=device,
        model=model.group(1).strip() if model else "Unknown",
        serial=serial.group(1).strip() if serial else "Unknown",
        capacity=capacity.group(1) if capacity else "Unknown",
        disk_type="NVMe",
        rotation_rate="N/A (NVMe)",
        smart_enabled=smart_enabled,
        smart_health=smart_health.group(1) if smart_health else "UNKNOWN",
        nvme=nvme,
        power_on_hours=nvme.power_on_hours,
        temperature=nvme.temperature_c,
    )