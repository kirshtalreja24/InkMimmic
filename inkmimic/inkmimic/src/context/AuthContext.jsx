import { createContext, useEffect, useMemo, useState } from 'react';
import { isSupabaseConfigured } from '../config/env.js';
import { getSession, onAuthStateChange, signOut as supabaseSignOut } from '../lib/supabase/auth.js';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    try {
      const local = localStorage.getItem('inkmimic_local_session');
      return local ? JSON.parse(local) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    function syncSession() {
      getSession()
        .then((s) => {
          if (s) setSession(s);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }

    syncSession();

    window.addEventListener('inkmimic_auth_changed', syncSession);

    const subscription = onAuthStateChange((_event, s) => {
      setSession(s);
      setLoading(false);
    });

    return () => {
      window.removeEventListener('inkmimic_auth_changed', syncSession);
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
