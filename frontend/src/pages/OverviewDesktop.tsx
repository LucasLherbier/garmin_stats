import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { HomeTrainingExplorer } from '../components/HomeTrainingExplorer';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { SyncButton } from '../components/SyncButton';
import { TrainingYtdHeatmap } from '../components/TrainingYtdHeatmap';
import type { HomeYtdResponse } from '../types';
import { formatDelta, formatDistance, formatDuration, formatDurationDelta } from '../utils/format';
import { toneFromSport } from '../utils/tones';

/**
 * Desktop Home (>= 1024 px). Same data, same sections as the mobile
 * OverviewPage — composed for a wide screen.
 */

export function OverviewDesktop() {
  const [loadingTotals, setLoadingTotals] = useState(true);
  const [ytdError, setYtdError] = useState<string | null>(null);
  const [totals, setTotals] = useState<Awaited<ReturnType<typeof api.overview.weeklyTotals>> | null>(
    null,
  );
  const [ytd, setYtd] = useState<HomeYtdResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingTotals(true);
    api.overview
      .weeklyTotals()
      .then((t) => {
        if (!cancelled) setTotals(t);
      })
      .catch(() => {
        if (!cancelled) setTotals(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingTotals(false);
      });

    setYtdError(null);
    api.overview
      .homeYtd()
      .then((h) => {
        if (!cancelled) setYtd(h);
      })
      .catch((e) => {
        if (!cancelled) {
          setYtd(null);
          const msg = e instanceof Error ? e.message : 'Failed to load YTD';
          setYtdError(
            msg === 'Not Found'
              ? 'YTD data unavailable — restart the API server (uvicorn) and refresh.'
              : msg,
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const mixTotal = totals?.sports.reduce((sum, s) => sum + (s.duration ?? 0), 0) ?? 0;
  const todayLabel = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <main className="page page-home">
      <PageHeader title="Home" subtitle={todayLabel} action={<SyncButton />} />
      {loadingTotals ? <div className="loading">Loading…</div> : null}
      {ytdError ? <div className="error">{ytdError}</div> : null}

      <div className="home-grid">
        {totals ? (
          <section className="surface tone-hero home-span-12 home-hero">
            <div className="hero-kicker">This week · {totals.sports.length} sports</div>
            <div className="hero-balance">{formatDuration(totals.totals.duration)}</div>
            {mixTotal > 0 ? (
              <>
                <div className="mix-bar" aria-hidden>
                  {totals.sports.map((s) => {
                    const share = ((s.duration ?? 0) / mixTotal) * 100;
                    if (share <= 0) return null;
                    return (
                      <span
                        key={s.sport}
                        className={`tone-${toneFromSport(s.sport)}`}
                        style={{ flexGrow: Math.max(share, 4), flexBasis: 0 }}
                      />
                    );
                  })}
                </div>
                <div className="mix-legend">
                  {totals.sports.map((s) => (
                    <span key={s.sport} className={`tone-${toneFromSport(s.sport)}`}>
                      <i />
                      {s.label}
                    </span>
                  ))}
                </div>
              </>
            ) : null}
            <div className="hero-stat-row">
              <div className="hero-stat">
                <div className="val">{Math.round(totals.totals.trainings)}</div>
                <div className="lbl">Sessions</div>
              </div>
              <div className="hero-stat">
                <div
                  className="val"
                  style={{ color: totals.totals.duration_delta >= 0 ? 'var(--orange)' : '#ff6b6b' }}
                >
                  {formatDurationDelta(totals.totals.duration_delta)}
                </div>
                <div className="lbl">vs last week</div>
              </div>
            </div>
            <div className="metric-grid">
              {totals.sports.map((s: (typeof totals.sports)[number]) => (
                <MetricCard
                  key={s.sport}
                  tint={toneFromSport(s.sport)}
                  label={`${s.label} km`}
                  value={formatDistance(s.distance, 1)}
                  delta={formatDelta(s.distance_delta, 1)}
                  icon={s.sport === 'swimming' ? 'swim' : s.sport === 'cycling' ? 'bike' : 'run'}
                  negativeDelta={s.distance_delta < 0}
                  compact
                  centered
                />
              ))}
            </div>
          </section>
        ) : null}

        {ytd ? (
          <section className="surface tone-accent home-span-12 home-heatmap">
            <TrainingYtdHeatmap year={ytd.year} days={ytd.heatmap.days} />
          </section>
        ) : null}

        {ytd ? (
          <div className="home-span-12">
            <HomeTrainingExplorer data={ytd} compactCharts />
          </div>
        ) : null}
      </div>
    </main>
  );
}
