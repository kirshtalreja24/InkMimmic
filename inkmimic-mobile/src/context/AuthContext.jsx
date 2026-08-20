import { createContext, useEffect, useMemo, useState } from 'react';
import { isSupabaseConfigured } from '../config/env.js';
import { getSession, onAuthStateChange, signOut as supabaseSignOut } from '../lib/supabase/auth.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    getSession()
      .then((s) => {
        if (isMounted && s) setSession(s);
      })
      .catch(() => {})
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    const subscription = onAuthStateChange((_event, s) => {
      if (isMounted) {
        setSession(s);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
      try {
        subscription?.unsubscribe?.();
      } catch {}
    };
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
