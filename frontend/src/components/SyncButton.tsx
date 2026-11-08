import { useEffect, useId, useRef, useState } from 'react';
import { api, clearApiCache } from '../api/client';

function formatPhaseLabel(phase: string | null | undefined): string | null {
  if (!phase) return null;
  const labels: Record<string, string> = {
    starting: 'Starting',
    garmin: 'Garmin',
    activities: 'Activities',
    summaries: 'Workout summaries',
    wellness: 'Wellness',
    done: 'Done',
    error: 'Error',
  };
  return labels[phase] ?? phase;
}

function describeSyncStatus(status: {
  status: string;
  phase?: string | null;
  detail?: string | null;
}): string {
  const phase = formatPhaseLabel(status.phase);
  const detail = status.detail?.trim();
  if (phase && detail) return `${phase}: ${detail}`;
  if (detail) return detail;
  if (phase) return phase;
  return status.status;
}

const SYNC_TERMINAL = new Set(['success', 'failed', 'skipped', 'idle']);

async function waitForSyncCompletion(
  onUpdate: (line: string) => void,
  maxWaitMs = 30 * 60 * 1000,
): Promise<{ ok: boolean; line: string }> {
  const started = Date.now();
  while (Date.now() - started < maxWaitMs) {
    const st = await api.sync.status();
    const line = describeSyncStatus(st);
    onUpdate(line);
    if (SYNC_TERMINAL.has(st.status) && st.status !== 'idle') {
      return { ok: st.status === 'success', line };
    }
    if (st.status === 'idle' && st.finished_at) {
      return { ok: false, line };
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  return { ok: false, line: 'Timed out waiting for sync (30 min).' };
}

export function SyncButton() {
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [syncPassword, setSyncPassword] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [progressLine, setProgressLine] = useState<string | null>(null);

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
    setProgressLine(null);
  }

  async function handleSync() {
    if (!syncPassword.trim()) {
      setSyncError('Enter the sync password.');
      return;
    }
    setSyncing(true);
    setSyncMessage(null);
    setSyncError(null);
    setProgressLine('Starting sync…');
    try {
      const result = await api.report.sync(syncPassword);
      if (!result.ok) {
        setSyncError(result.message || 'Could not start sync.');
        return;
      }
      setSyncPassword('');
      const outcome = await waitForSyncCompletion(setProgressLine);
      if (outcome.ok) {
        setSyncMessage(outcome.line);
        clearApiCache();
      } else {
        setSyncError(outcome.line);
      }
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
        title="Sync Garmin data"
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
            <p className="sync-modal-hint">
              Runs the same Garmin pipeline on this machine as the weekly script (extract →
              summaries → wellness). Requires API `.env` with Garmin + GCP credentials.
            </p>
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
                {syncing ? 'Syncing…' : 'Run sync'}
              </button>
            </div>
            {syncing && progressLine ? (
              <p className="sync-modal-msg progress" aria-live="polite">
                {progressLine}
              </p>
            ) : null}
            {syncMessage ? <p className="sync-modal-msg ok">{syncMessage}</p> : null}
            {syncError ? <p className="sync-modal-msg err">{syncError}</p> : null}
            <p className="sync-modal-hint">
              Full logs: watch the terminal where uvicorn is running.
            </p>
          </div>
        </div>
      ) : null}
    </>
  );
}
