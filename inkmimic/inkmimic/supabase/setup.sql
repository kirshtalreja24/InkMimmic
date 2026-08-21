-- Run this once in the Supabase SQL editor for a new project.
-- Safe to re-run: every policy is dropped-then-recreated, and the bucket
-- inserts / table creation are already idempotent.
--
-- Creates the storage bucket used by src/lib/supabase/storage.js and locks
-- it down so each user can only read/write their own folder
-- (handwriting-samples/<user_id>/...).

insert into storage.buckets (id, name, public)
values ('handwriting-samples', 'handwriting-samples', false)
on conflict (id) do nothing;

drop policy if exists "Users can upload their own samples" on storage.objects;
create policy "Users can upload their own samples"
  on storage.objects for insert
  with check (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can read their own samples" on storage.objects;
create policy "Users can read their own samples"
  on storage.objects for select
  using (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can delete their own samples" on storage.objects;
create policy "Users can delete their own samples"
  on storage.objects for delete
  using (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Generated pages (Artifacts) — a storage bucket for the rendered PNGs,
-- plus a table row per Artifact so the app can list a user's past
-- generations (prompt, paper, ink color) without listing the bucket.

insert into storage.buckets (id, name, public)
values ('generated-artifacts', 'generated-artifacts', false)
on conflict (id) do nothing;

drop policy if exists "Users can upload their own artifacts" on storage.objects;
create policy "Users can upload their own artifacts"
  on storage.objects for insert
  with check (
    bucket_id = 'generated-artifacts'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can read their own artifact files" on storage.objects;
create policy "Users can read their own artifact files"
  on storage.objects for select
  using (
    bucket_id = 'generated-artifacts'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can delete their own artifact files" on storage.objects;
create policy "Users can delete their own artifact files"
  on storage.objects for delete
  using (
    bucket_id = 'generated-artifacts'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create table if not exists public.artifacts (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  prompt text not null,
  paper text,
  ink_color text,
  storage_path text not null,
  created_at timestamptz not null default now()
);

alter table public.artifacts enable row level security;

drop policy if exists "Users can insert their own artifact rows" on public.artifacts;
create policy "Users can insert their own artifact rows"
  on public.artifacts for insert
  with check (user_id = auth.uid());

drop policy if exists "Users can read their own artifact rows" on public.artifacts;
create policy "Users can read their own artifact rows"
  on public.artifacts for select
  using (user_id = auth.uid());

drop policy if exists "Users can delete their own artifact rows" on public.artifacts;
create policy "Users can delete their own artifact rows"
  on public.artifacts for delete
  using (user_id = auth.uid());
