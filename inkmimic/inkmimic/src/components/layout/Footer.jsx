import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="border-t border-royal-500/15 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-parchment/40 md:flex-row md:px-10">
        <p>&copy; {new Date().getFullYear()} Inkmimic. Every page, in your own hand.</p>
        <div className="flex gap-6">
          <Link to="/about" className="transition-colors hover:text-gold-300">
            About us
          </Link>
          <Link to="/auth" className="transition-colors hover:text-gold-300">
            Get started
          </Link>
        </div>
      </div>
    </footer>
  );
}
