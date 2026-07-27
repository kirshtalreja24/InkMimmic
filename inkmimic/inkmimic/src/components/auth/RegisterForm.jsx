import { useState } from 'react';
import { signUpWithPassword } from '../../lib/supabase/auth.js';
import { Button } from '../ui/Button.jsx';

export function RegisterForm({ onSuccess, onSwitchToLogin }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password.length < 8) {
      setStatus('error');
      setError('Password needs at least 8 characters.');
      return;
    }
    setStatus('validating');
    setError(null);
    try {
      await signUpWithPassword(email, password, fullName);
      onSuccess?.();
    } catch (err) {
      setStatus('error');
      setError(err.message ?? 'Could not create your account. Try again.');
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="field-label" htmlFor="register-name">
          Full name
        </label>
        <input
          id="register-name"
          type="text"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="field-input"
          placeholder="Jordan Ellis"
        />
      </div>

      <div>
        <label className="field-label" htmlFor="register-email">
          Email
        </label>
        <input
          id="register-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="field-input"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label className="field-label" htmlFor="register-password">
          Password
        </label>
        <input
          id="register-password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field-input"
          placeholder="At least 8 characters"
        />
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      <Button type="submit" variant="gold" className="w-full" disabled={status === 'validating'}>
        {status === 'validating' ? 'Creating account…' : 'Create account'}
      </Button>

      <p className="text-center text-sm text-parchment/50">
        Already have an account?{' '}
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="font-semibold text-gold-300 hover:underline"
        >
          Sign in
        </button>
      </p>
    </form>
  );
}
