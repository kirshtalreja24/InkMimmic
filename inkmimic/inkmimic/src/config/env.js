// Centralized environment access.
// Every env var the app needs is read once here so the rest of the codebase
// never touches import.meta.env directly — makes it trivial to see what's
// required, and to swap sources later (e.g. server-injected config).

export const env = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL ?? '',
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY ?? '',
// Prototyping only — see src/packages/ai-prototype/README.md.
  // Never ship a build with a real key baked into client code.
  geminiApiKey: import.meta.env.VITE_GEMINI_API_KEY ?? '',
  geminiModel: import.meta.env.VITE_GEMINI_MODEL ?? 'gemini-2.5-flash',
};

export const isSupabaseConfigured = Boolean(env.supabaseUrl && env.supabaseAnonKey);
export const isAiPrototypeConfigured = Boolean(env.geminiApiKey);