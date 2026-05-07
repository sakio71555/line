create extension if not exists "pgcrypto";

alter table public.jobs
  add column if not exists delivery_date date,
  add column if not exists posted_at timestamptz,
  add column if not exists pickup_date date,
  add column if not exists pickup_time_text text,
  add column if not exists delivery_time_text text,
  add column if not exists schedule_text text,
  add column if not exists date_confidence numeric(4, 3)
    check (date_confidence is null or (date_confidence >= 0 and date_confidence <= 1)),
  add column if not exists date_needs_review boolean not null default false,
  add column if not exists recurring boolean not null default false,
  add column if not exists import_batch_id uuid,
  add column if not exists history_message_hash text,
  add column if not exists notify_group_id text,
  add column if not exists notified_at timestamptz,
  add column if not exists notify_error text;

alter table public.jobs
  drop constraint if exists jobs_source_type_check,
  add constraint jobs_source_type_check
  check (
    source_type is null
    or source_type in ('line_group', 'liff_form', 'admin_manual', 'line_history_import')
  );

create index if not exists jobs_delivery_date_idx on public.jobs(delivery_date);
create index if not exists jobs_pickup_date_idx on public.jobs(pickup_date);
create index if not exists jobs_posted_at_idx on public.jobs(posted_at);
create index if not exists jobs_import_batch_id_idx on public.jobs(import_batch_id);
create index if not exists jobs_notify_group_id_idx on public.jobs(notify_group_id);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
