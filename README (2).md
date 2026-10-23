# Supabase backend setup — J-Roc AI Mobile Repair

This folder contains the SQL migration, Edge Functions, function configuration and the 15-minute supplier-poll schedule for the Apple/Samsung service desk.

## 1. Create a Supabase project

Create or select a project you control. The architecture uses PostgreSQL, Edge Functions, Vault, pg_cron and pg_net. Usage is subject to the current Supabase plan quotas. Stripe processing fees and any wholesaler charges are separate costs; a free database tier does not make every transaction or supplier service free.

## 2. Apply the schema

Run the migration `migrations/20261021090000_mobile_repair_service_orders.sql` using the Supabase SQL Editor or your normal migration workflow. It creates:

- `public.orders`: private carrier unlock orders; IMEI is exactly 15 digits.
- `public.repair_requests`: private repair intake for Apple/Samsung phones, tablets and laptops.
- RLS enabled with **no anonymous table policy** and no direct table grants for `anon` or `authenticated`; trusted Edge Functions use the server-side key.

This is intentionally more secure than direct anonymous inserts into an exposed table. All public create/lookup requests go through validated Edge Functions.

## 3. Configure Edge Function secrets

Copy `functions/.env.example` to `functions/.env` for local testing, or set the same values through Supabase Edge Function Secrets. Keep `functions/.env` out of Git:

    STRIPE_SECRET_KEY=sk_test_...
    STRIPE_WEBHOOK_SECRET=whsec_...
    UNLOCK_PRICE_CENTS=4999
    UNLOCK_CURRENCY=usd
    WHOLESALER_ORDER_URL=https://YOUR_REAL_PROVIDER_HOST/api/orders
    WHOLESALER_STATUS_URL_TEMPLATE=https://YOUR_REAL_PROVIDER_HOST/api/orders/{supplier_order_id}
    WHOLESALER_API_KEY=...
    UNLOCK_POLL_SECRET=...

Choose the unlock price intentionally. The example 4999 is only a configuration example ($49.99 when using USD), not a recommendation or hard-coded charge. Do not use test Stripe keys for live production orders. Use a long random `UNLOCK_POLL_SECRET` and use the exact same value for the Edge Function and the Vault secret called `jroc_unlock_poll_secret`.

Deploy these functions from the repository root with the Supabase CLI:

    supabase functions deploy create-unlock-order
    supabase functions deploy create-repair-request
    supabase functions deploy lookup-service-request
    supabase functions deploy stripe-webhook
    supabase functions deploy poll-unlock-orders

The relevant `verify_jwt = false` values are in `config.toml`. They are deliberate: public intake and token-based lookup are unauthenticated endpoints, and the webhook validates Stripe's signature while cron polling validates `x-cron-secret`. Do not remove their application-level validations.

## 4. Configure Stripe

1. In Stripe, use test mode first.
2. Set `STRIPE_SECRET_KEY` as an Edge Function secret.
3. Add a webhook endpoint: `https://YOUR_PROJECT_REF.supabase.co/functions/v1/stripe-webhook`.
4. Subscribe to `payment_intent.succeeded`.
5. Copy the Stripe webhook signing secret into `STRIPE_WEBHOOK_SECRET`.
6. Put only the **publishable** key into `web/.env.local` as `VITE_STRIPE_PUBLISHABLE_KEY`.
7. Test a payment, verify the signed webhook is accepted and confirm the order transitions only after Stripe's verified success event.

The Edge Function creates PaymentIntents; the browser only confirms payment with Stripe Elements. No Stripe secret belongs in the frontend.

## 5. Connect the wholesaler

The function contract assumes:
- Order submission: HTTPS POST to `WHOLESALER_ORDER_URL`, authenticated with `Authorization: Bearer ...`.
- The request includes reference, IMEI, brand, device type, model, network and service email.
- A successful JSON response includes `order_id` or `id` (or `order.id`).
- Status endpoint template includes `{supplier_order_id}` and returns JSON such as `{"status":"completed","code":"..." }`.

These fields and the idempotency header must be reconciled with the actual supplier's API contract before going live. The source uses a stable idempotency key, but the supplier must support idempotency to guarantee duplicate protection after network failures. A missing or mock provider cannot process real unlocks.

## 6. Set up 15-minute polling

Enable `pg_cron`, `pg_net` and Vault if they are not already enabled. Create these Vault secrets **once**, substituting your project URL and a long random secret:

    select vault.create_secret('https://YOUR_PROJECT_REF.supabase.co', 'jroc_supabase_url');
    select vault.create_secret('YOUR_LONG_RANDOM_CRON_SECRET', 'jroc_unlock_poll_secret');

Then run `cron/schedule_unlock_polling.sql`. Set the same cron secret as `UNLOCK_POLL_SECRET` in Edge Function secrets. Verify the scheduled job in **Integrations → Cron** and inspect `cron.job_run_details` when troubleshooting.

### Why the polling request uses an Edge Function

Supabase `pg_net` HTTP methods are asynchronous: `net.http_get()` returns a request ID before the response body is ready. Reading the body within the same SQL statement can race the HTTP worker. This setup uses native pg_cron to call `poll-unlock-orders` every 15 minutes; the Edge Function filters `Processing` rows, performs each authenticated HTTPS GET, waits for the response, and stores the resulting status/code. That keeps API secrets out of public tables and avoids a race against pg_net's response queue.

## 7. Run the React frontend

From `web/`:

    Copy-Item .env.example .env.local
    # Edit .env.local and fill in your real public project URL and publishable/anon key.
    npm install
    npm test
    npm run build
    npm run dev

The UI supports Apple and Samsung phones, tablets and laptops. Carrier-unlock checkout is limited to eligible phones and cellular tablets with a 15-digit IMEI. Laptops are repair-intake only.

## Security and release checklist

- Do not create direct public `INSERT`, `SELECT` or `UPDATE` policies on `orders` or `repair_requests`.
- Do not add service-role keys, Stripe secrets, webhook secrets, supplier keys or cron secrets to the frontend.
- Restrict dashboard/operator access outside this public storefront; the current React frontend is not a multi-user staff admin console.
- Test supplier error, timeout, duplicate webhook, repeated polling, incomplete vendor response and invalid tracking-token cases.
- Review Supabase Security Advisors after applying the migration.
- Test end-to-end in Stripe test mode and with the supplier's sandbox before accepting live payments.
- Use authorized service procedures only; no account-lock, Activation Lock, PIN/password or other security bypass is provided.
