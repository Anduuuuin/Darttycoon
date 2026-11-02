create table if not exists profiles (
  code text primary key,
  name text,
  club text,
  stats jsonb,
  updated_at timestamptz default now()
);
alter table profiles enable row level security;
create policy "profiles_select" on profiles for select using (true);
create policy "profiles_insert" on profiles for insert with check (true);
create policy "profiles_update" on profiles for update using (true) with check (true);
