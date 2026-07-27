import { createContext, useEffect, useMemo, useState } from 'react';
import { isSupabaseConfigured } from '../config/env.js';
import { getSession, onAuthStateChange, signOut as supabaseSignOut } from '../lib/supabase/auth.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(isSupabaseConfigured);

  useEffect(() => {
    if (!isSupabaseConfigured) return undefined;

    let subscription;

    getSession()
      .then((s) => setSession(s))
      .finally(() => setLoading(false));

    subscription = onAuthStateChange((_event, s) => {
      setSession(s);
    });

    return () => subscription?.unsubscribe();
  }, []);

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.user),
      loading,
      signOut: async () => {
        await supabaseSignOut();
        setSession(null);
      },
    }),
    [session, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
