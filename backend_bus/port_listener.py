"""Read-only USB/serial inventory for the local CAM PRO bench.

No commands in this module write to devices, change device modes, or flash firmware.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeviceRecord:
    device_id: str
    bus: str
    description: str
    port: str | None = None
    vid: str | None = None
    pid: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    serial_number: str | None = None
    mode: str = "unknown"
    mock: bool = False


def _mock_records() -> list[DeviceRecord]:
    return [DeviceRecord(
        device_id="MOCK-USB-001", bus="USB", description="Synthetic Android test device",
        port="MOCK", vid="18D1", pid="4EE7", manufacturer="Simulation",
        product="CAM PRO Virtual Device", mode="mock", mock=True,
    )]


def _serial_records() -> list[DeviceRecord]:
    try:
        from serial.tools import list_ports  # type: ignore[import-not-found]
    except ImportError:
        LOGGER.info("pyserial is not installed; COM-port discovery is unavailable.")
        return []
    records: list[DeviceRecord] = []
    for port in list_ports.comports():
        records.append(DeviceRecord(
            device_id=str(port.device), bus="SERIAL",
            description=str(port.description or "Serial port"),
            port=str(port.device),
            vid=f"{port.vid:04X}" if port.vid is not None else None,
            pid=f"{port.pid:04X}" if port.pid is not None else None,
            manufacturer=port.manufacturer, product=port.product,
            serial_number=None, mode="detected", mock=False,
        ))
    return records


def _windows_usb_records() -> list[DeviceRecord]:
    """Query Windows Plug-and-Play metadata without changing device state."""
    if os.name != "nt" or not shutil.which("powershell"):
        return []
    script = (
        "$ErrorActionPreference='Stop'; "
        "Get-PnpDevice -PresentOnly -Class USB -ErrorAction SilentlyContinue | "
        "Select-Object -Property InstanceId,FriendlyName,Status | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=False, capture_output=True, text=True, timeout=5,
            shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        raw: Any = json.loads(result.stdout)
        items = raw if isinstance(raw, list) else [raw]
        records: list[DeviceRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            instance_id = str(item.get("InstanceId") or "")
            # Preserve only the VID/PID metadata, not the full hardware instance ID,
            # because instance IDs can contain serial-like identifiers.
            vid_pid = __import__("re").search(r"VID_([0-9A-Fa-f]{4}).*PID_([0-9A-Fa-f]{4})", instance_id)
            records.append(DeviceRecord(
                device_id=f"USB-{vid_pid.group(1).upper()}-{vid_pid.group(2).upper()}" if vid_pid else "USB-DEVICE",
                bus="USB", description=str(item.get("FriendlyName") or "USB device")[:200],
                vid=vid_pid.group(1).upper() if vid_pid else None,
                pid=vid_pid.group(2).upper() if vid_pid else None,
                mode=str(item.get("Status") or "detected").lower(), mock=False,
            ))
        return records
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        LOGGER.warning("Windows USB metadata query failed: %s", exc)
        return []


def discover_devices(*, mock: bool = False) -> list[DeviceRecord]:
    """Return synthetic records in mock mode, otherwise read-only host inventory."""
    if mock:
        return _mock_records()
    records = _serial_records() + _windows_usb_records()
    # De-duplicate on bus and device_id; some Windows adapters expose both records.
    unique: dict[tuple[str, str], DeviceRecord] = {}
    for record in records:
        unique[(record.bus, record.device_id)] = record
    return list(unique.values())


def records_as_dicts(records: list[DeviceRecord]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Read-only CAM PRO device inventory")
    parser.add_argument("--mock", action="store_true", help="emit a clearly labelled synthetic device")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    output = {"count": len(discover_devices(mock=args.mock)), "devices": records_as_dicts(discover_devices(mock=args.mock))}
    print(json.dumps(output, indent=2 if args.pretty else None))
