import { View } from 'react-native';

export function Card({ tone = 'ink', className = '', children }) {
  const base =
    tone === 'paper'
      ? 'bg-parchment rounded-2xl'
      : 'bg-ink-900/70 border border-royal-500/20 rounded-2xl';
  return <View className={`${base} p-6 ${className}`}>{children}</View>;
}
