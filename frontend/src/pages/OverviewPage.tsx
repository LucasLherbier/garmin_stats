import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { FocusHeatmap } from '../components/FocusHeatmap';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import { VolumeChart } from '../components/VolumeChart';
import type { Granularity, OverviewSport, TimeRange } from '../types';
import { formatDelta, formatDistance, formatDuration, formatDurationDelta } from '../utils/format';
import type { Tone } from '../utils/tones';
import { toneFromSport } from '../utils/tones';

const HEATMAP_OPTIONS: Array<{ value: 'swimming' | 'cycling' | 'running' | 'race'; label: string }> = [
  { value: 'running', label: 'Run' },
  { value: 'cycling', label: 'Bike' },
  { value: 'swimming', label: 'Swim' },
  { value: 'race', label: 'Race' },
];

const HEATMAP_TONES: Record<(typeof HEATMAP_OPTIONS)[number]['value'], Tone> = {
  swimming: 'swim',
  cycling: 'bike',
  running: 'run',
  race: 'gold',
};
const SPORT_OPTIONS: Array<{ value: OverviewSport; label: string }> = [
  { value: 'duration', label: 'Overall' },
  { value: 'swimming', label: 'Swim' },
  { value: 'cycling', label: 'Bike' },
  { value: 'running', label: 'Run' },
];

const RANGE_OPTIONS: Array<{ value: TimeRange; label: string }> = [
  { value: '4_units', label: '4' },
  { value: '6_units', label: '6' },
  { value: 'ytd', label: 'YTD' },
  { value: 'all', label: 'All' },
];

const GRANULARITY_OPTIONS: Array<{ value: Granularity; label: string }> = [
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
];

const PERIOD_LABELS: Record<string, string> = {
  last_1: 'Last period',
  last_4: 'Last 4',
  last_12: 'Last 12',
  last_all: 'YTD',
};

export function OverviewPage() {
  const [sport, setSport] = useState<OverviewSport>('duration');
  const [timeRange, setTimeRange] = useState<TimeRange>('4_units');
  const [granularity, setGranularity] = useState<Granularity>('week');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totals, setTotals] = useState<Awaited<ReturnType<typeof api.overview.weeklyTotals>> | null>(
    null,
  );
  const [chart, setChart] = useState<Awaited<ReturnType<typeof api.overview.volumeChart>> | null>(
    null,
  );
  const [benchmarks, setBenchmarks] = useState<Record<string, unknown>[]>([]);
  const [syncPassword, setSyncPassword] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [heatmapSport, setHeatmapSport] = useState<(typeof HEATMAP_OPTIONS)[number]['value']>('running');
  const [heatmap, setHeatmap] = useState<Awaited<ReturnType<typeof api.overview.activityHeatmap>> | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [t, c, b] = await Promise.all([
          api.overview.weeklyTotals(),
          api.overview.volumeChart(sport, timeRange, granularity),
          api.overview.benchmarks(sport, granularity),
        ]);
        if (!cancelled) {
          setTotals(t);
          setChart(c);
          setBenchmarks(b.periods);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [sport, timeRange, granularity]);

  useEffect(() => {
    let cancelled = false;
    api.overview.activityHeatmap(heatmapSport).then((data) => {
      if (!cancelled) setHeatmap(data);
    }).catch(() => {
      if (!cancelled) setHeatmap(null);
    });
    return () => {
      cancelled = true;
    };
  }, [heatmapSport]);

  const unitLabel = granularity === 'week' ? 'Weeks' : 'Months';
  const yLabel = sport === 'duration' ? 'Duration' : 'Distance (km)';
  const mixTotal = totals?.sports.reduce((sum, s) => sum + (s.duration ?? 0), 0) ?? 0;

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
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : 'Sync failed');
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="page">
      <PageHeader title="Dashboard" />

      <section className="section-card tone-hero">
        <h2 className="section-title">Sync data</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 0 }}>
          Trigger the weekly Garmin extract on GitHub Actions.
        </p>
        <input
          type="password"
          className="form-field"
          placeholder="Sync password"
          value={syncPassword}
          autoComplete="current-password"
          disabled={syncing}
          onChange={(e) => setSyncPassword(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary"
          disabled={syncing || !syncPassword.trim()}
          onClick={handleSync}
        >
          {syncing ? 'Starting sync…' : 'Upload / Sync'}
        </button>
        {syncMessage ? (
          <p style={{ color: 'var(--accent)', fontSize: '0.85rem' }}>{syncMessage}</p>
        ) : null}
        {syncError ? <div className="error">{syncError}</div> : null}
      </section>
      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {totals ? (
        <section className="surface tone-hero">
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

      <section className="section-card">
        <SegmentedControl options={HEATMAP_OPTIONS} value={heatmapSport} onChange={setHeatmapSport} />
        <div style={{ height: 10 }} />
        <FocusHeatmap
          cells={heatmap?.cells ?? []}
          tone={HEATMAP_TONES[heatmapSport]}
          title="When you train this week"
        />
      </section>

      <section className="surface tone-run">
        <h2 className="section-title">Training explorer</h2>
      <SegmentedControl options={GRANULARITY_OPTIONS} value={granularity} onChange={setGranularity} />
      <div style={{ height: 10 }} />
      <SegmentedControl options={SPORT_OPTIONS} value={sport} onChange={setSport} />
      <div style={{ height: 10 }} />
      <SegmentedControl
        options={RANGE_OPTIONS.map((r) => ({
          ...r,
          label: r.value === 'ytd' || r.value === 'all' ? r.label : `${r.label} ${unitLabel}`,
        }))}
        value={timeRange}
        onChange={setTimeRange}
      />

      {chart ? (
        <VolumeChart
          points={chart.points}
          yColumn={chart.y_column}
          yLabel={yLabel}
          title="Volume trend"
          valueFormat={sport === 'duration' ? 'duration' : 'distance'}
          periodLabel={granularity === 'week' ? 'Week' : 'Month'}
        />
      ) : null}      </section>

      {benchmarks.length ? (
        <section className="surface tone-gold">
          <h2 className="section-title">Benchmarks</h2>
          {benchmarks.map((row) => (
            <div key={String(row.name)} className="race-card">
              <h3>{PERIOD_LABELS[String(row.name)] ?? String(row.name)}</h3>
              <div className="metric-grid cols-3">
                <MetricCard
                  label="Distance"
                  value={formatDistance(Number(row.distance_total ?? 0), 1)}
                  icon="distance"
                  tint="hero"
                  compact
                  centered
                />
                <MetricCard
                  label="Duration"
                  value={formatDuration(Number(row.duration_total ?? 0))}
                  icon="duration"
                  tint="hero"
                  compact
                  centered
                />
                <MetricCard
                  label="Sessions"
                  value={String(Math.round(Number(row.nb_trainings ?? 0)))}
                  icon="sessions"
                  tint="hero"
                  compact
                  centered
                />
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </main>
  );
}
