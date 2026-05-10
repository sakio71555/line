alter table public.jobs
  drop constraint if exists jobs_status_check;

alter table public.jobs
  add constraint jobs_status_check
  check (status in ('needs_review', 'open', 'negotiating', 'assigned', 'in_progress', 'completed', 'cancelled', 'closed', 'hidden'));

drop policy if exists jobs_public_read_visible on public.jobs;

create policy jobs_public_read_visible
on public.jobs
for select
to anon, authenticated
using (status in ('open', 'negotiating', 'assigned', 'in_progress', 'closed', 'completed', 'cancelled'));

notify pgrst, 'reload schema';
