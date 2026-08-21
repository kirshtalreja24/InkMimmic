import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm.jsx';
import { RegisterForm } from '../components/auth/RegisterForm.jsx';
import { isSupabaseConfigured } from '../config/env.js';

export default function AuthPage() {
  const [mode, setMode] = useState('login'); // login | register
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 bg-ink-grain px-6 py-16">
      <div className="w-full max-w-md">
        <Link
          to="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-parchment/40 hover:text-parchment/70"
        >
          ← Back home
        </Link>

        <div className="ink-panel px-8 py-10 md:px-10">
          <p className="font-script text-2xl text-royal-400">
            {mode === 'login' ? 'Welcome back' : 'Join Inkmimic'}
          </p>
          <h1 className="mt-1 font-display text-2xl text-parchment">
            {mode === 'login' ? 'Sign in to your workspace' : 'Create your account'}
          </h1>

          {!isSupabaseConfigured && (
            <p className="mt-4 rounded-lg bg-royal-500/10 px-4 py-2.5 text-xs leading-relaxed text-parchment/70">
              Supabase isn't configured yet. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your .env file to enable authentication.
            </p>
          )}

          <div className="mt-6">
            {mode === 'login' ? (
              <LoginForm
                onSuccess={() => navigate('/workspace')}
                onSwitchToRegister={() => setMode('register')}
              />
            ) : (
              <RegisterForm
                onSuccess={() => navigate('/workspace')}
                onSwitchToLogin={() => setMode('login')}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
