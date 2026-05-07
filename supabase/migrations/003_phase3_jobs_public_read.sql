grant usage on schema public to anon, authenticated;
grant select on table public.jobs to anon, authenticated;

drop policy if exists jobs_public_read_visible on public.jobs;

create policy jobs_public_read_visible
on public.jobs
for select
to anon, authenticated
using (status <> '非公開');
