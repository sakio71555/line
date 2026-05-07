alter table public.jobs
  add column if not exists pickup_city text,
  add column if not exists pickup_address text,
  add column if not exists delivery_city text,
  add column if not exists delivery_address text;

create index if not exists jobs_pickup_city_idx on public.jobs(pickup_city);
create index if not exists jobs_delivery_city_idx on public.jobs(delivery_city);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
