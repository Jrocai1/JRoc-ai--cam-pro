# Universal Device Repair Support — Foundation Plan

## Product goal

Expand J-ROC AI Universal Repair Suite PRO into one Windows 11 x64 application for software-based inspection and supported recovery of smartphones, tablets, laptops, desktops, workstations, mini PCs, wearables, printers, cameras, network devices, and storage devices.

This document describes an implementation roadmap. It does not claim that every device or repair operation is already implemented.

## Core architecture

1. **Device Discovery** — USB, Bluetooth, serial, network, and OS-enumerated devices through isolated adapters with explicit permissions.
2. **Identity & Compatibility** — vendor, model, hardware revision, OS/build, connection mode, and confidence/evidence; never guess a model from weak signals.
3. **Capability Registry** — model-specific allow-list of read-only diagnostics, logs, supported recovery, firmware verification, and any approved write operation.
4. **Diagnostics Engine** — structured checks, timeouts, cancellation, redacted logs, and clear evidence-backed outcomes.
5. **Recovery & Firmware** — vendor-supported tools only; verify model, package provenance, cryptographic hashes/signatures where available, power/connection prerequisites, and rollback/recovery options.
6. **Approval Gate** — destructive or state-changing actions require a human confirmation that names the exact device, operation, and data-loss risk.
7. **Repair Case & Evidence** — SQLite-first local records, operation history, logs, before/after status, operator notes, and exportable report.
8. **Unified UI** — Overview, Devices, Diagnostics, Recovery, Firmware, Automation Queue, Repair Cases, Reports, Audit & Security, Settings.
9. **Windows Packaging** — x64 installer, driver/dependency disclosures, signed release when signing is available, upgrade/uninstall behavior, and CI artifact validation.

## Device families

- Smartphones and tablets: Apple, Samsung, and other Android vendors, each with separate compatibility adapters.
- Computers: Windows PCs, laptops, desktops, workstations, mini PCs; operating-system health and supported recovery tools.
- Apple computers: macOS devices with documented Apple-supported management/recovery paths.
- Wearables and accessories: discovery and supported diagnostics only where vendor interfaces exist.
- Printers, cameras, network devices, and storage: network/USB discovery, status, configuration backup where authorized, logs, and vendor-supported firmware checks.

## Safety and honesty requirements

- Read-only by default.
- No universal-flashing claims. Capability is enabled only after a vendor/model adapter verifies support.
- No bypass of passcodes, Activation Lock, FRP, account locks, MDM, or other access controls.
- No credential extraction or unauthorized network access.
- Factory reset, firmware writes, OS reinstall, bootloader changes, and other destructive actions require explicit approval and clear data-loss warnings.
- A simulated result must be labelled SIMULATION. A real result requires execution evidence.
- If no safe adapter exists, show diagnostics and official support guidance rather than inventing a repair action.

## Implementation phases

1. Shared registry and safety policy with unit tests.
2. Hardware-independent device records, audit events, and SQLite persistence.
3. Windows discovery adapters (Plug and Play, USB, serial) and safe OS diagnostics.
4. Android/Samsung and Apple mobile adapters with explicit capability limits.
5. Windows PC diagnostics and supported recovery.
6. Additional vendor adapters based on public APIs/tools and physical-device validation.
7. Installer, automated tests, compatibility matrix, and release checklist.

## Acceptance criteria

- Every device operation reports the detected identity, adapter, prerequisites, risk, and evidence.
- Unknown devices are registered as unknown; no guessed model.
- Destructive actions are blocked without approval.
- Hardware tests and mock tests are clearly separated.
- The release states tested models and known limitations.
