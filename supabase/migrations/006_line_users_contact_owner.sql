create extension if not exists "pgcrypto";

create table if not exists public.line_users (
  id uuid primary key default gen_random_uuid(),
  line_user_id text unique not null,
  display_name text,
  picture_url text,
  company_name text,
  contact_name text,
  phone_number text,
  role text not null default 'member',
  can_post_jobs boolean not null default false,
  can_close_own_jobs boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.jobs
  add column if not exists created_by_line_user_id text,
  add column if not exists created_by_display_name text,
  add column if not exists contact_line_user_id text,
  add column if not exists contact_display_name text,
  add column if not exists contact_phone text,
  add column if not exists contact_method text,
  add column if not exists contact_missing boolean not null default false,
  add column if not exists closed_reported_by_line_user_id text,
  add column if not exists closed_reported_at timestamptz;

alter table public.jobs
  drop constraint if exists jobs_contact_method_check,
  add constraint jobs_contact_method_check
  check (
    contact_method is null
    or contact_method in ('phone', 'registered_phone', 'group_reply_or_admin', 'form')
  );

alter table public.job_status_updates
  add column if not exists reported_by_line_user_id text,
  add column if not exists reported_by_display_name text,
  add column if not exists is_reported_by_job_owner boolean not null default false;

create index if not exists line_users_line_user_id_idx on public.line_users(line_user_id);
create index if not exists jobs_created_by_line_user_id_idx on public.jobs(created_by_line_user_id);
create index if not exists jobs_contact_line_user_id_idx on public.jobs(contact_line_user_id);
create index if not exists jobs_contact_missing_idx on public.jobs(contact_missing);
create index if not exists job_status_updates_reported_by_line_user_id_idx on public.job_status_updates(reported_by_line_user_id);
create index if not exists job_status_updates_owner_report_idx on public.job_status_updates(is_reported_by_job_owner);

drop trigger if exists set_line_users_updated_at on public.line_users;

create trigger set_line_users_updated_at
before update on public.line_users
for each row execute function public.set_updated_at();

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.line_users to service_role;
grant select, insert, update, delete on table public.jobs to service_role;
grant select, insert, update, delete on table public.job_status_updates to service_role;

alter table public.line_users enable row level security;
