"""Read-only desktop device discovery and firmware package inspection."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_firmware(file_path: str | Path) -> dict[str, Any]:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    result: dict[str, Any] = {
        "file": path.name,
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "archive_type": "unknown",
        "members": [],
        "components": {},
        "authenticity_verified": False,
        "warnings": [],
    }
    try:
        if zipfile.is_zipfile(path):
            result["archive_type"] = "zip"
            with zipfile.ZipFile(path, "r") as archive:
                result["members"] = [
                    {"name": member.filename, "size": member.file_size}
                    for member in archive.infolist()[:5000]
                ]
        elif path.name.lower().endswith((".tar", ".tar.md5", ".md5")):
            result["archive_type"] = "tar"
            with tarfile.open(path, "r:*") as archive:
                for index, member in enumerate(archive):
                    if index >= 5000:
                        result["warnings"].append("Member list truncated at 5000 entries.")
                        break
                    result["members"].append({"name": member.name, "size": member.size})
        else:
            result["warnings"].append("Unknown file extension; archive was not extracted.")
    except (OSError, ValueError, EOFError, tarfile.TarError, zipfile.BadZipFile) as exc:
        result["warnings"].append("Archive parsing failed: " + str(exc))

    names = [Path(str(item["name"])).name.upper() for item in result["members"]]
    for component in ("BL", "AP", "CP", "CSC", "HOME_CSC"):
        result["components"][component] = [
            name for name in names
            if name.startswith(component + "_") or name.startswith(component + ".")
        ]
    if not any(result["components"].values()):
        result["warnings"].append("No common Samsung firmware component filenames found.")
    result["warnings"].append(
        "Inspection and SHA-256 do not prove official origin or device/model compatibility."
    )
    result["warnings"].append(
        "Firmware writes are disabled in J-Roc AI Mobile Repair; no device was modified."
    )
    return result


def _run(command: list[str], timeout: int = 12) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        return {
            "available": True,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}


def collect_diagnostics() -> dict[str, Any]:
    report: dict[str, Any] = {
        "application": "J-Roc AI Mobile Repair",
        "os": os.environ.get("OS", os.name),
        "adb": {"available": False, "devices": [], "note": "Install Android Platform Tools for ADB."},
        "fastboot": {"available": False, "devices": [], "note": "Fastboot enumeration is read-only."},
        "usb_devices": {"available": False, "devices": [], "note": "Windows PowerShell/CIM is used on Windows."},
        "firmware_writes_supported": False,
        "warnings": [
            "Device diagnostics are read-only; this application does not flash or modify devices.",
            "ADB only reports devices exposed in the current Android state; Download Mode may not appear.",
            "A device or interface may require an official manufacturer driver."
        ],
    }
    adb = shutil.which("adb")
    if adb:
        version = _run([adb, "version"])
        devices = _run([adb, "devices", "-l"])
        lines = devices.get("stdout", "").splitlines()[1:] if devices.get("returncode") == 0 else []
        report["adb"] = {
            "available": True,
            "version": version.get("stdout", ""),
            "command": devices,
            "devices": [line.strip() for line in lines if line.strip()],
        }
    fastboot = shutil.which("fastboot")
    if fastboot:
        devices = _run([fastboot, "devices"])
        report["fastboot"] = {
            "available": True,
            "command": devices,
            "devices": [line.strip() for line in devices.get("stdout", "").splitlines() if line.strip()],
        }
    if os.name == "nt":
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            script = (
                "Get-CimInstance Win32_PnPEntity | "
                "Where-Object {$_.PNPDeviceID -like 'USB*'} | "
                "Select-Object Name,PNPDeviceID,Status | ConvertTo-Json -Depth 3"
            )
            output = _run([powershell, "-NoProfile", "-NonInteractive", "-Command", script], 20)
            devices: list[Any] = []
            if output.get("returncode") == 0 and output.get("stdout"):
                try:
                    parsed = json.loads(output["stdout"])
                    devices = parsed if isinstance(parsed, list) else [parsed]
                except json.JSONDecodeError:
                    output["parse_error"] = "Invalid JSON returned by PowerShell."
            report["usb_devices"] = {
                "available": output.get("returncode") == 0,
                "devices": devices,
                "command": output,
            }
    return report


def format_report(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
