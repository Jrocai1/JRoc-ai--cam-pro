import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_firmware(file_path):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    result = {"file": path.name, "path": str(path.resolve()),
              "size_bytes": path.stat().st_size, "sha256": sha256_file(path),
              "archive_type": "unknown", "members": [], "components": {},
              "warnings": [], "authenticity_verified": False}
    try:
        if zipfile.is_zipfile(path):
            result["archive_type"] = "zip"
            with zipfile.ZipFile(path, "r") as archive:
                result["members"] = [{"name": x.filename, "size": x.file_size}
                                     for x in archive.infolist()[:5000]]
        elif path.name.lower().endswith((".tar", ".tar.md5", ".md5")):
            result["archive_type"] = "tar"
            with tarfile.open(path, "r:*") as archive:
                for index, member in enumerate(archive):
                    if index >= 5000:
                        result["warnings"].append("Member list truncated at 5000 entries.")
                        break
                    result["members"].append({"name": member.name, "size": member.size})
        else:
            result["warnings"].append("Unknown extension; archive not extracted.")
    except (OSError, ValueError, EOFError, tarfile.TarError, zipfile.BadZipFile) as exc:
        result["warnings"].append("Archive parsing failed: " + str(exc))
    names = [Path(x["name"]).name.upper() for x in result["members"]]
    for part in ("BL", "AP", "CP", "CSC", "HOME_CSC"):
        result["components"][part] = [n for n in names if n.startswith(part + "_") or n.startswith(part + ".")]
    if not any(result["components"].values()):
        result["warnings"].append("No common Samsung component filenames found.")
    result["warnings"].append("SHA-256 does not prove official origin or device compatibility.")
    return result


def _run(command, timeout=12):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                           check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"available": True, "returncode": p.returncode,
                "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}


def collect_diagnostics():
    report = {"os": os.environ.get("OS", os.name),
              "adb": {"available": False, "devices": []},
              "usb_devices": {"available": False, "devices": []},
              "flash_write_supported": False,
              "warnings": ["Read-only diagnostics only; no firmware writes are supported.",
                           "Download Mode devices may not appear in ADB."]}
    adb = shutil.which("adb")
    if adb:
        version = _run([adb, "version"])
        devices = _run([adb, "devices", "-l"])
        lines = devices.get("stdout", "").splitlines()[1:] if devices.get("returncode") == 0 else []
        report["adb"] = {"available": True, "version": version.get("stdout", ""),
                         "command": devices, "devices": [x.strip() for x in lines if x.strip()]}
    if os.name == "nt":
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            script = "Get-CimInstance Win32_PnPEntity | Where-Object {$_.PNPDeviceID -like 'USB*'} | Select-Object Name,PNPDeviceID,Status | ConvertTo-Json -Depth 3"
            output = _run([ps, "-NoProfile", "-NonInteractive", "-Command", script], 20)
            devices = []
            if output.get("returncode") == 0 and output.get("stdout"):
                try:
                    parsed = json.loads(output["stdout"])
                    devices = parsed if isinstance(parsed, list) else [parsed]
                except json.JSONDecodeError:
                    output["parse_error"] = "Invalid JSON from PowerShell."
            report["usb_devices"] = {"available": output.get("returncode") == 0,
                                     "devices": devices, "command": output}
    return report


def format_report(data):
    return json.dumps(data, indent=2, ensure_ascii=False)
