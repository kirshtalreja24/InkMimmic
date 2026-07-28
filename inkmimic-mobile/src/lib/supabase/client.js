import 'react-native-url-polyfill/auto';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';
import { env, isSupabaseConfigured } from '../../config/env.js';

// A single shared Supabase client for the whole app. Import this everywhere
// instead of calling createClient() again, so auth state stays in sync.
// React Native has no browser localStorage, so sessions are persisted via
// AsyncStorage instead, and URL-based session detection is turned off
// (there's no browser URL to read a token from on a native app).
export const supabase = isSupabaseConfigured
  ? createClient(env.supabaseUrl, env.supabaseAnonKey, {
      auth: {
        storage: AsyncStorage,
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: false,
      },
    })
  : null;

export function assertSupabaseConfigured() {
  if (!supabase) {
    throw new Error(
      'Supabase is not configured. Set EXPO_PUBLIC_SUPABASE_URL and EXPO_PUBLIC_SUPABASE_ANON_KEY in your .env file (see .env.example).'
    );
  }
}
