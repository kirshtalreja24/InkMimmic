// The signature element of the site: the wordmark writes itself in on load,
// a small pen nib gliding left to right while the word reveals underneath it,
// like watching someone actually sign the page.
export function InkWordmark({ className = '' }) {
  return (
    <span className={`relative inline-block ${className}`}>
      <span
        className="font-script text-gold-400 [clip-path:inset(0_100%_0_0)] animate-reveal-ink inline-block"
        style={{ animationDelay: '0.2s' }}
      >
        Inkmimic
      </span>
      <svg
        viewBox="0 0 28 28"
        aria-hidden="true"
        className="absolute -top-2 h-5 w-5 md:h-7 md:w-7 md:-top-3 opacity-0 animate-pen-glide"
        style={{ animationDelay: '0.2s' }}
      >
        <path
          d="M14 4 L22 14 L14 24 L6 14 Z"
          fill="none"
          stroke="#FFC93C"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle cx="14" cy="14" r="1.6" fill="#FFC93C" />
      </svg>
    </span>
  );
}
