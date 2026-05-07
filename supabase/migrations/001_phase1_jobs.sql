create extension if not exists "pgcrypto";

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  source_group_id text,
  source_user_id text,
  source_message_id text unique,
  raw_text text not null,

  pickup_location text,
  delivery_location text,
  pickup_prefecture text,
  delivery_prefecture text,
  scheduled_date date,
  scheduled_time_text text,
  vehicle_type text,
  cargo_type text,
  price integer,

  status text not null default '募集中'
    check (status in ('募集中', '交渉中', '成約済', '非公開')),

  confidence numeric(4, 3)
    check (confidence is null or (confidence >= 0 and confidence <= 1)),
  missing_fields jsonb not null default '[]'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists jobs_status_idx on public.jobs(status);
create index if not exists jobs_scheduled_date_idx on public.jobs(scheduled_date);
create index if not exists jobs_pickup_prefecture_idx on public.jobs(pickup_prefecture);
create index if not exists jobs_delivery_prefecture_idx on public.jobs(delivery_prefecture);
create index if not exists jobs_source_group_id_idx on public.jobs(source_group_id);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

alter table public.jobs enable row level security;

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_jobs_updated_at on public.jobs;

create trigger set_jobs_updated_at
before update on public.jobs
for each row execute function public.set_updated_at();
