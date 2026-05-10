alter table public.jobs
  add column if not exists posting_type text default 'delivery',
  add column if not exists title text,
  add column if not exists free_text text,
  add column if not exists target_area text;

alter table public.jobs
  drop constraint if exists jobs_posting_type_check,
  add constraint jobs_posting_type_check
  check (posting_type is null or posting_type in ('delivery', 'other'));

alter table public.jobs
  drop constraint if exists jobs_job_category_check,
  add constraint jobs_job_category_check
  check (
    job_category is null
    or job_category in (
      'spot',
      'charter',
      'regular',
      'work',
      'driver_recruitment',
      'referral_request',
      'other'
    )
  );

create index if not exists jobs_posting_type_idx on public.jobs(posting_type);
create index if not exists jobs_title_idx on public.jobs(title);

grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
