# J-Roc AI Mobile Repair

**Apple + Samsung only · Phones, tablets and laptops · Windows desktop + React web frontend**

J-Roc AI Mobile Repair is a repair intake and shop-operations workspace. The Windows desktop app stores core shop records locally in SQLite. The React/Vite web frontend provides responsive customer-facing repair intake, private request tracking and carrier-unlock checkout integration through Supabase Edge Functions.

## Supported device scope

Only these device families are accepted by the current intake and service APIs:

- **Apple:** iPhone, iPad and MacBook.
- **Samsung:** Galaxy phones, Galaxy Tab tablets and Galaxy Book laptops.
- **Device types:** Phone, Tablet and Laptop only.

Carrier-unlock checkout is restricted to eligible phones and cellular tablets because it requires a 15-digit numeric IMEI. Laptops can use repair/diagnostics intake, not IMEI-based carrier unlocking. Other manufacturers and device types are rejected by the backend and desktop data layer.

## Windows desktop app

The current Windows desktop baseline includes:
- Customer, device and repair-ticket records with generated job numbers.
- Intake notes, priority, technician assignment, diagnosis findings and repair logs.
- Parts and inventory quantities, stock adjustments and job-linked part consumption.
- Estimates, approval status, invoices, partial/full payment records and QC checks.
- Basic warranty/service cases, notification drafts, owner summary, CSV export, local audit history, SQLite backup and integrity check.
- Read-only ADB/Fastboot/Windows USB diagnostics and firmware package inspection.
- Firmware writes remain disabled; no flashing or security bypass is claimed.

Run on Windows 11 x64 with Python 3.11+:

    py -3 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    .\.venv\Scripts\python.exe main.py

Tests:

    .\.venv\Scripts\python.exe -m compileall -q main.py jroc_mobile jroc_samsung tests
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v

Local SQLite data is stored in `%LOCALAPPDATA%\JROC\MobileRepair\mobile_repair.sqlite3`.

## React frontend

Frontend source: [web/](web/). It includes:
- Responsive J-Roc AI Mobile Repair service desk UI.
- Strict Apple/Samsung + phone/tablet/laptop scope.
- Carrier-unlock form with 15-digit IMEI validation and Stripe Elements.
- Repair-intake form for phones, tablets and laptops.
- Private request tracking requiring a reference plus high-entropy token.
- Supabase client with browser-safe public values only.
- Tailwind CSS styling and CI validation.

Setup instructions: [web/README.md](web/README.md).

## Supabase, Stripe and supplier polling

The `supabase/` folder includes:
- SQL migration with RLS-enabled private `orders` and `repair_requests` tables.
- Edge Functions for creating unlock/repair requests, signature-verified Stripe webhook processing, private token-based lookup and supplier status polling.
- A pg_cron schedule invoking the poll function every 15 minutes through pg_net/Vault.
- Configuration and secrets instructions.

Read the deployment guide: [supabase/README.md](supabase/README.md).

**Security design:** browser clients do not insert/select directly from the private request tables. Public requests are validated in Edge Functions. Stripe and supplier secrets stay server-side. Customer status lookups require a reference and a separate secret token; completed unlock results are only returned after token verification.

## Release status and limitations

The React UI and backend source are committed, and GitHub Actions is configured to compile/type-check the frontend and Edge Functions. A web build passing CI does not mean that a Supabase project, Stripe account or wholesaler credentials have been configured. The wholesaler URLs in example files are placeholders; real processing requires a provider contract and sandbox tests.

A SHA-256 checksum is not proof of firmware origin or compatibility. Firmware writes are disabled. This code does not bypass Activation Lock, FRP/account verification, PIN/password controls or other security mechanisms. Supabase usage limits and Stripe/supplier transaction charges may apply; free-tier infrastructure does not mean all transactions are cost-free.

## Documentation

- [React frontend guide](web/README.md)
- [Supabase / Stripe setup guide](supabase/README.md)
- [Operator Guide](docs/OPERATOR_GUIDE.md)
- [Mobile Repair Feature Matrix](docs/MOBILE_REPAIR_FEATURE_MATRIX.md)
- [Roadmap](docs/ROADMAP.md)
- [Testing Guide](docs/TESTING.md)

Repository: https://github.com/Jrocai1/Samsungrepair
