import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import type { RaceResult } from '../types';

function RaceCard({ race, triathlon = false }: { race: RaceResult; triathlon?: boolean }) {
  return (
    <article className="race-card tone-gold">
      <h3>{race.name}</h3>
      <div className="sub">
        {race.date} · {race.location} · Bib {race.bib}
      </div>
      <div className="metric-grid cols-3">
        <MetricCard label="Finish" value={race.duration} icon="duration" />
        <MetricCard label="Overall" value={`${race.ranking}/${race.nb_athletes}`} icon="trophy" />
        <MetricCard label="Category" value={race.ranking_category} icon="rank" />
      </div>
      <details className="expander">
        <summary>Split breakdown</summary>
        {triathlon ? (
          <div style={{ marginTop: 8 }}>
            <p>
              <strong>Swim:</strong> {race.swimming} ({race.swim_pace})
            </p>
            <p>
              <strong>T1/T2:</strong> {race.t1} / {race.t2}
            </p>
            <p>
              <strong>Bike:</strong> {race.cycling} ({race.cycling_pace})
            </p>
            <p>
              <strong>Run:</strong> {race.running} ({race.running_pace})
            </p>
          </div>
        ) : (
          <p style={{ marginTop: 8 }}>
            <strong>Pace:</strong> {race.running_pace}
          </p>
        )}
        {race.link ? (
          <p style={{ marginTop: 8 }}>
            <a href={race.link} target="_blank" rel="noreferrer">
              Official results →
            </a>
          </p>
        ) : null}
      </details>
    </article>
  );
}

export function ResultsPage() {
  const [tab, setTab] = useState<'tri' | 'run'>('tri');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triathlon, setTriathlon] = useState<RaceResult[]>([]);
  const [running, setRunning] = useState<RaceResult[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.races.results();
        if (!cancelled) {
          setTriathlon(data.triathlon);
          setRunning(data.running);
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
  }, []);

  const list = tab === 'tri' ? triathlon : running;

  return (
    <main className="page">
      <PageHeader title="Results" />

      <SegmentedControl
        options={[
          { value: 'tri' as const, label: 'Triathlon' },
          { value: 'run' as const, label: 'Running' },
        ]}
        value={tab}
        onChange={setTab}
      />

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {!loading && !list.length ? <div className="empty">No results found.</div> : null}

      {list.map((race) => (
        <RaceCard key={`${race.name}-${race.date}`} race={race} triathlon={tab === 'tri'} />
      ))}
    </main>
  );
}
