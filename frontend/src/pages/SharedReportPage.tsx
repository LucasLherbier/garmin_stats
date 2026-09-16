import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiUrl } from '../api/client';

export function SharedReportPage() {
  const { token } = useParams<{ token: string }>();
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    async function load() {
      setError(null);
      setHtml(null);
      try {
        const res = await fetch(apiUrl(`/report/r/${token}`));
        if (!res.ok) {
          throw new Error(res.status === 404 ? 'Report not found or link expired.' : 'Failed to load report.');
        }
        const text = await res.text();
        if (!cancelled) setHtml(text);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load report.');
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error) {
    return (
      <main className="page">
        <p className="error">{error}</p>
        <Link to="/" className="back-link">← Home</Link>
      </main>
    );
  }

  if (!html) {
    return <main className="page"><div className="loading">Loading report…</div></main>;
  }

  return (
    <iframe
      title="Activity report"
      srcDoc={html}
      style={{ width: '100%', height: '100dvh', border: 0, display: 'block' }}
    />
  );
}
