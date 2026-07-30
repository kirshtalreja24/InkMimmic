import { useState } from 'react';
import { View, Text, TextInput } from 'react-native';
// Swap this single import to `../../packages/ai-core` once the real
// integration is implemented — see src/packages/README.md.
import { generateHandwrittenArtifact } from '../../packages/ai-prototype/index.js';
import { SamplePicker } from './SamplePicker.jsx';
import { Button } from '../ui/Button.jsx';

const DEFAULT_PROMPT = 'Rewrite this page in a tidier version of the same handwriting.';

export function ChatPanel({ state, onStateChange, onArtifact }) {
  const [asset, setAsset] = useState(null);
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [errorMessage, setErrorMessage] = useState(null);

  function handleAsset(newAsset) {
    setAsset(newAsset);
    onStateChange('fileDropped');
  }

  function handleClear() {
    setAsset(null);
    onStateChange('idle');
  }

  async function handleSubmit() {
    if (!prompt.trim()) return;
    setErrorMessage(null);
    onStateChange('sending');
    try {
      onStateChange('awaiting');
      const artifact = await generateHandwrittenArtifact({ sampleAsset: asset, prompt });
      onArtifact(artifact);
      onStateChange('regenerated');
    } catch (err) {
      setErrorMessage(err.message ?? 'The model timed out. Try again.');
      onStateChange('error');
    }
  }

  const isBusy = state === 'sending' || state === 'awaiting';

  return (
    <View className="gap-5">
      <SamplePicker asset={asset} onAsset={handleAsset} onClear={handleClear} />

      <View>
        <Text className="mb-2 font-body text-sm text-parchment/70">
          What should Inkmimic do?
        </Text>
        <TextInput
          value={prompt}
          onChangeText={setPrompt}
          multiline
          numberOfLines={4}
          placeholder="e.g. Make this note look neater, keep the same handwriting"
          placeholderTextColor="rgba(246,241,230,0.3)"
          className="rounded-xl border border-royal-500/30 bg-ink-950/60 px-4 py-3 font-body text-parchment"
          style={{ minHeight: 96, textAlignVertical: 'top' }}
        />
        {!asset && (
          <Text className="mt-2 font-body text-xs text-parchment/35">
            No sample attached — the prototype will just respond to your prompt as text.
          </Text>
        )}
      </View>

      {errorMessage && (
        <View className="rounded-lg bg-red-500/10 px-4 py-2">
          <Text className="font-body text-sm text-red-300">{errorMessage}</Text>
        </View>
      )}

      <Button
        label={isBusy ? (state === 'sending' ? 'Sending…' : 'Generating…') : 'Generate artifact'}
        loading={isBusy}
        disabled={!prompt.trim() || isBusy}
        onPress={handleSubmit}
      />
    </View>
  );
}
