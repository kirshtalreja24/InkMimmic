import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth.js';
import { Button } from '../ui/Button.jsx';

export function Navbar() {
  const { isAuthenticated, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="relative z-20">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 md:px-10">
        <Link to="/" className="flex items-center gap-2">
          <PenMark />
          <span className="font-display text-lg tracking-tight text-parchment">Inkmimic</span>
        </Link>

        <div className="hidden items-center gap-8 text-sm text-parchment/70 md:flex">
          <Link to="/about" className="transition-colors hover:text-gold-300">
            About us
          </Link>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <Button as={Link} to="/workspace" variant="gold" className="!px-5 !py-2 text-sm">
                Open workspace
              </Button>
              <button
                onClick={async () => {
                  await signOut();
                  navigate('/');
                }}
                className="text-sm text-parchment/50 transition-colors hover:text-parchment"
              >
                Sign out
              </button>
            </>
          ) : (
            <Button as={Link} to="/auth" variant="gold" className="!px-5 !py-2 text-sm">
              Get started
            </Button>
          )}
        </div>
      </nav>
    </header>
  );
}

function PenMark() {
  return (
    <svg viewBox="0 0 28 28" className="h-6 w-6" aria-hidden="true">
      <path
        d="M14 4 L22 14 L14 24 L6 14 Z"
        fill="none"
        stroke="#FFC93C"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="14" cy="14" r="1.8" fill="#FFC93C" />
    </svg>
  );
}
