-- Dayline schema for Supabase. Paste into: Supabase dashboard → SQL Editor → New query → Run.
-- Safe to re-run.

create table if not exists public.items (
  id         text        not null,
  user_id    uuid        not null default auth.uid() references auth.users (id) on delete cascade,
  title      text        not null check (length(title) between 1 and 500),
  type       text        not null default 'task'
             check (type in ('meeting','focus','call','email','learn','personal','task')),
  space      text        not null default 'work'
             check (space in ('work','build','growth','life')),
  date       date        not null,
  time       text        check (time ~ '^\d\d:\d\d$'),
  dur        integer     not null default 30 check (dur between 5 and 1440),
  done       boolean     not null default false,
  doing      boolean     not null default false,
  note       text        not null default '',
  updated_at timestamptz not null default now(),
  primary key (user_id, id)
);

-- Added for the Kanban board (safe on existing tables).
alter table public.items add column if not exists doing boolean not null default false;

create index if not exists items_user_date on public.items (user_id, date);

-- Row-level security: every query only ever sees the signed-in user's rows.
alter table public.items enable row level security;

drop policy if exists "Own items only" on public.items;
create policy "Own items only" on public.items
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- Live updates between browsers.
do $$ begin
  alter publication supabase_realtime add table public.items;
exception when duplicate_object then null; end $$;
