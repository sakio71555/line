alter table public.jobs
  add column if not exists phone_number text;

update public.jobs
set phone_number = contact_phone
where phone_number is null
  and contact_phone is not null;

create index if not exists jobs_phone_number_idx on public.jobs(phone_number);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
