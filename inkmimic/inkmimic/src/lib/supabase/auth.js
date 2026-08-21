import { createSessionModule } from 'inkmimic-core';
import { supabase } from './client.js';
import { isSupabaseConfigured } from '../../config/env.js';

// localStorage's getItem/setItem/removeItem already match the shape
// createSessionModule expects, so it's passed straight through.
export const { signInWithPassword, signUpWithPassword, signOut, getSession, onAuthStateChange } =
  createSessionModule({
    supabase,
    isSupabaseConfigured,
    storage: localStorage,
    localSessionKey: 'inkmimic_local_session',
    notify: () => window.dispatchEvent(new Event('inkmimic_auth_changed')),
  });
