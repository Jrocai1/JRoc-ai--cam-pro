# J-ROC AI CAM PRO — Plug-and-Play Web Interface

## What this adds

- A responsive local-first bench control interface served by the existing Python standard-library dashboard server.
- Overview, device discovery, bench sessions, AI technician triage, plug-and-play integration status, and settings/safety pages.
- Live API health indicator, device/session refresh, session creation, and advisory triage requests.
- Clear distinction between connected, optional, unverified, and disabled capabilities.
- A Windows launcher that creates an isolated Python virtual environment, installs the declared requirements, and starts the local service.

## Windows 11 x64 quick start

1. Install Python 3.12 x64 and enable the Python launcher.
2. Download or clone this repository and extract it to a writable folder.
3. Double-click Install-And-Run-CAM-PRO.bat.
4. Wait for the local service to start and open http://127.0.0.1:8787.
5. Keep the terminal window open while using the dashboard. Press Ctrl+C to stop the service.

The launcher uses .venv so its Python dependencies are isolated from other applications. It does not install device drivers, modify firmware, or perform device-changing operations.

## Local routes used by the interface

- GET /api/status — service/version/mode status.
- GET /api/devices — read-only USB/COM inventory.
- GET /api/sessions — locally saved bench sessions.
- POST /api/sessions — create a session in the local SQLite database.
- POST /api/triage — advisory worker triage; technician review remains required.

The interface is served as a single self-contained HTML file at dashboard_ui/index.html; it does not require a separate JavaScript package install to render the local bench dashboard.

## Plug-and-play behavior

- The UI checks the local API and shows an offline state if it cannot connect.
- Device scan results are fetched from the actual local API; synthetic results must be explicitly marked by the server as mock.
- Session records are persisted by the Python server's SQLite database.
- AI triage calls the server's configured worker dispatch and presents returned results as advice, not an executed repair.
- Optional integrations (local model, Supabase/PostgreSQL, ADB/Fastboot) are not falsely represented as connected unless they are actually configured or checked.
- Physical jig controls, flashing, wiping, activation-lock/FRP bypass, and other device-changing operations remain disabled.

## Important release limitation

This commit adds the interface and a convenience launcher; it does not itself prove that the complete repository passes tests, that every referenced Python package/module is present on the target branch, or that hardware and Windows installer operations work. Run the repository test suite and verify the dashboard on a clean Windows 11 x64 machine before using it with customer data. The local service binds to loopback and is not a multi-user or public internet deployment.
