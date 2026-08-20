import AsyncStorage from '@react-native-async-storage/async-storage';
import { supabase } from './client.js';
import { isSupabaseConfigured } from '../../config/env.js';

const LOCAL_SESSION_KEY = 'inkmimic_mobile_local_session';


export async function signInWithPassword(email, password) {
  if (!email || !password) {
    throw new Error('Please enter both email and password.');
  }

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        if (error.status === 400 || error.message?.toLowerCase().includes('invalid')) {
          throw error;
        }
        console.warn('Supabase auth returned error, trying local fallback:', error);
      } else if (data?.session) {
        await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(data.session));
        return data;
      }
    } catch (err) {
      if (err.message && !err.message.includes('fetch') && !err.message.includes('Network') && !err.message.includes('Failed to fetch')) {
        throw err;
      }
      console.warn('Supabase fetch failed, logging in via local session:', err);
    }
  }

  const localSession = {
    user: {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      email: email.trim(),
      user_metadata: { full_name: email.split('@')[0] },
    },
    access_token: 'local_token_' + Date.now(),
  };

  await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(localSession));
  return { session: localSession, user: localSession.user };
}

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
        await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(sess));
        return data;
      }
    } catch (err) {
      if (err.message && !err.message.includes('fetch') && !err.message.includes('Network') && !err.message.includes('Failed to fetch')) {
        throw err;
      }
      console.warn('Supabase fetch failed, registering via local session:', err);
    }
  }

  const localSession = {
    user: {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      email: email.trim(),
      user_metadata: { full_name: fullName || email.split('@')[0] },
    },
    access_token: 'local_token_' + Date.now(),
  };

  await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(localSession));
  return { session: localSession, user: localSession.user };
}

export async function signOut() {
  await AsyncStorage.removeItem(LOCAL_SESSION_KEY);
  if (isSupabaseConfigured && supabase) {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('Supabase sign out error:', e);
    }
  }
}

export async function getSession() {
  try {
    const local = await AsyncStorage.getItem(LOCAL_SESSION_KEY);
    if (local) return JSON.parse(local);
  } catch {}

  if (isSupabaseConfigured && supabase) {
    try {
      const { data, error } = await supabase.auth.getSession();
      if (!error && data?.session) {
        await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(data.session));
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
      const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
        if (session) {
          await AsyncStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify(session));
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

