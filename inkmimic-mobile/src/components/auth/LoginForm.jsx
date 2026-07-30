import { useState } from 'react';
import { View, Text, TextInput, Pressable } from 'react-native';
import { signInWithPassword } from '../../lib/supabase/auth.js';
import { Button } from '../ui/Button.jsx';

export function LoginForm({ onSuccess, onSwitchToRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState('idle'); // idle | validating | error
  const [error, setError] = useState(null);

  async function handleSubmit() {
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
    <View className="gap-5">
      <View>
        <Text className="mb-2 font-body text-sm text-parchment/70">Email</Text>
        <TextInput
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="you@example.com"
          placeholderTextColor="rgba(246,241,230,0.3)"
          className="rounded-xl border border-royal-500/30 bg-ink-950/60 px-4 py-3 font-body text-parchment"
        />
      </View>

      <View>
        <Text className="mb-2 font-body text-sm text-parchment/70">Password</Text>
        <TextInput
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="••••••••"
          placeholderTextColor="rgba(246,241,230,0.3)"
          className="rounded-xl border border-royal-500/30 bg-ink-950/60 px-4 py-3 font-body text-parchment"
        />
      </View>

      {error && (
        <View className="rounded-lg bg-red-500/10 px-4 py-2">
          <Text className="font-body text-sm text-red-300">{error}</Text>
        </View>
      )}

      <Button
        label={status === 'validating' ? 'Signing in…' : 'Sign in'}
        loading={status === 'validating'}
        onPress={handleSubmit}
      />

      <View className="flex-row justify-center gap-1">
        <Text className="font-body text-sm text-parchment/50">New to Inkmimic?</Text>
        <Pressable onPress={onSwitchToRegister}>
          <Text className="font-bodySemibold text-sm text-gold-300">Create an account</Text>
        </Pressable>
      </View>
    </View>
  );
}
