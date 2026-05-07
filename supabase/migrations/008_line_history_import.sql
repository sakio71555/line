create extension if not exists "pgcrypto";

alter table public.line_messages
  add column if not exists source_type text,
  add column if not exists source_display_name text,
  add column if not exists import_batch_id uuid,
  add column if not exists history_date date,
  add column if not exists history_time time,
  add column if not exists posted_at timestamptz,
  add column if not exists history_message_hash text;

alter table public.jobs
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
  add column if not exists history_message_hash text;

alter table public.vehicle_availabilities
  add column if not exists source_type text,
  add column if not exists available_date date,
  add column if not exists notes text,
  add column if not exists contact_phone text,
  add column if not exists posted_at timestamptz,
  add column if not exists import_batch_id uuid,
  add column if not exists history_message_hash text;

alter table public.job_status_updates
  add column if not exists source_type text,
  add column if not exists posted_at timestamptz,
  add column if not exists import_batch_id uuid,
  add column if not exists history_message_hash text;

alter table public.jobs
  drop constraint if exists jobs_source_type_check,
  add constraint jobs_source_type_check
  check (source_type is null or source_type in ('line_group', 'liff_form', 'admin_manual', 'line_history_import'));

create unique index if not exists line_messages_history_message_hash_key
  on public.line_messages(history_message_hash)
  where history_message_hash is not null;

create index if not exists line_messages_import_batch_id_idx on public.line_messages(import_batch_id);
create index if not exists line_messages_posted_at_idx on public.line_messages(posted_at);
create index if not exists jobs_import_batch_id_idx on public.jobs(import_batch_id);
create index if not exists jobs_pickup_date_idx on public.jobs(pickup_date);
create index if not exists jobs_posted_at_idx on public.jobs(posted_at);
create index if not exists vehicle_availabilities_import_batch_id_idx on public.vehicle_availabilities(import_batch_id);
create index if not exists job_status_updates_import_batch_id_idx on public.job_status_updates(import_batch_id);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.line_messages to service_role;
grant select, insert, update, delete on table public.jobs to service_role;
grant select, insert, update, delete on table public.vehicle_availabilities to service_role;
grant select, insert, update, delete on table public.job_status_updates to service_role;
