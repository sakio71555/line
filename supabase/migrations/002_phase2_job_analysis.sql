alter table public.jobs
  add column if not exists notes text,
  add column if not exists analysis_status text not null default 'pending'
    check (analysis_status in ('pending', 'parsed', 'needs_review', 'failed')),
  add column if not exists analysis_error text,
  add column if not exists analysis_model text,
  add column if not exists analysis_completed_at timestamptz,
  add column if not exists review_required boolean not null default true;

create index if not exists jobs_analysis_status_idx on public.jobs(analysis_status);
create index if not exists jobs_review_required_idx on public.jobs(review_required);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;
