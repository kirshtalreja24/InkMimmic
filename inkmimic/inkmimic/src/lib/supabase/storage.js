import { supabase, assertSupabaseConfigured } from './client.js';

const HANDWRITING_BUCKET = 'handwriting-samples';

/**
 * Uploads a user's handwriting sample file to their own folder in the
 * handwriting-samples bucket. Bucket + RLS policies need to be created on
 * the Supabase project (see README.md in this package for the SQL).
 */
export async function uploadHandwritingSample(userId, file) {
  assertSupabaseConfigured();
  const path = `${userId}/${Date.now()}-${file.name}`;
  const { data, error } = await supabase.storage.from(HANDWRITING_BUCKET).upload(path, file, {
    cacheControl: '3600',
    upsert: false,
  });
  if (error) throw error;
  return data;
}

export async function getSignedUrl(path, expiresInSeconds = 3600) {
  assertSupabaseConfigured();
  const { data, error } = await supabase.storage
    .from(HANDWRITING_BUCKET)
    .createSignedUrl(path, expiresInSeconds);
  if (error) throw error;
  return data.signedUrl;
}

export async function listUserSamples(userId) {
  assertSupabaseConfigured();
  const { data, error } = await supabase.storage.from(HANDWRITING_BUCKET).list(userId, {
    sortBy: { column: 'created_at', order: 'desc' },
  });
  if (error) throw error;
  return data;
}
