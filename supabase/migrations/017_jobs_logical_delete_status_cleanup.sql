alter table public.jobs
  add column if not exists deleted_at timestamptz,
  add column if not exists deleted_by_line_user_id text,
  add column if not exists delete_reason text;

alter table public.jobs
  drop constraint if exists jobs_status_check;

alter table public.jobs
  add constraint jobs_status_check
  check (
    status in (
      'needs_review',
      'open',
      'negotiating',
      'assigned',
      'in_progress',
      'completed',
      'cancelled',
      'closed',
      'deleted',
      'hidden'
    )
  );

create index if not exists jobs_deleted_at_idx on public.jobs(deleted_at);
create index if not exists jobs_owner_visible_idx
  on public.jobs(created_by_line_user_id, created_at desc)
  where deleted_at is null;

drop policy if exists jobs_public_read_visible on public.jobs;

create policy jobs_public_read_visible
on public.jobs
for select
to anon, authenticated
using (
  deleted_at is null
  and status in ('open', 'assigned', 'closed', 'completed', 'cancelled')
);

grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
