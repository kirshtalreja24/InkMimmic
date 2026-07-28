import { useState } from 'react';
// Swap this single import to `../../packages/ai-core` once the real
// integration is implemented — see src/packages/README.md.
import { generateHandwrittenArtifact } from '../../packages/ai-prototype/index.js';
import { FileDropZone } from './FileDropZone.jsx';

const DEFAULT_PROMPT = 'Rewrite this page in a tidier version of the same handwriting.';

export function ChatPanel({ state, onStateChange, onArtifact }) {
  const [file, setFile] = useState(null);
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
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
      const artifact = await generateHandwrittenArtifact({ sampleFile: file, prompt });
      onArtifact(artifact);
      onStateChange('regenerated');
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
            What should Inkmimic do?
          </label>
          <textarea
            id="chat-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="field-input resize-none"
            placeholder="e.g. Make this note look neater, keep the same handwriting"
          />
          {!file && (
            <p className="mt-2 text-xs text-parchment/35">
              No sample uploaded — the prototype will just respond to your prompt as text.
            </p>
          )}
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