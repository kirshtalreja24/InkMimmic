-- Run this once in the Supabase SQL editor for a new project.
-- If you're using the SAME Supabase project as the Inkmimic webapp, you've
-- already run this — no need to run it again.
--
-- Creates the storage bucket used by src/lib/supabase/storage.js and locks
-- it down so each user can only read/write their own folder
-- (handwriting-samples/<user_id>/...).

insert into storage.buckets (id, name, public)
values ('handwriting-samples', 'handwriting-samples', false)
on conflict (id) do nothing;

create policy "Users can upload their own samples"
  on storage.objects for insert
  with check (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can read their own samples"
  on storage.objects for select
  using (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users can delete their own samples"
  on storage.objects for delete
  using (
    bucket_id = 'handwriting-samples'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
