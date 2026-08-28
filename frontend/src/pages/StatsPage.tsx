import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import { toneFromSport } from '../utils/tones';

type MetricChoice = 'duration' | 'distance';

export function StatsPage() {
  const navigate = useNavigate();
  const [metric, setMetric] = useState<MetricChoice>('duration');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Awaited<ReturnType<typeof api.stats.all>> | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.stats.all(metric);
        if (!cancelled) setData(result);
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
  }, [metric]);

  return (
    <main className="page">
      <PageHeader title="All-time stats" />

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {data?.best_records.map((group) => (
        <section key={group.sport_name} className={`section-card tone-${toneFromSport(group.sport_name)}`}>
          <h2 className="section-title">{group.sport_name} records</h2>
          <div className="metric-grid cols-3">
            {group.records.map((r) => (
              <MetricCard key={r.label} label={r.label} value={r.value} delta={r.date} icon={r.icon} />
            ))}
          </div>
        </section>
      ))}

      <section className="section-card tone-hero">
        <h2 className="section-title">Volume records</h2>
        <SegmentedControl
          options={[
            { value: 'duration' as const, label: 'Duration' },
            { value: 'distance' as const, label: 'Distance' },
          ]}
          value={metric}
          onChange={setMetric}
        />

        {data?.volume_records.map((group) => (
          <section key={group.sport_name} style={{ marginTop: 16 }}>
            <h3 className="section-title">{group.sport_name}</h3>
            <div className="metric-grid">
              {group.cards.map((c) => (
                <MetricCard key={c.label} label={c.label} value={c.value} delta={c.period} icon={c.icon} />
              ))}
            </div>
          </section>
        ))}
      </section>

      {data?.summary_rows.length ? (
        <section className="section-card">
          <h2 className="section-title">Record activities</h2>
          <div className="activity-list">
            {data.summary_rows.map((row) => (
              <button
                key={`${row.activityId}-${row.label}`}
                type="button"
                className="activity-row"
                onClick={() => navigate(`/stats/activity/${row.activityId}`)}
              >
                <div className="activity-row-main">
                  <div className="name">{row.label}</div>
                  <div className="meta">{row.activityName} · {row.day}</div>
                </div>
                <div className="activity-row-stats">
                  <div className="activity-stat-pill">
                    <div className="val">{row.distance.toFixed(2)} km</div>
                    <div className="lbl">Distance</div>
                  </div>
                  <div className="activity-stat-pill">
                    <div className="val">{String(row.duration)}</div>
                    <div className="lbl">Time</div>
                  </div>
                </div>
                <span className="arrow" aria-hidden>›</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
