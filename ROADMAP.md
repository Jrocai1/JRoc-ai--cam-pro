# J-Roc AI Mobile Repair Roadmap

## Phase 1 — supported service scope and core operations
- [x] Product scope restricted to Apple and Samsung.
- [x] Device type intake restricted to Phone, Tablet and Laptop.
- [x] SQLite schema for customers, devices, jobs, technicians, diagnostics and repair logs.
- [x] Jobs, priorities, statuses and technician assignment.
- [x] Inventory, stock adjustments, history and job-linked part consumption.
- [x] Estimates, approvals, invoices, partial/full payment records, QC and audit.
- [x] Owner dashboard, CSV export, database backup and integrity check.
- [x] Responsive React frontend with Apple/Samsung service-request flow.
- [x] Shared client-side brand/type/IMEI validation and Node unit tests.
- [x] Supabase migrations and private Edge Function request paths.
- [x] Stripe Elements PaymentIntent flow and signed payment webhook source.
- [x] Private reference-plus-token lookup.
- [x] pg_cron/pg_net/Vault SQL schedule for 15-minute polling.
- [ ] Verify latest React and Edge Function CI workflow passes.
- [ ] Deploy to a real Supabase project with secrets configured.
- [ ] Verify Stripe test-mode checkout and duplicate-webhook behavior.
- [ ] Validate the real supplier sandbox contract, idempotency semantics and failure handling.
- [ ] Manual acceptance on a clean Windows 11 x64 machine.

## Phase 2 — production shop workflow and security
- [ ] Enforced Owner/Manager/Technician/Front Desk/Viewer accounts and permissions.
- [ ] Electronic authorization/waiver capture and consent history.
- [ ] Better device/customer search, update and archive workflows.
- [ ] Multiple estimate lines in the desktop GUI, estimate revisions and printable invoices.
- [ ] Full warranty/RMA, returns and refund/void flow.
- [ ] Real SMS/email notification integration with delivery status and opt-out records.
- [ ] Supplier purchase orders, goods receiving and replenishment.
- [ ] Backups off-device, restore drills and database migration checks.

## Phase 3 — supported Apple and Samsung diagnostics
- [ ] Publish tested model and operating-state matrix for each supported iPhone/iPad/MacBook and Samsung Galaxy/Galaxy Tab/Galaxy Book device.
- [ ] Add device-specific diagnostic adapters only where supported APIs/protocols are documented and licensed.
- [ ] Document supported USB drivers and ADB/Fastboot limitations per device state.
- [ ] Add model-aware preflight and explicit data-loss warnings for supported manufacturer recovery operations.
- [ ] If a flashing backend is pursued, require firmware provenance, exact model/region/bootloader checks, recovery safeguards and hardware-in-the-loop testing before enabling writes.
- [ ] Keep all device-changing operations disabled until the relevant model-specific acceptance tests pass.

## Phase 4 — owner reporting and automation
- [ ] Workflow rules for status changes, customer reminders, QC exceptions and low stock.
- [ ] Revenue/cost/profit summaries, technician workload and turnaround reporting.
- [ ] Optional J-ROC AI model gateway with explicit owner-selected model allow-list.
- [ ] AI repair documentation/decision support with evidence tracking and confidence limits.

## Explicit out-of-scope boundary

The supported hardware list will remain limited to **Apple and Samsung phones, tablets and laptops**. This project will not add other phone manufacturers, desktops/PCs, game consoles, wearables, consumer electronics or unrelated device categories unless the product scope is explicitly changed later.

## Release gates

Do not mark a feature complete based on a screen or schema alone. Require automated tests, a passing relevant CI build, documented limitations, manual acceptance evidence, secure credentials handling and vendor sandbox/hardware tests where applicable. A free-tier deployment is subject to platform quotas; Stripe fees and supplier charges may still apply.
