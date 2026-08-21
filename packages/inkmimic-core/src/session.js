// Session module shared by the Inkmimic web and mobile apps.
//
// Both apps hand-implemented the same signIn/signUp/signOut/getSession
// state machine — Supabase when configured and reachable, falling back to
// a locally-fabricated session otherwise (see Local mode in CONTEXT.md).
// The only thing that ever varied between the two copies was the storage
// adapter (browser localStorage vs React Native's AsyncStorage) and an
// optional post-mutation notification hook (web needs one to tell other
// parts of the same tab a session changed; mobile doesn't). Everything
// else is the identical control flow, now written once.
//
// `storage` just needs getItem/setItem/removeItem — browser localStorage
// and AsyncStorage both already match this shape, so callers can pass
// either directly.

const NETWORK_ERROR_HINTS = ['fetch', 'Network', 'Failed to fetch'];

function isNetworkError(err) {
  return Boolean(err?.message) && NETWORK_ERROR_HINTS.some((hint) => err.message.includes(hint));
}

function makeLocalSession(email, fullName) {
  return {
    user: {
      id: 'usr_' + Math.random().toString(36).substring(2, 9),
      email: email.trim(),
      user_metadata: { full_name: fullName || email.split('@')[0] },
    },
    access_token: 'local_token_' + Date.now(),
  };
}

/**
 * @param {object} params
 * @param {import('@supabase/supabase-js').SupabaseClient | null} params.supabase
 * @param {boolean} params.isSupabaseConfigured
 * @param {{ getItem: Function, setItem: Function, removeItem: Function }} params.storage
 * @param {string} params.localSessionKey - keep this distinct per app; the two apps
 *   intentionally never share a stored session.
 * @param {() => void} [params.notify] - called after every local session mutation.
 */
export function createSessionModule({
  supabase,
  isSupabaseConfigured,
  storage,
  localSessionKey,
  notify = () => {},
}) {
  async function persistLocal(session) {
    await storage.setItem(localSessionKey, JSON.stringify(session));
    notify();
  }

  async function signInWithPassword(email, password) {
    if (!email || !password) {
      throw new Error('Please enter both email and password.');
    }

    if (isSupabaseConfigured && supabase) {
      try {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) {
          // A specific auth error (e.g. invalid password) should surface directly.
          if (error.status === 400 || error.message?.toLowerCase().includes('invalid')) {
            throw error;
          }
          console.warn('Supabase auth returned error, trying local fallback:', error);
        } else if (data?.session) {
          await persistLocal(data.session);
          return data;
        }
      } catch (err) {
        if (!isNetworkError(err)) {
          throw err;
        }
        console.warn('Supabase fetch failed, logging in via local session:', err);
      }
    }

    const localSession = makeLocalSession(email);
    await persistLocal(localSession);
    return { session: localSession, user: localSession.user };
  }

  async function signUpWithPassword(email, password, fullName) {
    if (!email || !password) {
      throw new Error('Please enter both email and password.');
    }

    if (isSupabaseConfigured && supabase) {
      try {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName ?? '' } },
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
          await persistLocal(sess);
          return data;
        }
      } catch (err) {
        if (!isNetworkError(err)) {
          throw err;
        }
        console.warn('Supabase fetch failed, registering via local session:', err);
      }
    }

    const localSession = makeLocalSession(email, fullName);
    await persistLocal(localSession);
    return { session: localSession, user: localSession.user };
  }

  async function signOut() {
    await storage.removeItem(localSessionKey);
    if (isSupabaseConfigured && supabase) {
      try {
        await supabase.auth.signOut();
      } catch (e) {
        console.warn('Supabase sign out error:', e);
      }
    }
    notify();
  }

  async function getSession() {
    try {
      const local = await storage.getItem(localSessionKey);
      if (local) return JSON.parse(local);
    } catch {
      // fall through to Supabase
    }

    if (isSupabaseConfigured && supabase) {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (!error && data?.session) {
          await storage.setItem(localSessionKey, JSON.stringify(data.session));
          return data.session;
        }
      } catch (err) {
        console.warn('Supabase getSession failed:', err);
      }
    }

    return null;
  }

  function onAuthStateChange(callback) {
    if (isSupabaseConfigured && supabase) {
      try {
        const { data } = supabase.auth.onAuthStateChange(async (event, session) => {
          if (session) {
            await storage.setItem(localSessionKey, JSON.stringify(session));
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

  return { signInWithPassword, signUpWithPassword, signOut, getSession, onAuthStateChange };
}
