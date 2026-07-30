import { View, Text, Pressable } from 'react-native';

const STATUS_COPY = {
  idle: 'Waiting for a sample',
  fileDropped: 'Sample ready',
  sending: 'Sending to the model…',
  awaiting: 'Generating your page…',
  regenerated: 'New artifact ready',
  error: 'Something went wrong',
};

export function SessionHeader({ userEmail, state, onCloseSession }) {
  return (
    <View className="gap-4 border-b border-royal-500/15 pb-6">
      <View>
        <Text className="font-body text-xs uppercase tracking-widest text-parchment/40">
          Workspace
        </Text>
        <Text className="mt-1 font-display text-2xl text-parchment">
          Welcome back{userEmail ? `, ${userEmail.split('@')[0]}` : ''}
        </Text>
      </View>

      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center gap-2 rounded-full border border-royal-500/25 px-4 py-2">
          <StatusDot state={state} />
          <Text className="font-body text-xs text-parchment/60">
            {STATUS_COPY[state] ?? state}
          </Text>
        </View>
        <Pressable
          onPress={onCloseSession}
          className="rounded-full border border-parchment/30 px-4 py-2"
        >
          <Text className="font-bodySemibold text-xs text-parchment">Close session</Text>
        </Pressable>
      </View>
    </View>
  );
}

function StatusDot({ state }) {
  const color =
    state === 'error'
      ? '#F87171'
      : state === 'regenerated'
        ? '#34D399'
        : state === 'idle'
          ? 'rgba(246,241,230,0.3)'
          : '#FFC93C';
  return <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />;
}
