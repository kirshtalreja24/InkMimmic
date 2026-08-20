// Centralized environment access for the mobile app.
// Expo reads env vars prefixed with EXPO_PUBLIC_ automatically into
// process.env at build time — same idea as Vite's import.meta.env on web.

export const env = {
  supabaseUrl: (process.env.EXPO_PUBLIC_SUPABASE_URL ?? '').trim(),
  supabaseAnonKey: (process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '').trim(),
  apiUrl: (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').trim(),
};

export const isSupabaseConfigured = Boolean(
  env.supabaseUrl &&
  env.supabaseAnonKey &&
  env.supabaseUrl.startsWith('http') &&
  !env.supabaseUrl.includes('placeholder') &&
  !env.supabaseAnonKey.includes('placeholder')
);


