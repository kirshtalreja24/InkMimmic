// Centralized environment access for the mobile app.
// Expo reads env vars prefixed with EXPO_PUBLIC_ automatically into
// process.env at build time — same idea as Vite's import.meta.env on web.

export const env = {
  supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL ?? '',
  supabaseAnonKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '',

  // Prototyping only — see src/packages/README.md.
  // Never ship a build with a real key baked into client code.
  geminiApiKey: process.env.EXPO_PUBLIC_GEMINI_API_KEY ?? '',
  geminiModel: process.env.EXPO_PUBLIC_GEMINI_MODEL ?? 'gemini-3.6-flash',
};

export const isSupabaseConfigured = Boolean(env.supabaseUrl && env.supabaseAnonKey);
export const isAiPrototypeConfigured = Boolean(env.geminiApiKey);
