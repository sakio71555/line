create extension if not exists "pgcrypto";

create table if not exists public.line_liff_sessions (
  id uuid primary key default gen_random_uuid(),
  session_id text unique not null,
  source_group_id text,
  source_user_id text,
  source_line_message_id uuid references public.line_messages(id),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);

alter table public.jobs
  add column if not exists notify_group_id text,
  add column if not exists notified_at timestamptz,
  add column if not exists notify_error text;

create index if not exists line_liff_sessions_session_id_idx on public.line_liff_sessions(session_id);
create index if not exists line_liff_sessions_expires_at_idx on public.line_liff_sessions(expires_at);
create index if not exists line_liff_sessions_source_group_id_idx on public.line_liff_sessions(source_group_id);
create index if not exists jobs_notify_group_id_idx on public.jobs(notify_group_id);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.line_liff_sessions to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

alter table public.line_liff_sessions enable row level security;
