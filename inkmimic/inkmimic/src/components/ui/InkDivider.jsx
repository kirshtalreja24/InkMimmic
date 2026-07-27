export function InkDivider({ className = '' }) {
  return (
    <svg
      viewBox="0 0 240 16"
      className={`h-4 w-40 ${className}`}
      aria-hidden="true"
      fill="none"
    >
      <path
        d="M2 8c20-6 40-6 60 0s40 6 60 0 40-6 60 0 40 6 56 0"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
