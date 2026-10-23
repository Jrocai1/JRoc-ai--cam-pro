-- Run only after migrations are applied, the poll-unlock-orders Edge Function
-- is deployed, and the two Vault secrets below have been created.
--
-- Supabase pg_net calls are asynchronous: net.http_get() returns a request ID
-- before the remote body is available in PostgreSQL. The scheduled Edge Function
-- performs the HTTPS GET, awaits/parses the response, and updates each order.
-- This avoids racing the net._http_response queue and keeps the supplier API key
-- out of SQL-visible tables.

create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

-- Run once with your real project URL and a long random secret; do not commit
-- actual values to GitHub:
-- select vault.create_secret('https://YOUR_PROJECT_REF.supabase.co', 'jroc_supabase_url');
-- select vault.create_secret('YOUR_LONG_RANDOM_CRON_SECRET', 'jroc_unlock_poll_secret');
--
-- Set the matching UNLOCK_POLL_SECRET secret on the Edge Function.

select cron.unschedule(jobid)
from cron.job
where jobname = 'jroc-mobile-repair-poll-unlock-orders';

select cron.schedule(
  'jroc-mobile-repair-poll-unlock-orders',
  '*/15 * * * *',
  $job$
    select net.http_post(
      url := (
        select decrypted_secret
        from vault.decrypted_secrets
        where name = 'jroc_supabase_url'
        limit 1
      ) || '/functions/v1/poll-unlock-orders',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'x-cron-secret', (
          select decrypted_secret
          from vault.decrypted_secrets
          where name = 'jroc_unlock_poll_secret'
          limit 1
        )
      ),
      body := '{}'::jsonb,
      timeout_milliseconds := 10000
    );
  $job$
);

-- Verify the job and its runs in Dashboard > Integrations > Cron or query:
-- select jobid, jobname, schedule, active from cron.job
-- where jobname = 'jroc-mobile-repair-poll-unlock-orders';
-- select * from cron.job_run_details order by start_time desc limit 20;
