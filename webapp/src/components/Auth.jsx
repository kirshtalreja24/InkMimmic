import React, { useState } from 'react';
import { PenTool, ArrowRight, Mail, Lock, User, AlertCircle, Eye, EyeOff, ShieldAlert } from 'lucide-react';

export default function Auth({ onLogin, onRegister, onNavigate, error, loading, isPlaceholderEnv }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [formError, setFormError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError('');

    if (!email || !password) {
      setFormError('Please fill in all required fields.');
      return;
    }

    if (password.length < 6) {
      setFormError('Password must be at least 6 characters.');
      return;
    }

    if (isSignUp) {
      onRegister(email, password, fullName);
    } else {
      onLogin(email, password);
    }
  };

  const handleDemoMode = () => {
    onLogin("demo@scribbleai.com", "demopassword", true);
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center px-6 py-12" id="auth-page">
      {/* Dynamic background mesh */}
      <div className="pastel-bg-grid"></div>

      {/* Back to Home Link */}
      <button
        onClick={() => onNavigate('landing')}
        className="absolute top-8 left-8 flex items-center gap-2 text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors p-2 rounded-xl hover:bg-white/40 border border-transparent hover:border-slate-200/20"
        id="auth-back-btn"
      >
        <span className="text-md">&larr;</span> Back to Home
      </button>

      {/* Logo container */}
      <div className="flex items-center gap-2 font-extrabold text-2xl tracking-tight text-[var(--text-main)] mb-8" style={{ fontStyle: 'italic' }}>
        <span className="p-2.5 bg-white rounded-xl flex items-center justify-center shadow-md border border-slate-200/40 animate-float">
          <PenTool size={20} className="text-[var(--periwinkle-glow)]" />
        </span>
        Scribble<span className="text-[var(--periwinkle-glow)]">AI</span>
      </div>

      {/* Auth Card */}
      <div className="glass-panel w-full max-w-md p-8 md:p-10 bg-white/70 border-white/80 shadow-lg relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--butter-light)] opacity-40 rounded-full filter blur-2xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-[var(--periwinkle-light)] opacity-40 rounded-full filter blur-2xl pointer-events-none"></div>

        <h2 className="text-2xl font-extrabold text-[var(--text-main)] text-center mb-2">
          {isSignUp ? 'Create your Account' : 'Welcome Back'}
        </h2>
        <p className="text-xs text-[var(--text-muted)] text-center mb-8 leading-relaxed">
          {isSignUp ? 'Join ScribbleAI and sync your generated documents to the cloud.' : 'Log in to securely manage and export your handwriting sheets.'}
        </p>

        {/* Placeholder keys warning */}
        {isPlaceholderEnv && (
          <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex flex-col gap-1.5 text-left shadow-sm" id="auth-placeholder-warning">
            <span className="font-extrabold flex items-center gap-1.5 text-amber-900">
              <ShieldAlert size={16} className="text-amber-700 animate-pulse" />
              Supabase Placeholders Active
            </span>
            <span className="leading-relaxed">
              Your `.env` file is still using placeholder keys. Please open your project `.env` file and replace them with your actual Project URL and Anon Key from your Supabase Dashboard, then restart the server!
            </span>
          </div>
        )}

        {/* Errors display */}
        {(formError || error) && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-100 text-red-700 text-xs flex items-start gap-2.5 text-left" id="auth-error-alert">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{formError || error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* Full Name (Sign Up only) */}
          {isSignUp && (
            <div className="flex flex-col gap-1.5 text-left">
              <label className="text-[10px] font-black uppercase tracking-wider text-[var(--text-muted)]" htmlFor="name-input">Full Name</label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-light)]">
                  <User size={16} />
                </span>
                <input
                  id="name-input"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 rounded-xl bg-white border border-slate-200/50 text-[var(--text-main)] placeholder-[var(--text-light)] text-xs focus:outline-none focus:border-[var(--periwinkle-glow)] transition-colors focus:bg-white shadow-sm"
                  placeholder="John Doe"
                />
              </div>
            </div>
          )}

          {/* Email Address */}
          <div className="flex flex-col gap-1.5 text-left">
            <label className="text-[10px] font-black uppercase tracking-wider text-[var(--text-muted)]" htmlFor="email-input">Email Address</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-light)]">
                <Mail size={16} />
              </span>
              <input
                id="email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-11 pr-4 py-3 rounded-xl bg-white border border-slate-200/50 text-[var(--text-main)] placeholder-[var(--text-light)] text-xs focus:outline-none focus:border-[var(--periwinkle-glow)] transition-colors focus:bg-white shadow-sm"
                placeholder="you@example.com"
              />
            </div>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5 text-left">
            <div className="flex justify-between items-center">
              <label className="text-[10px] font-black uppercase tracking-wider text-[var(--text-muted)]" htmlFor="password-input">Password</label>
              {!isSignUp && (
                <button type="button" className="text-[10px] font-bold text-[var(--periwinkle-glow)] hover:underline bg-transparent border-none">
                  Forgot Password?
                </button>
              )}
            </div>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-light)]">
                <Lock size={16} />
              </span>
              <input
                id="password-input"
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-11 pr-11 py-3 rounded-xl bg-white border border-slate-200/50 text-[var(--text-main)] placeholder-[var(--text-light)] text-xs focus:outline-none focus:border-[var(--periwinkle-glow)] transition-colors focus:bg-white shadow-sm"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-light)] hover:text-[var(--text-muted)]"
                id="auth-toggle-pwd-btn"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
            id="auth-submit-btn"
          >
            {loading ? 'Processing...' : isSignUp ? 'Create Account' : 'Sign In'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="relative flex py-5 items-center">
          <div className="flex-grow border-t border-slate-200/40"></div>
          <span className="flex-shrink mx-4 text-[9px] font-black uppercase tracking-widest text-[var(--text-light)]">or</span>
          <div className="flex-grow border-t border-slate-200/40"></div>
        </div>

        {/* Demo Account Button for Sandbox Testing */}
        <button
          onClick={handleDemoMode}
          className="btn-secondary w-full"
          id="auth-demo-btn"
        >
          Explore Sandbox Mode (Without DB)
        </button>

        {/* Toggle link */}
        <div className="mt-6 text-center text-xs">
          <span className="text-[var(--text-muted)]">
            {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
          </span>
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setFormError('');
            }}
            className="font-bold text-[var(--periwinkle-glow)] hover:underline"
            id="auth-toggle-view-btn"
          >
            {isSignUp ? 'Log In' : 'Sign Up'}
          </button>
        </div>
      </div>
    </div>
  );
}
