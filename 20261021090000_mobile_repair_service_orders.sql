-- J-Roc AI Mobile Repair — Supabase schema
-- Public browser clients never receive direct table grants. All inserts/lookups
-- pass through validated Edge Functions using the server-side service key.
create extension if not exists pgcrypto;

create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  imei text not null check (imei ~ '^[0-9]{15}$'),
  brand text not null check (brand in ('Apple', 'Samsung')),
  model text not null check (length(trim(model)) between 1 and 120),
  device_type text not null default 'Phone' check (device_type in ('Phone', 'Tablet')),
  network text not null check (length(trim(network)) between 1 and 120),
  email text not null check (length(email) between 5 and 254),
  status text not null default 'Awaiting Payment',
  stripe_intent_id text unique,
  supplier_order_id text,
  unlock_code text not null default '',
  public_reference text not null unique,
  lookup_token_hash text not null,
  supplier_error text,
  poll_attempts integer not null default 0 check (poll_attempts >= 0),
  last_supplier_poll_at timestamptz
);

create index if not exists orders_imei_idx on public.orders (imei);
create index if not exists orders_processing_idx
  on public.orders (created_at)
  where status = 'Processing' and supplier_order_id is not null;

create table if not exists public.repair_requests (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  brand text not null check (brand in ('Apple', 'Samsung')),
  device_type text not null check (device_type in ('Phone', 'Tablet', 'Laptop')),
  model text not null check (length(trim(model)) between 1 and 120),
  email text not null check (length(email) between 5 and 254),
  imei text check (imei is null or imei ~ '^[0-9]{15}$'),
  issue text not null check (length(trim(issue)) between 3 and 2000),
  status text not null default 'Awaiting Review',
  public_reference text not null unique,
  lookup_token_hash text not null
);

create index if not exists repair_requests_reference_idx
  on public.repair_requests (public_reference);

-- Tables are in an exposed schema, so enable RLS and intentionally create no
-- anon/authenticated policies. Public access must use narrowly-scoped functions.
alter table public.orders enable row level security;
alter table public.repair_requests enable row level security;

revoke all on table public.orders from public, anon, authenticated;
revoke all on table public.repair_requests from public, anon, authenticated;
grant select, insert, update, delete on table public.orders to service_role;
grant select, insert, update, delete on table public.repair_requests to service_role;

comment on table public.orders is
  'Private carrier service orders. Read/write only by trusted Edge Functions; never exposed for direct anonymous lookups.';
comment on column public.orders.lookup_token_hash is
  'SHA-256 hash of a high-entropy customer-held token; raw token is shown once and never stored.';
comment on column public.orders.unlock_code is
  'Supplier result; only returned by the token-verified lookup Edge Function after completion.';
comment on table public.repair_requests is
  'Private Apple/Samsung phone/tablet/laptop repair intake submitted through the create-repair-request Edge Function.';
