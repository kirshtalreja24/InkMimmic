import { createClient } from '@supabase/supabase-js';
import { env, isSupabaseConfigured } from '../../config/env.js';

// A single shared Supabase client for the whole app. Import this everywhere
// instead of calling createClient() again, so auth state and realtime
// subscriptions stay in sync.
export const supabase = isSupabaseConfigured
  ? createClient(env.supabaseUrl, env.supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

export function assertSupabaseConfigured() {
  if (!supabase) {
    throw new Error(
      'Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file (see .env.example).'
    );
  }
}
