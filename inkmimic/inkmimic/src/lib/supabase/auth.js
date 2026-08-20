import { supabase } from './client.js';
import { isSupabaseConfigured } from '../../config/env.js';

const LOCAL_SESSION_KEY = 'inkmimic_local_session';


/**
 * Sign in with email and password.
 * Uses Supabase when available and reachable; falls back to local session.
 */
export async function signInWithPassword(email, password) {
  if (!email || !password) {
    throw new Error('Please enter both email and password.');
  }

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        // If it's a specific auth error (e.g. invalid password), throw it directly
        if (error.status === 400 || error.message?.toLowerCase().includes('invalid')) {
          throw error;
        }
        console.warn('Supabase auth returned error, trying local fallback:', error);
      } else if (data?.session) {
        localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(data.session));
        window.dispatchEvent(new Event('inkmimic_auth_changed'));
        return data;
      }
    } catch (err) {
      if (err.message && !err.message.includes('fetch') && !err.message.includes('NetworkError') && !err.message.includes('Failed to fetch')) {
        throw err;
      }
      console.warn('Supabase fetch failed, logging in via local session:', err);
    }
  }

  // Local authentication fallback
  const localSession = {
    user: {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      email: email.trim(),
      user_metadata: { full_name: email.split('@')[0] },
    },
    access_token: 'local_token_' + Date.now(),
  };

  localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(localSession));
  window.dispatchEvent(new Event('inkmimic_auth_changed'));
  return { session: localSession, user: localSession.user };
}

/**
 * Sign up with email, password, and full name.
 * Uses Supabase when available and reachable; falls back to local session.
 */
export async function signUpWithPassword(email, password, fullName) {
  if (!email || !password) {
    throw new Error('Please enter both email and password.');
  }

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName ?? '' },
        },
      });
      if (error) {
        if (error.status === 400 && !error.message?.includes('fetch')) {
          throw error;
        }
        console.warn('Supabase sign up error, trying local fallback:', error);
      } else if (data?.session || data?.user) {
        const sess = data.session || {
          user: data.user,
          access_token: 'supabase_token_' + Date.now(),
        };
        localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(sess));
        window.dispatchEvent(new Event('inkmimic_auth_changed'));
        return data;
      }
    } catch (err) {
      if (err.message && !err.message.includes('fetch') && !err.message.includes('NetworkError') && !err.message.includes('Failed to fetch')) {
        throw err;
      }
      console.warn('Supabase fetch failed, registering via local session:', err);
    }
  }

  // Local registration fallback
  const localSession = {
    user: {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      email: email.trim(),
      user_metadata: { full_name: fullName || email.split('@')[0] },
    },
    access_token: 'local_token_' + Date.now(),
  };

  localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(localSession));
  window.dispatchEvent(new Event('inkmimic_auth_changed'));
  return { session: localSession, user: localSession.user };
}

export async function signOut() {
  localStorage.removeItem(LOCAL_SESSION_KEY);
  if (isSupabaseConfigured && supabase) {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('Supabase sign out error:', e);
    }
  }
  window.dispatchEvent(new Event('inkmimic_auth_changed'));
}

export async function getSession() {
  try {
    const local = localStorage.getItem(LOCAL_SESSION_KEY);
    if (local) return JSON.parse(local);
  } catch {}

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase.auth.getSession();
      if (!error && data?.session) {
        localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(data.session));
        return data.session;
      }
    } catch (err) {
      console.warn('Supabase getSession failed:', err);
    }
  }

  return null;
}

export function onAuthStateChange(callback) {
  if (isSupabaseConfigured && supabase) {
    try {
      const { data } = supabase.auth.onAuthStateChange((event, session) => {
        if (session) {
          localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(session));
        }
        callback(event, session);
      });
      return data?.subscription;
    } catch (e) {
      console.warn('Supabase onAuthStateChange error:', e);
    }
  }
  return { unsubscribe: () => {} };
}

