export function ArtifactPreview({ artifact, onNewRequest }) {
  if (!artifact) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 rounded-2xl border border-royal-500/15 px-8 py-16 text-center">
        <EmptyGlyph />
        <p className="max-w-xs text-sm text-parchment/40">
          Your generated handwriting page appears here once the model responds.
        </p>
      </div>
    );
  }

  const isImage = artifact.kind === 'image' || artifact.content?.startsWith('data:image/');

  function handleDownload() {
    if (!artifact.content) return;
    const link = document.createElement('a');
    link.href = artifact.content;
    link.download = `inkmimic_handwriting_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="paper-panel flex h-full flex-col p-6 md:p-8">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <span className="font-script text-2xl text-royal-700">Handwritten Page</span>
          {artifact.note && (
            <p className="text-xs text-ink-950/60 mt-0.5">{artifact.note}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isImage && (
            <button
              onClick={handleDownload}
              className="rounded-full bg-royal-700 px-4 py-1.5 text-xs font-semibold text-parchment shadow hover:bg-royal-800 transition"
            >
              Download PNG
            </button>
          )}
          <button
            onClick={onNewRequest}
            className="rounded-full border border-ink-950/15 px-4 py-1.5 text-xs font-semibold text-ink-950/60 hover:border-royal-500 hover:text-royal-700"
          >
            Create another
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto rounded-xl bg-white/60 p-4 border border-ink-950/10 flex items-center justify-center">
        {isImage ? (
          <img
            src={artifact.content}
            alt="Generated Handwriting"
            className="max-h-full max-w-full rounded shadow-sm object-contain"
          />
        ) : (
          <div className="w-full whitespace-pre-wrap font-body text-[15px] leading-relaxed text-ink-950/85">
            {artifact.content}
          </div>
        )}
      </div>
    </div>
  );
}


function EmptyGlyph() {
  return (
    <svg viewBox="0 0 48 48" className="h-10 w-10 text-royal-400/50" fill="none" aria-hidden="true">
      <rect x="8" y="6" width="32" height="36" rx="3" stroke="currentColor" strokeWidth="1.6" />
      <path d="M15 16h18M15 23h18M15 30h11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
