alter table public.jobs
  add column if not exists posted_fare_yen integer;

alter table public.jobs
  add column if not exists fare_ratio_text text;

notify pgrst, 'reload schema';
