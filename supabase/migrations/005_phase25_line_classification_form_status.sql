create extension if not exists "pgcrypto";

create table if not exists public.line_messages (
  id uuid primary key default gen_random_uuid(),
  source_group_id text,
  source_user_id text,
  source_message_id text,
  event_type text,
  message_type text,
  raw_text text,
  attachment_type text,
  attachment_file_name text,
  attachment_message_id text,
  is_unsent boolean not null default false,
  received_at timestamptz,
  created_at timestamptz not null default now(),
  classification_confidence numeric(4, 3)
    check (classification_confidence is null or (classification_confidence >= 0 and classification_confidence <= 1)),
  classification_reason text,
  processed_at timestamptz,
  processing_error text
);

alter table public.jobs
  add column if not exists source_type text,
  add column if not exists source_line_message_id uuid references public.line_messages(id),
  add column if not exists job_category text,
  add column if not exists vehicle_count integer,
  add column if not exists delivery_date date,
  add column if not exists tax_type text,
  add column if not exists fee_note text,
  add column if not exists highway_fee_note text,
  add column if not exists budget_note text,
  add column if not exists company_name text,
  add column if not exists contact_name text,
  add column if not exists phone_numbers jsonb not null default '[]'::jsonb,
  add column if not exists created_by_line_user_id text,
  add column if not exists created_by_display_name text,
  add column if not exists assigned_at timestamptz,
  add column if not exists in_progress_at timestamptz,
  add column if not exists completed_at timestamptz,
  add column if not exists cancelled_at timestamptz,
  add column if not exists status_updated_at timestamptz,
  add column if not exists status_updated_by text,
  add column if not exists closed_reason text;

alter table public.jobs
  drop constraint if exists jobs_status_check;

update public.jobs
set
  status = case status
    when '募集中' then 'open'
    when '交渉中' then 'negotiating'
    when '成約済' then 'assigned'
    when '非公開' then 'hidden'
    else status
  end,
  source_type = coalesce(source_type, 'line_group')
where status in ('募集中', '交渉中', '成約済', '非公開')
   or source_type is null;

alter table public.jobs
  alter column status set default 'needs_review';

alter table public.jobs
  add constraint jobs_status_check
  check (status in ('needs_review', 'open', 'negotiating', 'assigned', 'in_progress', 'completed', 'cancelled', 'hidden'));

alter table public.jobs
  drop constraint if exists jobs_analysis_status_check;

alter table public.jobs
  add constraint jobs_analysis_status_check
  check (analysis_status in ('pending', 'parsed', 'needs_review', 'failed', 'verified', 'form_submitted'));

alter table public.jobs
  drop constraint if exists jobs_source_type_check,
  add constraint jobs_source_type_check
  check (source_type is null or source_type in ('line_group', 'liff_form', 'admin_manual'));

alter table public.jobs
  drop constraint if exists jobs_job_category_check,
  add constraint jobs_job_category_check
  check (job_category is null or job_category in ('spot', 'charter', 'regular', 'work', 'other'));

alter table public.jobs
  drop constraint if exists jobs_tax_type_check,
  add constraint jobs_tax_type_check
  check (tax_type is null or tax_type in ('税別', '税込', '不明'));

create table if not exists public.vehicle_availabilities (
  id uuid primary key default gen_random_uuid(),
  source_line_message_id uuid references public.line_messages(id),
  source_group_id text,
  source_user_id text,
  location text,
  prefecture text,
  vehicle_type text,
  available_from timestamptz,
  company_name text,
  contact_name text,
  phone_numbers jsonb not null default '[]'::jsonb,
  status text not null default 'open',
  review_required boolean not null default true,
  confidence numeric(4, 3)
    check (confidence is null or (confidence >= 0 and confidence <= 1)),
  raw_text text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.vehicle_availabilities
  drop constraint if exists vehicle_availabilities_status_check,
  add constraint vehicle_availabilities_status_check
  check (status in ('open', 'assigned', 'completed', 'cancelled', 'hidden'));

create table if not exists public.job_status_updates (
  id uuid primary key default gen_random_uuid(),
  source_line_message_id uuid references public.line_messages(id),
  source_group_id text,
  source_user_id text,
  source_message_id text,
  raw_text text not null,
  update_type text,
  proposed_status text,
  possible_job_id uuid references public.jobs(id),
  candidates jsonb not null default '[]'::jsonb,
  confidence numeric(4, 3)
    check (confidence is null or (confidence >= 0 and confidence <= 1)),
  review_required boolean not null default true,
  reason text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text,
  applied_at timestamptz,
  ignored_at timestamptz
);

alter table public.job_status_updates
  drop constraint if exists job_status_updates_update_type_check,
  add constraint job_status_updates_update_type_check
  check (update_type is null or update_type in ('job_closed', 'assigned_candidate', 'completed_candidate', 'cancelled_candidate'));

alter table public.job_status_updates
  drop constraint if exists job_status_updates_proposed_status_check,
  add constraint job_status_updates_proposed_status_check
  check (proposed_status is null or proposed_status in ('assigned', 'completed', 'cancelled', 'hidden'));

create table if not exists public.job_status_history (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.jobs(id),
  old_status text,
  new_status text not null,
  reason text,
  source_type text,
  source_line_message_id uuid references public.line_messages(id),
  changed_by_line_user_id text,
  changed_by_name text,
  created_at timestamptz not null default now()
);

create index if not exists line_messages_source_message_id_idx on public.line_messages(source_message_id);
create index if not exists line_messages_message_type_idx on public.line_messages(message_type);
create index if not exists line_messages_source_group_id_idx on public.line_messages(source_group_id);
create index if not exists line_messages_received_at_idx on public.line_messages(received_at);
create index if not exists jobs_source_line_message_id_idx on public.jobs(source_line_message_id);
create index if not exists jobs_source_type_idx on public.jobs(source_type);
create index if not exists jobs_job_category_idx on public.jobs(job_category);
create index if not exists jobs_delivery_date_idx on public.jobs(delivery_date);
create index if not exists jobs_status_created_at_idx on public.jobs(status, created_at desc);
create index if not exists vehicle_availabilities_status_idx on public.vehicle_availabilities(status);
create index if not exists vehicle_availabilities_source_line_message_id_idx on public.vehicle_availabilities(source_line_message_id);
create index if not exists job_status_updates_review_idx on public.job_status_updates(review_required, created_at desc);
create index if not exists job_status_updates_possible_job_id_idx on public.job_status_updates(possible_job_id);
create index if not exists job_status_history_job_id_idx on public.job_status_history(job_id);

drop trigger if exists set_vehicle_availabilities_updated_at on public.vehicle_availabilities;

create trigger set_vehicle_availabilities_updated_at
before update on public.vehicle_availabilities
for each row execute function public.set_updated_at();

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.line_messages to service_role;
grant select, insert, update, delete on table public.jobs to service_role;
grant select, insert, update, delete on table public.vehicle_availabilities to service_role;
grant select, insert, update, delete on table public.job_status_updates to service_role;
grant select, insert on table public.job_status_history to service_role;

grant usage on schema public to anon, authenticated;
grant select on table public.jobs to anon, authenticated;

alter table public.line_messages enable row level security;
alter table public.jobs enable row level security;
alter table public.vehicle_availabilities enable row level security;
alter table public.job_status_updates enable row level security;
alter table public.job_status_history enable row level security;

drop policy if exists jobs_public_read_visible on public.jobs;

create policy jobs_public_read_visible
on public.jobs
for select
to anon, authenticated
using (status in ('open', 'negotiating', 'assigned', 'in_progress'));
