alter table public.jobs
  drop constraint if exists jobs_source_type_check,
  add constraint jobs_source_type_check
  check (
    source_type is null
    or source_type in ('line_group', 'liff_form', 'admin_manual', 'line_history_import')
  );

update public.jobs
set
  status = 'open',
  review_required = false,
  updated_at = now()
where source_type = 'liff_form'
  and status = 'needs_review';

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
