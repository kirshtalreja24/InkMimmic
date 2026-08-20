import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm.jsx';
import { RegisterForm } from '../components/auth/RegisterForm.jsx';
import { isSupabaseConfigured } from '../config/env.js';
import { signInWithPassword } from '../lib/supabase/auth.js';

export default function AuthPage() {
  const [mode, setMode] = useState('login'); // login | register
  const navigate = useNavigate();

  async function handleGuestAccess() {
    await signInWithPassword('guest@inkmimic.local', 'password123');
    navigate('/workspace');
  }


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
              Running in local mode. You can sign in or create an account with any email/password, or continue as guest below.
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

          <div className="mt-6 border-t border-royal-500/15 pt-6 text-center">
            <button
              type="button"
              onClick={handleGuestAccess}
              className="text-xs font-semibold text-gold-300/80 hover:text-gold-300 hover:underline"
            >
              Continue as Guest (Skip Sign In) →
            </button>
          </div>


        </div>
      </div>
    </div>
  );
}
