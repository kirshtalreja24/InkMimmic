import { useState } from 'react';
import { generateHandwrittenArtifact } from '../../packages/ai-core/index.js';
import { uploadHandwritingSample } from '../../lib/supabase/storage.js';
import { saveArtifact } from '../../lib/supabase/persistence.js';
import { useAuth } from '../../hooks/useAuth.js';
import { FileDropZone } from './FileDropZone.jsx';

const DEFAULT_PROMPT = 'Write down notes in realistic natural handwriting.';

export function ChatPanel({ state, onStateChange, onArtifact }) {
  const { user } = useAuth();
  const [file, setFile] = useState(null);
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [paper, setPaper] = useState('white');
  const [inkColor, setInkColor] = useState('#1a1a2e');
  const [errorMessage, setErrorMessage] = useState(null);

  function handleFile(newFile) {
    setFile(newFile);
    onStateChange('fileDropped');
  }

  function handleClear() {
    setFile(null);
    onStateChange('idle');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;

    setErrorMessage(null);
    onStateChange('sending');

    try {
      onStateChange('awaiting');
      const artifact = await generateHandwrittenArtifact({
        sampleFile: file,
        prompt,
        paper,
        inkColor,
      });
      onArtifact(artifact);
      onStateChange('regenerated');

      // Best-effort persistence: a failed save shouldn't hide a successful
      // generation, so this never affects the state shown above.
      if (user?.id) {
        Promise.resolve()
          .then(async () => {
            if (file) await uploadHandwritingSample(user.id, file);
            await saveArtifact({
              userId: user.id,
              artifactId: artifact.id,
              dataUri: artifact.content,
              prompt,
              paper,
              inkColor,
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
    <div className="flex h-full flex-col gap-5">
      <FileDropZone file={file} onFile={handleFile} onClear={handleClear} />

      <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
        <div>
          <label className="field-label" htmlFor="chat-prompt">
            Text to write in handwriting
          </label>
          <textarea
            id="chat-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="field-input resize-none"
            placeholder="Type or paste the text you want converted to handwriting..."
          />
          {!file ? (
            <p className="mt-2 text-xs text-parchment/50">
              No sample uploaded — the model will use its classic handwriting style reference.
            </p>
          ) : (
            <p className="mt-2 text-xs text-gold-300/80">
              Sample attached — the model will mimic your sample's handwriting style.
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-parchment/60" htmlFor="paper-select">Paper Style</label>
            <select
              id="paper-select"
              value={paper}
              onChange={(e) => setPaper(e.target.value)}
              className="mt-1 w-full rounded-lg border border-royal-500/30 bg-ink-900 px-3 py-1.5 text-xs text-parchment"
            >
              <option value="white">Plain White</option>
              <option value="ruled">Ruled Lines</option>
              <option value="graph">Graph Paper</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-parchment/60" htmlFor="ink-select">Ink Color</label>
            <select
              id="ink-select"
              value={inkColor}
              onChange={(e) => setInkColor(e.target.value)}
              className="mt-1 w-full rounded-lg border border-royal-500/30 bg-ink-900 px-3 py-1.5 text-xs text-parchment"
            >
              <option value="#1a1a2e">Deep Ink (#1a1a2e)</option>
              <option value="#0c2340">Navy Blue (#0c2340)</option>
              <option value="#111111">Black Ink (#111111)</option>
            </select>
          </div>
        </div>


        {errorMessage && (
          <p role="alert" className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {errorMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={!prompt.trim() || isBusy}
          className="btn-gold mt-auto w-full disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isBusy ? <Spinner label={state === 'sending' ? 'Sending…' : 'Generating…'} /> : 'Generate artifact'}
        </button>
      </form>
    </div>
  );
}

function Spinner({ label }) {
  return (
    <span className="flex items-center gap-2">
      <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" opacity="0.25" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      {label}
    </span>
  );
}