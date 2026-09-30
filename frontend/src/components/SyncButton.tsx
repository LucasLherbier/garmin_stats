import { useEffect, useId, useRef, useState } from 'react';
import { api } from '../api/client';

export function SyncButton() {
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [syncPassword, setSyncPassword] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => inputRef.current?.focus(), 50);
    return () => window.clearTimeout(t);
  }, [open]);

  function close() {
    if (syncing) return;
    setOpen(false);
    setSyncError(null);
    setSyncMessage(null);
  }

  async function handleSync() {
    if (!syncPassword.trim()) {
      setSyncError('Enter the sync password.');
      return;
    }
    setSyncing(true);
    setSyncMessage(null);
    setSyncError(null);
    try {
      const result = await api.report.sync(syncPassword);
      setSyncMessage(result.message);
      if (!result.ok) setSyncError(result.message);
      else setSyncPassword('');
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : 'Sync failed');
    } finally {
      setSyncing(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="sync-top-btn"
        aria-label="Sync Garmin data"
        title="Upload / Sync"
        onClick={() => setOpen(true)}
      >
        <svg viewBox="0 0 24 24" aria-hidden>
          <path d="M12 3v12" />
          <path d="m8 11 4 4 4-4" />
          <path d="M4 14v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4" />
        </svg>
      </button>

      {open ? (
        <div className="sync-modal-backdrop" role="presentation" onClick={close}>
          <div
            className="sync-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id={titleId} className="sync-modal-title">
              Sync data
            </h2>
            <p className="sync-modal-hint">Weekly Garmin extract via GitHub Actions.</p>
            <input
              ref={inputRef}
              type="password"
              className="form-field"
              placeholder="Sync password"
              value={syncPassword}
              autoComplete="current-password"
              disabled={syncing}
              onChange={(e) => setSyncPassword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleSync();
                if (e.key === 'Escape') close();
              }}
            />
            <div className="sync-modal-actions">
              <button type="button" className="btn-ghost" disabled={syncing} onClick={close}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary sync-modal-submit"
                disabled={syncing || !syncPassword.trim()}
                onClick={() => void handleSync()}
              >
                {syncing ? 'Starting…' : 'Upload / Sync'}
              </button>
            </div>
            {syncMessage ? <p className="sync-modal-msg ok">{syncMessage}</p> : null}
            {syncError ? <p className="sync-modal-msg err">{syncError}</p> : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
