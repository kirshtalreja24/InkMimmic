import { createPersistenceModule } from 'inkmimic-core';
import { supabase } from './client.js';
import { isSupabaseConfigured } from '../../config/env.js';

export const { saveArtifact, listArtifacts, getArtifactUrl } = createPersistenceModule({
  supabase,
  isSupabaseConfigured,
});
