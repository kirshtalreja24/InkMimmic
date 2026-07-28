import { useState } from 'react';
import { signInWithPassword } from '../../lib/supabase/auth.js';
import { Button } from '../ui/Button.jsx';

export function LoginForm({ onSuccess, onSwitchToRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('idle'); // idle | validating | error
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus('validating');
    setError(null);
    try {
      await signInWithPassword(email, password);
      onSuccess?.();
    } catch (err) {
      setStatus('error');
      setError(err.message ?? 'Invalid credentials. Try again.');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="field-label" htmlFor="login-email">
          Email
        </label>
        <input
          id="login-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="field-input"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label className="field-label" htmlFor="login-password">
          Password
        </label>
        <input
          id="login-password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field-input"
          placeholder="••••••••"
        />
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <Button type="submit" variant="gold" className="w-full" disabled={status === 'validating'}>
        {status === 'validating' ? 'Signing in…' : 'Sign in'}
      </Button>

      <p className="text-center text-sm text-parchment/50">
        New to Inkmimic?{' '}
        <button
          type="button"
          onClick={onSwitchToRegister}
          className="font-semibold text-gold-300 hover:underline"
        >
          Create an account
        </button>
      </p>
    </form>
  );
}
