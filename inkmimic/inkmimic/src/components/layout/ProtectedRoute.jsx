import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth.js';
import { isSupabaseConfigured } from '../../config/env.js';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  // Without Supabase configured there's no session to check — let the
  // workspace through so the UI (and handwriting chat) can still be
  // exercised during setup.
  if (!isSupabaseConfigured) return children;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-950">
        <span className="font-script text-xl text-parchment/50">Checking your session…</span>
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/auth" replace />;

  return children;
}
