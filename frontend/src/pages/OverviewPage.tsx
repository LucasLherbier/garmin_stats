import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { ActivityMonthCalendar } from '../components/ActivityMonthCalendar';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { SyncButton } from '../components/SyncButton';
import { SegmentedControl } from '../components/SegmentedControl';
import { VolumeChart } from '../components/VolumeChart';
import type { Granularity, OverviewSport, TimeRange } from '../types';
import { formatDelta, formatDistance, formatDuration, formatDurationDelta } from '../utils/format';
import { toneFromSport } from '../utils/tones';

function currentYearMonth() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

function shiftMonth(year: number, month: number, delta: number) {
  const d = new Date(year, month - 1 + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

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
  const [calendarMonth, setCalendarMonth] = useState(currentYearMonth);
  const [calendar, setCalendar] = useState<
    Awaited<ReturnType<typeof api.overview.activityCalendar>> | null
  >(null);

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
    api.overview
      .activityCalendar(calendarMonth.year, calendarMonth.month)
      .then((data) => {
        if (!cancelled) setCalendar(data);
      })
      .catch(() => {
        if (!cancelled) setCalendar(null);
      });
    return () => {
      cancelled = true;
    };
  }, [calendarMonth]);

  const nowYm = currentYearMonth();
  const canNextCalendarMonth =
    calendarMonth.year < nowYm.year ||
    (calendarMonth.year === nowYm.year && calendarMonth.month < nowYm.month);

  const unitLabel = granularity === 'week' ? 'Weeks' : 'Months';
  const yLabel = sport === 'duration' ? 'Duration' : 'Distance (km)';
  const mixTotal = totals?.sports.reduce((sum, s) => sum + (s.duration ?? 0), 0) ?? 0;

  return (
    <main className="page">
      <PageHeader title="Home" action={<SyncButton />} />
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
        <ActivityMonthCalendar
          year={calendarMonth.year}
          month={calendarMonth.month}
          activities={calendar?.activities ?? []}
          title="When you train"
          onPrevMonth={() => setCalendarMonth((m) => shiftMonth(m.year, m.month, -1))}
          onNextMonth={() => {
            if (canNextCalendarMonth) {
              setCalendarMonth((m) => shiftMonth(m.year, m.month, 1));
            }
          }}
          canNextMonth={canNextCalendarMonth}
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
