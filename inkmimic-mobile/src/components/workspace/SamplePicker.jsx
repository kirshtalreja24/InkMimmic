import { useEffect } from 'react';
import { View, Text, Pressable, Image } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { useSamplePicker } from '../../hooks/useSamplePicker.js';

// Mobile has no drag-and-drop, so this is the equivalent intake surface:
// take a photo, pick from the library, or browse files. `asset`/`onClear`
// are controlled by the parent (ChatPanel) so the workspace state machine
// stays the single source of truth for what's currently attached.
export function SamplePicker({ onAsset, asset, onClear }) {
  const picker = useSamplePicker();

  useEffect(() => {
    if (picker.asset) onAsset?.(picker.asset);
  }, [picker.asset]);

  if (asset) {
    return (
      <View className="flex-row items-center justify-between gap-3 rounded-2xl border border-royal-500/20 bg-ink-900/70 px-4 py-3">
        <View className="flex-1 flex-row items-center gap-3">
          {asset.mimeType?.startsWith('image/') ? (
            <Image source={{ uri: asset.uri }} className="h-10 w-10 rounded-lg" />
          ) : (
            <FileGlyph />
          )}
          <Text numberOfLines={1} className="flex-1 font-body text-sm text-parchment">
            {asset.fileName ?? 'Sample attached'}
          </Text>
        </View>
        <Pressable
          onPress={() => {
            picker.reset();
            onClear?.();
          }}
        >
          <Text className="font-bodySemibold text-xs text-parchment/50">Replace</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View>
      <View className="items-center gap-4 rounded-2xl border-2 border-dashed border-royal-500/30 px-5 py-8">
        <FileGlyph large />
        <Text className="text-center font-body text-sm text-parchment/70">
          Add a handwriting sample
        </Text>

        <View className="flex-row flex-wrap justify-center gap-3">
          <PickerButton label="Take photo" onPress={picker.takePhoto} />
          <PickerButton label="Photo library" onPress={picker.pickFromLibrary} />
          <PickerButton label="Browse files" onPress={picker.pickDocument} />
        </View>
      </View>
      {picker.error && <Text className="mt-2 font-body text-xs text-red-300">{picker.error}</Text>}
    </View>
  );
}

function PickerButton({ label, onPress }) {
  return (
    <Pressable
      onPress={onPress}
      className="rounded-full border border-gold-400/40 px-3 py-2 active:opacity-70"
    >
      <Text className="font-bodySemibold text-xs text-gold-300">{label}</Text>
    </Pressable>
  );
}

function FileGlyph({ large = false }) {
  const size = large ? 40 : 24;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"
        stroke="#FFC93C"
        strokeWidth={1.6}
      />
      <Path d="M14 2v5h5" stroke="#FFC93C" strokeWidth={1.6} />
      <Path d="M8 14c1.5-2 3-2 4 0s2.5 2 4 0" stroke="#FFC93C" strokeWidth={1.4} strokeLinecap="round" />
    </Svg>
  );
}
