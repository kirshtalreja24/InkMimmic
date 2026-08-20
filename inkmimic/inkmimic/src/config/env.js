// Centralized environment access.
// Every env var the app needs is read once here so the rest of the codebase
// never touches import.meta.env directly — makes it trivial to see what's
// required, and to swap sources later (e.g. server-injected config).

export const env = {
  supabaseUrl: (import.meta.env.VITE_SUPABASE_URL ?? '').trim(),
  supabaseAnonKey: (import.meta.env.VITE_SUPABASE_ANON_KEY ?? '').trim(),
  apiUrl: (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').trim(),
};

export const isSupabaseConfigured = Boolean(
  env.supabaseUrl &&
  env.supabaseAnonKey &&
  env.supabaseUrl.startsWith('http') &&
  !env.supabaseUrl.includes('placeholder') &&
  !env.supabaseAnonKey.includes('placeholder')
);