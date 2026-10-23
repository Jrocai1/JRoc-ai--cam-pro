# Testing — J-Roc AI Mobile Repair

Run from PowerShell on Windows or a Python development machine:

    python -m compileall -q main.py jroc_mobile jroc_samsung tests
    python -m unittest discover -s tests -v

Automated coverage includes customer/device/job linkage, job status updates, diagnostic and repair logs, estimates and invoice approvals, partial/full payments, inventory adjustment/consumption/low-stock reporting, QC checks, audit entries, settings, SQLite backup/integrity and read-only firmware package inspection.

## Windows 11 x64 acceptance
- Compile and run the application as a standard user.
- Create customer/device/job records and verify data persists after restart.
- Change job status and assign technician.
- Create/approve an estimate and record a partial payment plus a balance settlement.
- Consume stock against a repair job and confirm inventory history.
- Record QC checks, export jobs to CSV, back up the database and check integrity.
- Run diagnostics with no device and with a Samsung/Android device in normal Android mode.
- Inspect a known official firmware package and verify the displayed SHA-256 independently.
- Confirm the UI clearly states firmware writing is disabled.
- Install and uninstall from the setup EXE using the CI smoke test; manually validate the installer on a clean Windows 11 x64 machine.
- Test actual devices and supported peripherals individually before advertising device-specific functions.

Automated tests do not validate every hardware adapter, real firmware compatibility, external messaging, payment processors, or multi-user security. Do not claim those capabilities without relevant implementation and evidence.
