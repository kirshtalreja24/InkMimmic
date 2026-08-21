// Persistence module shared by the Inkmimic web and mobile apps — saves a
// signed-in user's generated Artifacts (and their handwriting Samples) to
// Supabase Storage + a `public.artifacts` row, instead of letting them
// vanish on refresh (the gap ADR 0007 flagged as the top go-live item).
//
// No-ops quietly when Supabase isn't configured (local-mode sessions have
// no real backend to persist to) so callers don't need to branch on it.
//
// Converting the generated PNG (a data: URI from api/server.py) to an
// ArrayBuffer via fetch().arrayBuffer() is the pattern Supabase's own
// React Native storage guide recommends — it works identically on web,
// so both platforms share this one code path instead of a Blob (RN's
// Blob support for Supabase uploads is comparatively flaky).

async function dataUriToArrayBuffer(dataUri) {
  const res = await fetch(dataUri);
  return res.arrayBuffer();
}

/**
 * @param {object} params
 * @param {import('@supabase/supabase-js').SupabaseClient | null} params.supabase
 * @param {boolean} params.isSupabaseConfigured
 * @param {string} [params.bucket] - Storage bucket for generated pages.
 * @param {string} [params.table] - Table tracking each saved artifact.
 */
export function createPersistenceModule({
  supabase,
  isSupabaseConfigured,
  bucket = 'generated-artifacts',
  table = 'artifacts',
}) {
  /**
   * @param {object} params
   * @param {string} params.userId
   * @param {string} params.artifactId - same id returned by /api/generate.
   * @param {string} params.dataUri - the generated PNG as a data: URI.
   * @param {string} params.prompt
   * @param {string} [params.paper]
   * @param {string} [params.inkColor]
   */
  async function saveArtifact({ userId, artifactId, dataUri, prompt, paper, inkColor }) {
    if (!isSupabaseConfigured || !supabase || !userId) return null;

    const path = `${userId}/${artifactId}.png`;
    const buffer = await dataUriToArrayBuffer(dataUri);

    const { error: uploadError } = await supabase.storage.from(bucket).upload(path, buffer, {
      contentType: 'image/png',
      upsert: true,
    });
    if (uploadError) throw uploadError;

    const { error: dbError } = await supabase.from(table).insert({
      id: artifactId,
      user_id: userId,
      prompt,
      paper: paper ?? null,
      ink_color: inkColor ?? null,
      storage_path: path,
    });
    if (dbError) throw dbError;

    return { path };
  }

  async function listArtifacts(userId) {
    if (!isSupabaseConfigured || !supabase || !userId) return [];
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false });
    if (error) throw error;
    return data;
  }

  async function getArtifactUrl(path, expiresInSeconds = 3600) {
    if (!isSupabaseConfigured || !supabase) return null;
    const { data, error } = await supabase.storage.from(bucket).createSignedUrl(path, expiresInSeconds);
    if (error) throw error;
    return data.signedUrl;
  }

  return { saveArtifact, listArtifacts, getArtifactUrl };
}
