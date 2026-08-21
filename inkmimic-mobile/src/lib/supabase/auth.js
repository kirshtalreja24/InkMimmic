import AsyncStorage from '@react-native-async-storage/async-storage';
import { createSessionModule } from 'inkmimic-core';
import { supabase } from './client.js';
import { isSupabaseConfigured } from '../../config/env.js';

// AsyncStorage's getItem/setItem/removeItem already match the shape
// createSessionModule expects, so it's passed straight through. No
// `notify` — mobile's AuthContext detects session changes on its own
// (see its isMounted-guarded getSession() call), unlike web which needs
// a same-tab event to notice a session change made elsewhere.
export const { signInWithPassword, signUpWithPassword, signOut, getSession, onAuthStateChange } =
  createSessionModule({
    supabase,
    isSupabaseConfigured,
    storage: AsyncStorage,
    localSessionKey: 'inkmimic_mobile_local_session',
  });
