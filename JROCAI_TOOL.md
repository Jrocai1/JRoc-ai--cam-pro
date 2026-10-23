# Jrocai Tool
## Official Device Servicing Utility of J-ROC AI PRO

Jrocai Tool is the official device servicing and repair utility framework for J-ROC AI PRO. Its product goals are a clean, modern, ad-free Windows desktop experience, privacy-first defaults, transparent diagnostics, and reliable repair-shop workflows.

**Status notice:** This document establishes the official product direction. It does not mean every planned feature is implemented or verified. See the repository's releases, test results, and feature matrix for confirmed capabilities.

## Product principles

- No advertising, ad redirects, or hidden telemetry by default.
- Local-first storage for diagnostics, repair tickets, inventory, and reports wherever practical.
- Clear consent before collecting, exporting, or sending diagnostic data to an external service.
- Firmware integrity verification using trusted checksums and signatures when available.
- Explicit confirmation before destructive operations, with the target device and data-loss risks clearly displayed.
- Honest results: show actual tool output, exit status, and verification state.
- Support only devices the technician owns or is authorized to service.

## Planned modules

### Device discovery and diagnostics
- Discover Android devices through ADB and supported bootloader connections through Fastboot.
- Read available device properties and connection status.
- Monitor Windows device arrival/removal events.
- Produce diagnostic reports with sensitive identifiers redacted by default.
- Explain missing drivers and dependencies with links to official sources.

### Firmware and recovery
- Verify firmware file hashes and supported signatures.
- Check model/variant compatibility before a firmware workflow.
- Provide preflight checks for battery, cable, backups, package source, and expected data loss.
- Guide technicians through supported manufacturer recovery and restore processes.
- Stop by default when a checksum, signature, or compatibility check fails.

### Samsung and Android
- Authorized device identification and read-only diagnostics.
- Firmware package organization and compatibility checks.
- Supported ADB app installation and package inspection with owner authorization.
- Documented, reversible device-management actions where the device and operating system permit them.

### Apple
- Detect supported Normal, Recovery, and DFU connection states when required drivers and tools are available.
- Display available device and connection information.
- Guide users through official Apple update, recovery, and restore workflows.

### Repair-shop operations
- Repair tickets, status history, technician notes, and audit events.
- Parts inventory and stock validation.
- Draft estimates with itemized parts, labor, and tax.
- Searchable technician notes and local reports.
- Multi-device job queues with independent logs and cancellation.
- Optional AI-assisted log explanations that do not automatically execute suggested fixes.

## Security boundaries

Jrocai Tool is for authorized diagnostics and repair. It is not intended to defeat account protections, anti-theft locks, carrier restrictions, or other access controls, alter device identity values, or inject authentication-bypass payloads. For locked devices, use manufacturer account recovery, proof-of-ownership procedures, or an authorized service channel.

## Firmware Repository & Direct Downloader

The Firmware Hub is a planned first-class module that helps technicians find and download firmware from official manufacturer channels or other explicitly authorized, trusted repositories. Its purpose is to avoid advertising redirects, deceptive download buttons, and unverified mirror packages.

### Planned workflow

1. **Identify the device conservatively.** Read model and region/CSC information only when the connected device and supported interface expose it. Do not require an IMEI for ordinary firmware discovery, and do not transmit IMEI, serial numbers, or other unique identifiers to a repository by default.
2. **Find a trusted source.** Use official manufacturer endpoints or a repository whose authorization, provenance, and distribution terms have been reviewed. Display the source, model/variant, region, version, file size, and any known release metadata before download.
3. **Download directly.** Stream the file to a user-selected workspace with progress, cancellation, timeouts, disk-space checks, and a partial `.download` file. Only rename it to the final filename after the transfer completes and validation succeeds.
4. **Validate integrity.** Verify a signed manifest or trusted published SHA-256 hash where available. If only MD5 is supplied, show that it is a legacy integrity check and not a modern authenticity guarantee. A mismatch, incomplete transfer, invalid signature, or missing required validation must mark the package unverified and block it from being queued for flashing by default.
5. **Preflight before servicing.** Check exact model/variant and region compatibility where reliable metadata exists. Show data-loss risks and require a separate confirmation before any device-write operation.
6. **Keep an audit record.** Store the source, timestamp, package name, size, expected and computed hashes, validation result, and user-selected destination locally. Redact device identifiers.

### Downloader security requirements

- HTTPS only; reject insecure redirects and restrict downloads to approved hostnames.
- Never accept arbitrary URLs from a device or remote manifest without validation.
- Protect against path traversal, filename spoofing, oversized downloads, insufficient disk space, and partial-file confusion.
- Use cancellation tokens and bounded buffers; do not load multi-gigabyte firmware archives into memory.
- Do not follow ad redirects, scrape access-controlled endpoints, or bypass repository authentication or rate limits.
- Do not silently ignore MD5 or SHA-256 mismatches. Failed validation must be explicit and cannot be marked as verified.
- Keep downloads separate from the flash queue until validation and compatibility checks pass.
- Firmware discovery/download is distinct from flashing. No package should be flashed automatically merely because its download completed.

### Intended Firmware Hub interface

The WPF module should provide search by model code, region/CSC, and firmware version; trusted-source labels; release metadata; download progress and cancellation; checksum/signature status; local download history; and a clear validation report. If the repository does not expose a trustworthy direct-download API or verifiable manifest, the app should say so instead of fabricating a download link or claiming official provenance.

## Open-source servicing engines and niche chipset modules

The architecture may support additional device families through adapters for reputable open-source projects and official manufacturer utilities. Every adapter must be independently reviewed, pinned to a known version, license-checked, tested, and clearly identified in the UI. A listed integration is planned unless a release note and test result confirm it is implemented.

### MediaTek (MTKClient)

- Planned adapter for supported MediaTek device identification and documented recovery/firmware workflows.
- Bundle or install dependencies only when the upstream license permits redistribution; otherwise provide a verified setup/download route.
- Do not expose authentication-bypass payload injection, anti-theft bypasses, or automated extraction of private user data, credentials, or device identity material.
- Partition reads/writes must be explicit, narrowly scoped, device/model-validated, logged, and gated by authorization and confirmation. No broad userdata/NVRAM dumping by default.

### Xiaomi / Mi Flash / Fastboot

- Provide an adapter for official Xiaomi servicing tools and documented Fastboot or sideload workflows where supported.
- Validate the exact model and firmware package, show the source and expected data-loss impact, and stop on integrity or compatibility errors.
- Do not bypass Mi Account/cloud locks or inject recovery images to evade account protections.

### LG UP and LG firmware

- Provide guided integration with official LG UP/KDZ workflows when the required tool and device are supported and legally available.
- Make model compatibility, package provenance, and data-loss warnings explicit.
- Do not automate FRP removal or other account-protection circumvention.

### Qualcomm EDL and Spreadtrum/Unisoc

- Consider adapters only for documented, authorized diagnostics and manufacturer-supported recovery procedures.
- Use only properly licensed and verified loaders and packages. Do not bundle proprietary loaders without redistribution rights.
- Do not provide authentication bypasses, exploit payloads, or unrestricted partition erasure/write features. Unsupported or ambiguous devices must fail closed.

### Adapter requirements

Each engine must have a capability manifest listing its version, upstream source, license, supported operating systems and device families, allowed operations, required drivers, and known risks. Commands must use an executable allow-list and structured arguments; never concatenate untrusted user input into shell commands. Default to read-only inspection, with separate confirmations for write or erase operations. Test adapters with mocks and safe fixtures before hardware testing.

## Planned technology stack

- C# and .NET 8.
- Windows Presentation Foundation (WPF) with MVVM separation.
- Controlled process execution for approved tools.
- Windows device notifications through supported Windows APIs or WMI.
- System.IO.Ports only for documented, authorized serial workflows.
- SQLite for local records where appropriate.
- SHA-256 integrity checks and signature verification.
- Optional AI providers behind explicit opt-in controls.

Obtain ADB, Fastboot, Apple support components, and manufacturer utilities from official sources. Respect their licenses; do not redistribute third-party binaries unless permitted.

## Intended directory structure

```text
JrocaiTool/
├── src/
│   ├── Core/
│   ├── ViewModels/
│   ├── Views/
│   ├── Services/
│   └── Data/
├── tests/
├── docs/
├── resources/
├── JrocaiTool.sln
└── README.md
```

This is the intended structure, not a claim that every directory or feature already exists.

## Windows 11 development

1. Install Visual Studio with the .NET desktop development workload.
2. Install the .NET 8 SDK.
3. Open the solution when available, restore dependencies, and build.
4. Run automated tests before connecting a physical device.
5. Test only on owner-authorized, non-critical devices and preserve diagnostic logs.

When the solution exists, the expected build/test commands are:

```powershell
dotnet restore .\JrocaiTool.sln
dotnet build .\JrocaiTool.sln --configuration Release
dotnet test .\JrocaiTool.sln --configuration Release
```

## Next-generation enhancements

- Multi-device queues with per-device locking, cancellation, and separate logs.
- Local AI log diagnostics that suggest explanations without automatically applying fixes.
- An ad-free updater using official release metadata and verified artifacts.
- A compatibility registry of tested models, OS versions, and tool versions.
- Local-first privacy controls and explicit consent for external AI processing.
- Automated tests, dependency checks, and release checksums.

## Release requirements

Each release should include a version and change log, supported Windows versions, tested device/model combinations, installation and uninstall instructions, known limitations, recovery guidance, and SHA-256 checksums. CI without physical hardware does not establish device compatibility. AI-provider features require separate tests and must never include committed API keys.

## Disclaimer

Provided as-is unless a separate written agreement says otherwise. Device servicing may cause data loss or device failure. Back up customer data, obtain informed consent, verify the exact model and firmware, and follow applicable law, manufacturer terms, and third-party software licenses. Do not disable security software simply because a tool is flagged; investigate the detection and review dependencies.
