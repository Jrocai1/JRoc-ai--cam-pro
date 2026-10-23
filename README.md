# J-Roc AI CAM PRO

J-Roc AI CAM PRO is the foundation for a Windows 11 64-bit repair-bench application with read-only device discovery, controlled repair-tool integrations, local AI orchestration, and auditable bench workflows.

> **Current status:** active foundation implementation. Read-only discovery, advisory AI triage, a live worker catalog, optional PostgreSQL-backed bench sessions, and CI checks are present. The database schema still must be applied to the target database, database-backed routes need a live integration test, and physical repair hardware and Windows installer validation remain outstanding. This is not yet a finished repair product.

## Current repository contents

- `backend_bus/port_listener.py` — read-only USB/COM inventory with mock mode.
- `backend_bus/firmware_vault.py` — bounded, read-only SHA-256 integrity checking for local firmware files and JSON manifests. A matching hash does not independently prove vendor authenticity; use a trusted manifest.
- `backend_bus/tool_wrappers/android_tools.py` — fixed-argument, read-only ADB/Fastboot wrappers with `shell=False`, timeouts, and output caps.
- `backend_bus/policy_gate.py` — fail-closed policy decisions; it does not execute device operations.
- `backend_bus/model_router.py` — explicit-target local Ollama chat routing with timeout limits and fallback; remote endpoints are rejected by default.
- `core_swarm/agent_registry.py`, `core_swarm/orchestrator.py`, and `core_swarm/worker_swarm.py` — typed worker roles and advisory task dispatch.
- `core_swarm/token_rotator.py` — environment-based provider credential selection with provider-wide rate-limit cooldowns. This is not yet wired into live model requests and does not bypass provider quotas.
- `config/security_vault.py` — optional AES-256-GCM authenticated encryption for JSON configuration mappings; requires `requirements-security.txt` and a locally provisioned `JROC_CAM_VAULT_KEY`.
- `database/core_schema.sql` and `database/migrations/001_core_automation.sql` — namespaced PostgreSQL/Supabase schema for sessions, agent registry, swarm tasks, feature-pack usage, and sanitization evidence.
- `database/db_client.py` — optional async PostgreSQL pool client; install `requirements-postgres.txt` only when direct PostgreSQL connectivity is configured.
- `matrix_controls/crypto_sanitizer.py` — SHA-256 evidence-file hashing and verification, not a physical storage wiper.
- `matrix_controls/power_jig_controller.py` — simulation-only interface; physical relay/power operations are disabled.
- `tests/` — automated unit tests, including firmware integrity and optional encrypted-vault tests.
- `.github/workflows/python-tests.yml` — Windows-based Python unit-test workflow.

## Quick start (Windows 11 64-bit)

Install Python 3.12 or newer, then open PowerShell in the repository folder:

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m backend_bus.port_listener --mock --pretty
```

To run optional AES-GCM vault tests and use the encrypted configuration vault, install:

```powershell
python -m pip install -r requirements-security.txt
python -c "from config.security_vault import generate_master_key; print(generate_master_key())"
```

Store the generated key securely as `JROC_CAM_VAULT_KEY` in your local environment. Do not commit the key, a populated `.env`, or `vault.enc` containing real secrets. Losing the key means the encrypted vault cannot be decrypted. Prefer a dedicated OS credential manager for long-term production secret storage.

For read-only host discovery, run:

```powershell
python -m backend_bus.port_listener --pretty
```

The discovery command reports metadata only. It does not flash, unlock, erase, or modify connected devices.

## React dashboard + local Python bench API

The existing React interface remains in place. The **Local Bench Console** adds a local-first integration to the Python bench API without replacing the existing request, tracking, or recovery screens.

Run the Python API in one PowerShell window:

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt
.\\.venv\\Scripts\\python.exe dashboard_server.py
```

Run the React app from the repository root in a second PowerShell window:

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

Open the localhost URL printed by Vite, then select **Local Bench Console**. The default local API URL is `http://127.0.0.1:8787`; override it with `VITE_CAM_API_BASE_URL` only when necessary. The local server allows the standard localhost Vite origins. For another exact frontend origin, set `CAM_ALLOWED_ORIGINS` or `JROC_CAM_CORS_ORIGINS` on the server process as a comma-separated list. Never configure a wildcard origin.

The console can read USB/COM metadata, run read-only host/ADB/Fastboot checks when the relevant tools are available, create and update local SQLite bench sessions, and display session audit events. The audit events record local session creation and status changes; they are not a tamper-proof or authenticated compliance ledger. The local SQLite data is not automatically synced to Supabase.

See [Builder React Interface Audit and CAM PRO Integration](BUILDER_REACT_AUDIT.md) for the source-based component review, API mapping, and release gates.

## Database deployment

Review `database/core_schema.sql` before applying it to a Supabase project. Use a migration workflow and a least-privilege database role. The schema intentionally does not enable broad public access or add permissive Row Level Security (RLS) policies. Before exposing tables through Supabase APIs, define and test access policies for the application's actual authentication and authorization model.

The current schema already contains a richer `core_automation` model than the minimal example schema in early planning notes. Do not replace it with a reduced schema merely to match a file-tree sketch. Add new business tables through versioned migrations only when the product workflow and tenant/access model are defined.

## Safety and integration boundaries

- Keep device discovery and firmware inspection read-only by default.
- Run only vendor-authorized tools and documented device modes.
- Require explicit operator confirmation and preflight checks for any future state-changing action.
- Low-level BROM/EDL exploit injection, boot-chain hijacking, and unauthorized access workflows are intentionally excluded. A future BROM/EDL module must be a documented, authorized, safety-gated diagnostic/preflight adapter—not an exploit bridge.
- USB/IP forwarding requires compatible host support, drivers, network controls, and explicit device-sharing authorization; it is not provided by a Python listener alone.
- Never store raw customer identifiers or device serial numbers unnecessarily. Prefer access-controlled records and hashed or otherwise minimized references where appropriate.
- A SHA-256 digest proves only byte-level integrity relative to a known digest. It does not prove secure erasure, firmware authenticity, or NIST SP 800-88 compliance by itself.

## Local dashboard

Start the local dashboard and SQLite bench-session database:

```powershell
python dashboard_server.py --mock
```

Open **http://127.0.0.1:8787** in your browser. Mock mode shows a synthetic USB device and does not scan hardware. To use read-only host discovery instead, stop the server with Ctrl+C and run `python dashboard_server.py`.

The dashboard currently supports local service status, read-only USB/COM inventory, bench intake sessions, SQLite persistence, and an AI triage panel. It binds to `127.0.0.1`; it is not a remotely accessible web service. Session fields are local-only and are not synchronized to Supabase. Triage output requires technician review and does not run device commands.

## Optional PostgreSQL setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL` to a private PostgreSQL connection string if you want direct database connectivity.
2. Install the optional driver: `python -m pip install -r requirements-postgres.txt`.
3. Review and back up the target database, then apply `database/migrations/001_core_automation.sql` using your trusted migration workflow.
4. Configure project-specific authentication and row-level security policies before storing real customer/device data. The migration does not grant anonymous access.

Do not commit `.env` or database credentials. Supabase service-role credentials must never be embedded in browser code.

## Model and credential policy

`config/model_endpoints.json` keeps model targets disabled by default. Remote model endpoints require explicit configuration and review of diagnostic-data handling. `core_swarm/token_rotator.py` selects only configured credentials; if a provider is rate-limited, its provider ID is cooled down as one quota domain. It does not cycle through keys to evade limits, guarantee that models are free, or automatically call provider APIs. See `docs/PROVIDER_CREDENTIAL_POLICY.md`.

The requested sub-50 ms failover is not guaranteed for remote or local model calls: a timeout can exceed that budget. Any hard service-level objective requires measured inference/health-check behavior and a separately designed cached response path.

## Tests

Run the suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

Vault encryption tests are skipped if the optional `cryptography` dependency is not installed. Install `requirements-security.txt` to exercise AES-GCM round-trip, tamper detection, and wrong-key rejection.

## Release principles and remaining work

- Prefer open-source components and free tiers where practical; verify current provider terms and quotas before enabling any model.
- Keep state-changing device operations behind documented vendor tools, explicit technician confirmation, and audited preflight checks.
- Validate tests on Windows 11 x64 and a controlled physical repair bench before claiming hardware compatibility.
- Supabase authentication/RLS, full USB/IP support, live provider-adapter integration, physical jig drivers, verified sanitization workflows, and a Windows installer remain separate work items.
- Report tested functionality separately from planned functionality; this repository is not yet a finished production repair product.

## Optional master API gateway

The optional FastAPI master gateway provides real read-only device inventory, advisory AI triage, and safety-policy preflight endpoints. It is separate from the standard-library local dashboard and binds to loopback by default.

```powershell
python -m pip install -r requirements-api.txt
python -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8000
```

See [`docs/UPDATED_BLUEPRINT_IMPLEMENTATION_STATUS.md`](docs/UPDATED_BLUEPRINT_IMPLEMENTATION_STATUS.md) for the current v1.0–v6.0 roadmap, API routes, implementation boundaries, and release gates. The master API does not flash devices, erase storage, deploy OTA updates, provision eSIMs, clear MDM/activation locks, or control robotic hardware.


## Updated multi-stage blueprint and runnable API

The updated architecture adds a safe FastAPI gateway, a React/Vite dashboard, compatibility modules for future OEM/Apple/eSIM/OTA/Academy/hardware integrations, and local container configuration. Some modules intentionally report **disabled or not implemented** rather than simulating a successful device operation. Review [the implementation stage ledger](docs/UPDATED_BLUEPRINT_IMPLEMENTATION_STATUS.md) before using or deploying features.

### Windows 11 x64 — local development

PowerShell terminal 1 (API):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8000
```

PowerShell terminal 2 (dashboard):

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL printed by the command. The dashboard calls the API through the development proxy. To run tests from the repository root, use `python -m unittest discover -s tests -v`.

### Docker

Copy `.env.example` to `.env` before starting Compose; the Compose service is published only on `127.0.0.1:8000` by default:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The container is not a USB pass-through service and does not provide direct access to Windows host device drivers. For physical bench use, run the local API directly on Windows. Do not deploy the unauthenticated local gateway publicly. The server API-key helper is a building block for protected server routes, not a replacement for tenant authentication or database RLS.

### Implemented boundaries

- Read-only host inventory and advisory diagnostic triage are real API operations; synthetic inventory is explicitly marked mock.
- Firmware, BROM/EDL, Apple, eSIM, OTA, billing entitlement, Academy credit, robotic, and post-quantum modules do not claim unavailable capabilities. Destructive, exploit, activation-lock bypass, and device-wipe operations are not implemented.
- PostgreSQL schema files are not automatically applied by the API. Tenant ownership and row-level security must be reviewed and tested in the target database before multi-tenant use.
- Hash verification proves equality to a supplied digest, not source authenticity by itself. No file-hash routine is a NIST SP 800-88 device sanitization certificate.

## Foundational API additions

The API now registers two additional route groups:

- `GET /v1/agents` — read-only catalog of the five registered worker roles. Listing a role does not enable a model or execute a device operation.
- `GET /v1/bench/sessions/database-status` — read-only database readiness probe.
- `GET /v1/bench/sessions?limit=50&status=open` — lists persisted bench-session metadata.
- `POST /v1/bench/sessions` — creates a session record only; it does not communicate with or modify a connected device.

These session endpoints require `DATABASE_URL` or `SUPABASE_DB_URL`, the optional `asyncpg` dependency, and the reviewed `core_automation` schema to be applied. Install the optional driver with:

```powershell
python -m pip install -r requirements-postgres.txt
```

Apply the reviewed migration through your database's approved migration process; do not paste database credentials into source files or commit them. A missing database produces an explicit unavailable response rather than silently switching to a different database. The session API accepts only a SHA-256 serial hash, not a clear-text serial number. Before public deployment, implement and verify technician authentication, tenant scoping, and database RLS policies.

Run the unit tests after pulling these changes:

```powershell
python -m unittest discover -s tests -v
```


## J-Roc AI CAM PRO dashboard and automation

The React dashboard is in `frontend/`. It calls the local API for health, read-only USB/COM inventory, advisory triage, and the registered AI worker catalog. The worker cards are loaded from `GET /v1/agents`; they are not hard-coded sample workers.

The local bench daemon is `operations/runtime/local_bench_daemon.py`. It only discovers device metadata and logs a local inventory report. **Cloud synchronization is intentionally disabled** until a separate authenticated, privacy-reviewed telemetry protocol is implemented. Do not expose the local API directly to the public internet.

The GitHub Actions workflow `.github/workflows/ci_cd_pipeline.yml` runs Python unit tests, builds the frontend, and builds the Docker image without pushing it to a registry. A successful container build does not prove that the image works with physical USB devices or that a live PostgreSQL/Supabase project is configured.

To run the dashboard locally, start the API and frontend in separate PowerShell windows from the repository root:

```powershell
python -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

The frontend currently expects API routes at the same origin. Use the repository's configured local proxy or a same-origin deployment when running the Vite development server; do not enable wildcard CORS as a workaround.


## Stripe webhook intake and agent task persistence

The master API registers `POST /webhooks/stripe`. The endpoint requires a real `STRIPE_WEBHOOK_SECRET`, verifies the Stripe signature against the raw request body, and records the event ID/type, livemode flag, payload SHA-256, and intake status in `core_automation.stripe_webhook_events`. Duplicate event IDs are handled idempotently. Raw payment payloads are not stored by this ledger.

Before enabling Stripe delivery:

1. Apply the reviewed `database/core_schema.sql` (or the matching migration) to the configured PostgreSQL database.
2. Install the API dependencies with `python -m pip install -r requirements.txt -r requirements-postgres.txt`.
3. Configure `STRIPE_WEBHOOK_SECRET` and `DATABASE_URL` in the runtime environment; never commit secrets.
4. Configure Stripe to deliver events to the HTTPS endpoint `/webhooks/stripe`.
5. Confirm the GitHub Actions test results and send Stripe test-mode events before production.

A verified webhook is **not** itself a license upgrade. The receiver deliberately does not grant entitlements from customer email or event contents. Account/customer mapping, subscription-state reconciliation, and an entitlement ledger with authorization checks must be implemented and tested before paid features are unlocked. If persistence is unavailable, the endpoint returns HTTP 503 so Stripe can retry.

The async `operations/runtime/agent_control_plane.py` writes task lifecycle records to `core_automation.ai_swarm_tasks`. Its `dispatch_task` and `complete_task` methods are asynchronous and require a configured PostgreSQL connection. Tasks are audit records; the control plane does not by itself execute an AI model or a device command.



### Bench dashboard and privacy erasure endpoint

The React command dashboard calls FastAPI for health, host inventory, advisory triage, the worker catalog, and PostgreSQL-backed bench sessions. Synthetic inventory is opt-in and labelled; it never represents a physical device. The dashboard does not issue flash, erase, unlock, FRP-clear, or relay commands. The local bench daemon remains a separate process and currently reports inventory locally only.

The privacy route is `POST /v1/privacy/purge-device-data`. It is disabled until `JROC_PRIVACY_ADMIN_TOKEN` is configured. Supply a SHA-256 device-serial hash in the JSON body and the administrator token in `X-Privacy-Admin-Token`. The default request previews affected rows; actual deletion requires `"confirm_purge": true`. It deletes matching bench sessions and linked sanitization/swarm-task records in one PostgreSQL statement and does not touch Stripe billing records. Never submit raw serial numbers.

This administrator-only utility is not a complete GDPR/CCPA compliance program. Before multi-tenant or public deployment, add identity-provider authentication, tenant-scoped authorization, request verification, documented retention rules, and an independently retained audit trail. Automated tests mock the database; live erasure still requires controlled staging validation and backup/restore testing.
