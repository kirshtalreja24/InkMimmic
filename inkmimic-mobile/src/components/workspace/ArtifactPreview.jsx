import { View, Text, Pressable, ScrollView } from 'react-native';
import Svg, { Rect, Path } from 'react-native-svg';

export function ArtifactPreview({ artifact, onNewRequest }) {
  if (!artifact) {
    return (
      <View className="items-center justify-center gap-3 rounded-2xl border border-royal-500/15 px-8 py-14">
        <Svg width={40} height={40} viewBox="0 0 48 48" fill="none">
          <Rect x="8" y="6" width="32" height="36" rx="3" stroke="#5B79E8" strokeOpacity={0.5} strokeWidth={1.6} />
          <Path
            d="M15 16h18M15 23h18M15 30h11"
            stroke="#5B79E8"
            strokeOpacity={0.5}
            strokeWidth={1.4}
            strokeLinecap="round"
          />
        </Svg>
        <Text className="max-w-xs text-center font-body text-sm text-parchment/40">
          Your regenerated page appears here once the model responds.
        </Text>
      </View>
    );
  }

  return (
    <View className="flex-1 rounded-2xl bg-parchment p-6">
      <View className="mb-4 flex-row items-center justify-between">
        <Text className="font-script text-2xl text-royal-700">Your new artifact</Text>
        <Pressable
          onPress={onNewRequest}
          className="rounded-full border border-ink-950/15 px-4 py-1.5"
        >
          <Text className="font-bodySemibold text-xs text-ink-950/60">Upload another</Text>
        </Pressable>
      </View>
      <ScrollView className="flex-1">
        <Text className="font-body text-[15px] leading-relaxed text-ink-950/85">
          {artifact.content}
        </Text>
      </ScrollView>
    </View>
  );
}
