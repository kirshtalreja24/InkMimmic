import { useState } from 'react';
import { View, Text, TextInput } from 'react-native';
import { generateHandwrittenArtifact } from '../../packages/ai-core/index.js';
import { uploadHandwritingSample } from '../../lib/supabase/storage.js';
import { saveArtifact } from '../../lib/supabase/persistence.js';
import { useAuth } from '../../hooks/useAuth.js';
import { SamplePicker } from './SamplePicker.jsx';
import { Button } from '../ui/Button.jsx';

const DEFAULT_PROMPT = 'Write down notes in realistic natural handwriting.';

export function ChatPanel({ state, onStateChange, onArtifact }) {
  const { user } = useAuth();
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

      // Best-effort persistence: a failed save shouldn't hide a successful
      // generation, so this never affects the state shown above.
      if (user?.id) {
        Promise.resolve()
          .then(async () => {
            if (asset) await uploadHandwritingSample(user.id, asset);
            await saveArtifact({
              userId: user.id,
              artifactId: artifact.id,
              dataUri: artifact.content,
              prompt,
            });
          })
          .catch((persistErr) => {
            console.warn('Failed to save artifact to Supabase:', persistErr);
          });
      }
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
          Text to convert to handwriting
        </Text>
        <TextInput
          value={prompt}
          onChangeText={setPrompt}
          multiline
          numberOfLines={4}
          placeholder="Type or paste the text you want handwritten..."
          placeholderTextColor="rgba(246,241,230,0.3)"
          className="rounded-xl border border-royal-500/30 bg-ink-950/60 px-4 py-3 font-body text-parchment"
          style={{ minHeight: 96, textAlignVertical: 'top' }}
        />
        {!asset ? (
          <Text className="mt-2 font-body text-xs text-parchment/35">
            No sample attached — the model will use its classic handwriting style reference.
          </Text>
        ) : (
          <Text className="mt-2 font-body text-xs text-gold-300/80">
            Sample attached — the model will mimic your sample's handwriting style.
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
