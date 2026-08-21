import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth.js';
import { listArtifacts, getArtifactUrl } from '../lib/supabase/persistence.js';
import { isSupabaseConfigured } from '../config/env.js';

export default function GalleryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isSupabaseConfigured || !user?.id) {
        setLoading(false);
        return;
      }
      try {
        const rows = await listArtifacts(user.id);
        const withUrls = await Promise.all(
          rows.map(async (row) => ({
            ...row,
            url: await getArtifactUrl(row.storage_path).catch(() => null),
          }))
        );
        if (!cancelled) setItems(withUrls);
      } catch (err) {
        if (!cancelled) setError(err.message ?? 'Failed to load your past generations.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  return (
    <div className="min-h-screen bg-ink-950 bg-ink-grain px-6 py-10 md:px-10">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-royal-500/15 pb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-parchment/40">Your history</p>
            <h1 className="mt-1 font-display text-2xl text-parchment">Past generations</h1>
          </div>
          <Link to="/workspace" className="btn-outline !px-5 !py-2 text-sm">
            Back to Workspace
          </Link>
        </div>

        <div className="mt-8">
          {!isSupabaseConfigured ? (
            <EmptyState text="Past generations aren't saved in local mode — connect a real Supabase project to enable this." />
          ) : loading ? (
            <p className="text-sm text-parchment/50">Loading…</p>
          ) : error ? (
            <p className="text-sm text-red-300">{error}</p>
          ) : items.length === 0 ? (
            <EmptyState text="Nothing here yet — generate a page in the Workspace and it'll show up here." />
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <GalleryCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GalleryCard({ item }) {
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    if (!item.url || downloading) return;
    setDownloading(true);
    try {
      // item.url is a signed Supabase Storage URL (cross-origin), so a
      // plain <a download> won't reliably force a download in most
      // browsers -- fetch it to a blob and download that instead, which
      // always honors `download` since blob: URLs are same-origin.
      const res = await fetch(item.url);
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = `inkmimic_${item.id}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(objectUrl);
    } catch {
      // best-effort -- the img preview already tells the user the file exists
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="ink-panel flex flex-col overflow-hidden p-4">
      <div
        className="flex flex-1 items-center justify-center overflow-hidden rounded-lg border border-ink-950/10 bg-white/60"
        style={{ minHeight: 180 }}
      >
        {item.url ? (
          <img src={item.url} alt={item.prompt} className="max-h-56 w-full object-contain" />
        ) : (
          <span className="text-xs text-parchment/40">Preview unavailable</span>
        )}
      </div>
      <p className="mt-3 line-clamp-2 text-sm text-parchment/80">{item.prompt}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-xs text-parchment/40">
          {new Date(item.created_at).toLocaleString()}
          {item.paper ? ` · ${item.paper} paper` : ''}
        </p>
        {item.url && (
          <button
            type="button"
            onClick={handleDownload}
            disabled={downloading}
            className="shrink-0 rounded-full border border-gold-300/40 px-3 py-1 text-xs font-semibold text-gold-300/80 hover:text-gold-300 hover:border-gold-300 disabled:opacity-40"
          >
            {downloading ? 'Downloading…' : 'Download'}
          </button>
        )}
      </div>
    </div>
  );
}

function EmptyState({ text }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-royal-500/15 px-8 py-16 text-center">
      <p className="max-w-sm text-sm text-parchment/40">{text}</p>
    </div>
  );
}
