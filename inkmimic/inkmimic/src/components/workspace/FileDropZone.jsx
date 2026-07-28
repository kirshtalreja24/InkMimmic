import { useRef } from 'react';
import { useFileDrop } from '../../hooks/useFileDrop.js';

export function FileDropZone({ onFile, file, onClear }) {
  const inputRef = useRef(null);
  const { isDragging, error, handlers, onBrowse } = useFileDrop({ onFile });

  if (file) {
    return (
      <div className="ink-panel flex items-center justify-between gap-4 px-5 py-4">
        <div className="flex items-center gap-3 overflow-hidden">
          <FileGlyph />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-parchment">{file.name}</p>
            <p className="text-xs text-parchment/40">{(file.size / 1024).toFixed(0)} KB · ready</p>
          </div>
        </div>
        <button
          onClick={onClear}
          className="shrink-0 text-xs font-semibold text-parchment/50 hover:text-gold-300"
        >
          Replace
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        {...handlers}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors
          ${isDragging ? 'border-gold-400 bg-gold-400/5' : 'border-royal-500/30 hover:border-royal-400/50'}`}
      >
        <FileGlyph large />
        <p className="text-sm text-parchment/70">
          <span className="font-semibold text-gold-300">Drop a handwriting sample</span> or click to
          browse
        </p>
        <p className="text-xs text-parchment/35">PNG, JPG, WEBP, or PDF</p>
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,application/pdf"
        onChange={onBrowse}
        className="hidden"
      />
    </div>
  );
}

function FileGlyph({ large = false }) {
  const size = large ? 'h-10 w-10' : 'h-6 w-6';
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`${size} text-gold-400`} aria-hidden="true">
      <path
        d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path d="M14 2v5h5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8 14c1.5-2 3-2 4 0s2.5 2 4 0" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
