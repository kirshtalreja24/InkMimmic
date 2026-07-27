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
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-royal-500/15 pb-6">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-parchment/40">Workspace</p>
        <h1 className="mt-1 font-display text-2xl text-parchment">
          Welcome back{userEmail ? `, ${userEmail.split('@')[0]}` : ''}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        <span className="flex items-center gap-2 rounded-full border border-royal-500/25 px-4 py-2 text-xs text-parchment/60">
          <StatusDot state={state} />
          {STATUS_COPY[state] ?? state}
        </span>
        <button onClick={onCloseSession} className="btn-outline !px-5 !py-2 text-sm">
          Close session
        </button>
      </div>
    </div>
  );
}

function StatusDot({ state }) {
  const color =
    state === 'error'
      ? 'bg-red-400'
      : state === 'regenerated'
        ? 'bg-emerald-400'
        : state === 'idle'
          ? 'bg-parchment/30'
          : 'bg-gold-400 animate-pulse';
  return <span className={`h-2 w-2 rounded-full ${color}`} />;
}
