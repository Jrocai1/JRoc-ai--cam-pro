# J-ROC AI Universal Repair PRO — Free Build and Release Plan

## Purpose

Build and verify the existing repository with free development tooling, targeting Windows 11 x64. This plan does not mark unimplemented device operations as complete.

## Current repository findings (2026-10-22)

- The default branch is `main`; this work is isolated on `build/free-windows-release-pipeline`.
- The root contains a React/Vite application (`package.json`, `index.html`, `main.jsx`, `App.jsx`) and Windows technician utilities in `tools/windows-repair/`.
- Existing GitHub Actions workflows test portions of the technician-tool code.
- `J-Roc-AI-Mobile-Repair.iss` defines an Inno Setup installer, and `requirements-dev.txt` lists PyInstaller.
- **Desktop packaging is not yet verified.** `main.py` imports `jroc_mobile` and `jroc_samsung`; those package directories were not present in the repository tree inspected on this date. The installer references a staged `dist/J-Roc AI Mobile Repair/` directory. The packaging pipeline must not publish a setup EXE until the required modules are restored/implemented and the staged executable can be built and smoke-tested.
- The README refers to a `web/` directory and the Supabase README, but those paths were not present in the repository tree inspected. Documentation and actual repository layout must be reconciled.
- The Inno Setup script version and root npm package version do not match; choose one release version before publishing.

## Phase gates

### Gate 1 — Continuous integration

- Build the root Vite app on a free GitHub-hosted Linux runner.
- Run existing Windows utility tests on a Windows runner.
- Upload the web build as a short-retention CI artifact, not as a production release.
- Review failures; a green build is evidence only for the steps actually run.

### Gate 2 — Restore a complete desktop source tree

- Confirm whether `jroc_mobile/`, `jroc_samsung/` and `tests/` were accidentally omitted, renamed, or stored on another branch.
- Restore the authoritative code rather than creating empty placeholder modules.
- Run `python -m unittest discover -s tests -v` after the real test suite exists.
- Confirm the desktop app starts as a standard user and persists SQLite data under the current user's local application-data directory.

### Gate 3 — Windows x64 installer

- Build the Python desktop executable with PyInstaller from a Windows runner.
- Stage the executable and its runtime dependencies at the exact path expected by `J-Roc-AI-Mobile-Repair.iss`.
- Install Inno Setup on the runner and compile the installer.
- Smoke-test install, launch, basic data persistence, and uninstall/upgrade behavior.
- Generate SHA-256 checksums and upload the setup EXE as a GitHub Actions artifact.
- Do not publish a GitHub Release until this gate passes.

### Gate 4 — Cloud and real-device acceptance

- Configure Supabase secrets privately; test RLS and authenticated access using separate test accounts.
- Keep Stripe in test mode until webhook signatures, duplicate events and failure cases are verified.
- Confirm supplier API documentation, credentials, idempotency and sandbox tests before enabling real orders.
- Test ADB/Fastboot diagnostics on actual supported devices.
- Keep firmware writing disabled until model-specific safeguards and hardware tests pass.

## Zero-cost operating rules

- Use GitHub Free, Codespaces within quota, GitHub Actions within quota, Python, Node.js and Inno Setup.
- Do not enable paid overages. GitHub-hosted runner and artifact quotas can limit builds.
- Do not put secrets in source code, `VITE_*` variables, logs, artifacts or pull requests.
- A free-tier target does not make Stripe transaction fees, suppliers, a custom domain or future production usage free.

## Release evidence required

A feature is complete only when its source exists, automated tests pass, relevant CI is green, limitations are documented, and manual acceptance evidence exists for operations that depend on Windows, cloud services or physical devices.
