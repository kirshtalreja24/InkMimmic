import { Pressable, Text, ActivityIndicator } from 'react-native';

export function Button({ variant = 'gold', label, onPress, disabled, loading, className = '' }) {
  const isGold = variant === 'gold';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      className={`flex-row items-center justify-center gap-2 rounded-full px-6 py-3.5 active:opacity-80
        ${isGold ? 'bg-gold-400' : 'border border-parchment/30'}
        ${disabled || loading ? 'opacity-40' : ''} ${className}`}
    >
      {loading && (
        <ActivityIndicator size="small" color={isGold ? '#080B22' : '#F6F1E6'} />
      )}
      <Text
        className={`font-bodySemibold text-base ${isGold ? 'text-ink-950' : 'text-parchment'}`}
      >
        {label}
      </Text>
    </Pressable>
  );
}
