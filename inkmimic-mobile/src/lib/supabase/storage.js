import { supabase, assertSupabaseConfigured } from './client.js';

const HANDWRITING_BUCKET = 'handwriting-samples';

/**
 * Uploads a user's handwriting sample to their own folder in the
 * handwriting-samples bucket. On native, `asset` is whatever
 * expo-image-picker / expo-document-picker returned (an object with a
 * local `uri`, `mimeType`, and `fileName` / `name`) rather than a browser
 * File — so we fetch the local URI into a blob first.
 *
 * Bucket + RLS policies need to be created on the Supabase project
 * (see supabase/setup.sql).
 */
export async function uploadHandwritingSample(userId, asset) {
  assertSupabaseConfigured();

  const response = await fetch(asset.uri);
  const blob = await response.blob();

  const fileName = asset.fileName ?? asset.name ?? `sample-${Date.now()}`;
  const path = `${userId}/${Date.now()}-${fileName}`;

  const { data, error } = await supabase.storage.from(HANDWRITING_BUCKET).upload(path, blob, {
    contentType: asset.mimeType ?? blob.type ?? 'application/octet-stream',
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
