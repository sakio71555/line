alter table public.jobs
  add column if not exists distance_km numeric(10, 2),
  add column if not exists distance_text text,
  add column if not exists distance_source text,
  add column if not exists standard_fare_yen integer,
  add column if not exists fare_ratio_percent numeric(6, 2),
  add column if not exists fare_judgement text,
  add column if not exists fare_calc_status text,
  add column if not exists fare_calc_note text,
  add column if not exists fare_region text,
  add column if not exists fare_vehicle_class text,
  add column if not exists fare_vehicle_label text;

create index if not exists jobs_fare_calc_status_idx on public.jobs(fare_calc_status);
create index if not exists jobs_distance_km_idx on public.jobs(distance_km);

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.jobs to service_role;

notify pgrst, 'reload schema';
