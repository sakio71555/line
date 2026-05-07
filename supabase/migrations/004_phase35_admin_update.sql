alter table public.jobs
  drop constraint if exists jobs_analysis_status_check;

alter table public.jobs
  add constraint jobs_analysis_status_check
  check (analysis_status in ('pending', 'parsed', 'needs_review', 'failed', 'verified'));

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;
