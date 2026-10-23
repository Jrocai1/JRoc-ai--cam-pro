# Builder React Interface Audit and CAM PRO Integration

## Purpose

This document records what the checked-in React source actually does, separates working local behavior from configuration-dependent integrations, and describes the safe path to a Windows 11 x64 bench release. It does not claim physical-hardware or clean-PC installation tests have been performed.

## React interface: source-based functionality review

| Area | Evidence in source | Current classification |
|---|---|---|
| Main navigation and overview | `App.jsx` | Implemented client-side UI; navigation and request launch actions change React state. Dashboard metrics include configured/not-configured states, not verified service health. |
| New repair request | `UnlockForm.jsx`, `supabaseClient.js` | Form validation is local. Submission calls the `create-repair-request` Supabase Edge Function. It is operational only when the Supabase project, deployed function, schema, secrets, and access policies are configured and tested. |
| Carrier service and checkout | `UnlockForm.jsx` | Calls `create-unlock-order` and uses Stripe Elements. Real checkout depends on valid Stripe/Supabase configuration and a verified webhook/supplier workflow. Not a device unlock command. |
| Track request | `TrackRequest.jsx` | Calls `lookup-service-request` using a reference and private lookup token. Requires the deployed function and real stored order data. |
| Device tools page | `App.jsx` | Informational cards only; the original page does not itself query the local Python bench API. |
| Admin Recovery Workbench | `AdminRecoveryWorkbench.jsx` | Interactive checklist and JSON export work in the browser. Events are held in component state; the component explicitly does not provide a server-side audit log or execute device commands. |
| Recovery / guide pages | `App.jsx` | UI workflow content. Their presence alone does not demonstrate physical device repair or firmware execution. |
| Local Bench Console | `BenchDashboard.jsx` (added on the production-foundation branch) | Calls the local Python API for status, read-only inventory, diagnostics, persistent SQLite sessions, status updates, and audit events. Requires the local server to be running. |
| Python bench backend | `dashboard_server.py` | Local-only HTTP API; SQLite session persistence; read-only inventory and advisory AI triage. Device-changing operations are not exposed. |

## React-to-Python integration

The React app's **Local Bench Console** uses:

- `VITE_CAM_API_BASE_URL`, defaulting to `http://127.0.0.1:8787`.
- `GET /api/status` to distinguish the real local service from a simulation.
- `GET /api/devices` and `GET /api/diagnostics` for read-only discovery and diagnostic metadata.
- `GET/POST /api/sessions` to read/create records in the local SQLite database.
- `PATCH /api/sessions/{id}` to update an allowed workflow status.
- `GET /api/audit` to show persistent events for session creation and status changes.

The API accepts browser origins on localhost Vite development/preview ports by default. Add any other exact frontend origin to the comma-separated `CAM_ALLOWED_ORIGINS` environment variable. Do not use a wildcard origin. Keep the Python service bound to loopback unless a separately reviewed authentication and network-security design is implemented.

A cloud-hosted Builder/React site is not automatically able to control the PC's local API. Browser local-network restrictions, origin allowlisting, and the user’s local server must all permit the connection. For reliable bench use, run the frontend on the same PC and use an allowed localhost origin. Do not put a database service-role key or device-control credentials in browser code.

## Windows USB/COM and diagnostic behavior

- `backend_bus/port_listener.py` queries Windows Plug-and-Play USB metadata and uses pySerial for serial/COM port enumeration when installed.
- `device_tools.py` checks ADB and Fastboot only when their executables are installed and available on PATH; it also reports USB PnP metadata on Windows.
- The results are read-only metadata. A missing result can mean that a driver, cable, USB mode, authorization, or platform tool is unavailable; it does not prove the hardware is defective.
- Simulation mode returns an explicitly labelled synthetic device. A mock record must never be presented as a physical detection.
- No firmware flashing, unlocking, erasing, or power-relay action is exposed by these endpoints.

## Test and release gates

1. Run `python -m unittest discover -s tests -v` on Windows 11 x64.
2. Run `npm test` and `npm run build` from the repository root.
3. Start the local API and verify status, session creation, status update, audit trail, and diagnostics in the React Local Bench Console.
4. Test USB and COM discovery on the actual Windows bench with known, authorized devices; compare reported VID/PID/COM metadata with Windows Device Manager.
5. Test ADB and Fastboot with a supported test device and official platform tools installed. Record the exact device model, state, driver version, and command output.
6. Install on a clean Windows 11 x64 machine/account with Python 3.12 x64 and no pre-existing virtual environment. Test the launcher, browser startup, shutdown/restart, and SQLite persistence.
7. Build and test a signed/unsigned installer only after its packaging workflow is explicitly selected. The current `Install-And-Run-CAM-PRO.bat` is a bootstrap launcher, not a standalone installer.
8. Keep the release marked **not production-ready** until the above local/hardware/installation checks are recorded as passed.

## Evidence limits

GitHub Actions can verify source-level tests and build steps in its own runners. It cannot verify the user’s USB cables, physical devices, locally installed drivers, or a clean installation on the user’s own PC. No such physical test is claimed by this audit.
