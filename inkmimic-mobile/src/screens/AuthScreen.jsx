import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, View, Text } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { LoginForm } from '../components/auth/LoginForm.jsx';
import { RegisterForm } from '../components/auth/RegisterForm.jsx';
import { isSupabaseConfigured } from '../config/env.js';

export default function AuthScreen() {
  const [mode, setMode] = useState('login');

  return (
    <LinearGradient colors={['#080B22', '#0C1030', '#10143B']} className="flex-1">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        className="flex-1"
      >
        <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center' }} className="px-6">
          <View className="rounded-2xl border border-royal-500/20 bg-ink-900/70 p-8">
            <Text className="font-script text-xl text-royal-400">
              {mode === 'login' ? 'Welcome back' : 'Join Inkmimic'}
            </Text>
            <Text className="mt-1 font-display text-2xl text-parchment">
              {mode === 'login' ? 'Sign in to your workspace' : 'Create your account'}
            </Text>

            {!isSupabaseConfigured && (
              <View className="mt-4 rounded-lg bg-gold-400/10 px-4 py-3">
                <Text className="font-body text-xs leading-relaxed text-gold-200">
                  Supabase isn't configured yet. Add EXPO_PUBLIC_SUPABASE_URL and
                  EXPO_PUBLIC_SUPABASE_ANON_KEY to your .env file to enable real authentication.
                </Text>
              </View>
            )}

            {/*
              No onSuccess navigation call here on purpose: once Supabase
              confirms sign-in/sign-up, AuthContext's onAuthStateChange
              listener updates isAuthenticated, RootNavigator swaps to the
              signed-in navigator tree, and Workspace becomes the screen
              automatically. Navigating manually here would race that
              state update and fail, since Workspace doesn't exist in this
              tree yet at the moment of a successful login.
            */}
            <View className="mt-6">
              {mode === 'login' ? (
                <LoginForm onSwitchToRegister={() => setMode('register')} />
              ) : (
                <RegisterForm onSwitchToLogin={() => setMode('login')} />
              )}
            </View>

            <View className="mt-6 border-t border-royal-500/15 pt-5 items-center">
              <Text
                onPress={async () => {
                  const { signInWithPassword } = await import('../lib/supabase/auth.js');
                  await signInWithPassword('guest@inkmimic.local', 'password123');
                }}
                className="font-bodySemibold text-xs text-gold-300/80 active:opacity-70"
              >
                Continue as Guest (Skip Sign In) →
              </Text>
            </View>

          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}