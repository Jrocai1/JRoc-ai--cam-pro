# J-Roc AI Mobile Repair — React Frontend

Vite + React + Tailwind CSS frontend for the Apple/Samsung-only service desk.

## Supported product scope

- Manufacturers: **Apple and Samsung only**.
- Device types: **Phone, Tablet, Laptop**.
- Service request: repair and diagnostics for all three device categories.
- Carrier unlock checkout: eligible phones and cellular tablets only. Laptops do not use IMEI-based carrier unlocking.
- IMEI inputs accept exactly 15 numeric digits; repair intake allows an optional IMEI for a phone/tablet.
- The UI never requests an Apple Account password, Google password, screen-lock code or other account credentials.

## Run locally

Use Node.js 20 or later. In PowerShell:

    cd web
    Copy-Item .env.example .env.local
    npm install
    npm run dev

Open the local URL printed by Vite. The app can render in **Preview mode** without cloud keys, but it will not pretend that a request was saved. Add real configuration values in `.env.local` to submit requests.

## Browser environment variables

Set these in `web/.env.local`:

    VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
    VITE_SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_OR_ANON_KEY
    VITE_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY

Only public values belong in Vite environment variables. Never put a Supabase `service_role`/secret key, Stripe secret key, Stripe webhook secret, wholesaler API key, or cron secret in `VITE_*` variables.

## Quality checks

    npm test
    npm run build

A production preview can be opened with `npm run preview` after building.

## Security model

The web client calls Supabase Edge Functions; it does not read or write the `orders` and `repair_requests` tables directly. SQL enables RLS and revokes anonymous/authenticated table grants. The Edge Functions validate the permitted brands and device types again on the server. Unlock checkout uses Stripe Payment Element. Service tracking requires both a public reference and a separate high-entropy token; only a completed unlock request can return its supplier result/code.

## Connected backend needed

See [Supabase setup](../supabase/README.md). A real wholesaler's API URL, authentication method, idempotency behavior and response schema must be confirmed before production. The example wholesaler URLs in `supabase/functions/.env.example` are placeholders, not live services.

## Low-fixed-cost deployment and supplier integration

See [Zero-Cost Hosting and Supplier API Integration](docs/ZERO_COST_HOSTING_AND_SUPPLIER_API.md) for the Supabase/Stripe hosting plan, supplier API verification requirements, security gates, and production checklist. Supplier credentials and endpoints must be configured privately after confirming the provider's official API contract.

## First-party API

See [J-ROC AI API v1](docs/JROC_AI_API_V1.md) for the versioned API foundation, health and authenticated identity endpoints, request IDs, private metadata-only API tracking, deployment steps, and security gates. This initial release does not enable supplier dispatch or unlocking operations.
