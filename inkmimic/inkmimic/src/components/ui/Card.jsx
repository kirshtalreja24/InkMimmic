export function Card({ tone = 'ink', className = '', children }) {
  const base = tone === 'paper' ? 'paper-panel' : 'ink-panel';
  return <div className={`${base} p-6 md:p-8 ${className}`}>{children}</div>;
}
