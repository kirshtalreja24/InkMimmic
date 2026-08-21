import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth.js';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  // Login is mandatory even without Supabase configured — signing in still
  // works in that case via the local-mode fallback in session.js (any
  // email/password creates a fabricated on-device session), so there's
  // always a real sign-in step to check here.
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
