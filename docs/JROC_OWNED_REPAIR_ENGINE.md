# J-ROC-Owned Device Repair Engine — Architecture Directive

## Ownership requirement

J-ROC AI Universal Repair Suite PRO must implement and own its application code, user interface, orchestration, device registry, diagnostics framework, policy engine, firmware validation, repair workflow, evidence collection, audit log, local data model, tests, and installer integration.

Do not make third-party repair applications, paid repair SDKs, proprietary remote APIs, or external AI services mandatory runtime dependencies. Do not shell out to a third-party repair program and rebrand it as a J-ROC tool. Do not copy proprietary vendor software or reverse-engineer protected protocols in violation of applicable law.

## What J-ROC-owned means

- First-party source code maintained in J-ROC repositories, with clear licensing and dependency inventory.
- Local-first operation with no cloud account required for core diagnostics.
- Internal device abstraction and capability registry.
- First-party diagnostics, decision rules, workflow engine, UI, evidence and reporting.
- Reproducible builds and automated tests.
- Explicit disclosure for unavoidable platform interfaces, operating-system APIs, USB transport libraries, device drivers, firmware signing requirements, and vendor restrictions.

Open-source general-purpose libraries may be used only if reviewed and approved, license-compatible, inventoried, and replaceable where practical. They are supporting dependencies, not the repair product itself. Platform interfaces and device drivers are not represented as J-ROC inventions.

## First-party architecture

1. jroc_device_core: device identity, lifecycle, capability negotiation, transport abstraction, timeouts and cancellation.
2. jroc_usb_transport: own transport orchestration over documented operating-system interfaces; enumerate devices, permissions, descriptors and connection state.
3. jroc_diagnostics: model-aware, read-only checks with structured results and evidence.
4. jroc_firmware_lab: package inspection, metadata/model matching, cryptographic hash verification, signature validation when format/key material permits, compatibility policy and provenance.
5. jroc_recovery_engine: explicit state machine for supported recovery actions, prerequisites, user approval, cancellation, rollback guidance and outcome verification.
6. jroc_policy_guard: default deny for unsupported or high-impact operations; explicit approvals for firmware writes, resets, OS reinstall and other destructive actions.
7. jroc_evidence_ledger: local audit events, logs, report export, redaction and integrity checks.
8. jroc_automation: worker queue, bounded retries, operator review, failure isolation and observable state transitions.
9. jroc_device_profiles: versioned, signed capability profiles for each tested device/model/OS/firmware combination.
10. jroc_windows_shell: Windows 11 x64 user interface, local API, database, installer, updater and diagnostics console.

## Device families

Use one shared engine with first-party profiles/adapters for smartphones and tablets (Apple, Samsung, other Android devices); Windows laptops, desktops, workstations and mini PCs; Apple computers using documented platform-supported workflows; and storage devices, printers, cameras, wearables, network equipment and other electronics where interfaces are available.

Do not claim every family has equivalent functionality. Each profile must specify supported operations, prerequisites, transport, identity confidence, tested models, known limits and evidence requirements.

## Engineering rules

- Read-only by default; all unknown operations are denied.
- No third-party repair application as the actual repair engine.
- No fabricated progress, device identity, firmware compatibility or success result.
- No security-lock, passcode, account, activation, FRP, MDM or other access-control bypass.
- Firmware writes must verify target identity, package compatibility, provenance, required signatures, power and connection state, operator authorization, and safe recovery options.
- If a vendor protocol is undocumented or protected, use a documented interface where possible or mark the operation unsupported until a lawful, safe implementation is available.
- Separate simulations from physical-device tests.
- Keep secrets out of source code and logs.

## Delivery stages

A. Finish and test the first-party registry and policy unit tests.
B. Implement Windows device enumeration and safe read-only device inventory.
C. Implement diagnostic result schemas, SQLite evidence ledger, and repair-session API.
D. Implement model-specific Samsung/Android and Apple profiles with capability checks.
E. Implement Windows computer diagnostics.
F. Add firmware package inspection and validation before any write functionality.
G. Implement recovery state machines only for combinations validated on physical hardware.
H. Build the Windows installer and publish a compatibility matrix and test report.

## Release gate

Do not label the suite production-ready until tests run successfully, the application is packaged on Windows x64, supported physical devices are validated, installer/uninstaller/upgrade behavior is checked, and limitations are documented.
