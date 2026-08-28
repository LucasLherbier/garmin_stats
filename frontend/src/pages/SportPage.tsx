import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { ActivityList } from '../components/ActivityList';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import { SportSummaryMetrics } from '../components/SportSummaryMetrics';
import { VolumeChart } from '../components/VolumeChart';
import type { Sport } from '../types';
import { SPORT_VOLUME_KEYS, volumeKeyToSummaryKey, volumeKeyToTimeRange } from '../utils/sportFilters';
import { toneFromSport } from '../utils/tones';

interface SportPageProps {
  sport: Sport;
  routePrefix: string;
  title: string;
}

export function SportPage({ sport, routePrefix, title }: SportPageProps) {
  const [volumeKey, setVolumeKey] = useState('last_12');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolume] = useState<Record<string, unknown>[]>([]);
  const [trends, setTrends] = useState<Awaited<ReturnType<typeof api.sports.trends>> | null>(null);
  const [activities, setActivities] = useState<
    Awaited<ReturnType<typeof api.sports.activities>> | null
  >(null);

  const timeRange = useMemo(() => volumeKeyToTimeRange(volumeKey), [volumeKey]);

  useEffect(() => {
    setPage(1);
  }, [volumeKey, sport]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [v, t, a] = await Promise.all([
          api.sports.volumeSummary(sport),
          api.sports.trends(sport, timeRange),
          api.sports.activities(sport, timeRange, page),
        ]);
        if (!cancelled) {
          setVolume(v.periods);
          setTrends(t);
          setActivities(a);
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
  }, [sport, timeRange, page]);

  const selectedVolume = volume.find((r) => r.name === volumeKeyToSummaryKey(volumeKey));

  return (
    <main className="page">
      <PageHeader title={title} />

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      <section className={`section-card sport-panel tone-${toneFromSport(sport)}`}>
        <SegmentedControl options={SPORT_VOLUME_KEYS} value={volumeKey} onChange={setVolumeKey} />

        {selectedVolume ? (
          <SportSummaryMetrics
            sport={sport}
            distanceKm={Number(selectedVolume.distance_total ?? 0)}
            durationSec={Number(selectedVolume.duration_total ?? 0)}
            sessions={Math.round(Number(selectedVolume.nb_trainings ?? 0))}
            averageHr={Number(selectedVolume.averageHR ?? 0)}
            elevationGainM={Number(selectedVolume.elevationGain ?? 0)}
            averageSwolf={Number(selectedVolume.averageSwolf ?? 0)}
            avgNpW={Number(selectedVolume.avgNpW ?? 0)}
            tint={toneFromSport(sport)}
          />
        ) : null}
      </section>

      <section className="section-card">
        <h2 className="section-title">Performance trends</h2>
        {trends ? (
          <VolumeChart
            points={trends.points}
            yColumn="total_distance"
            yLabel="Distance (km)"
          />
        ) : null}
      </section>

      <section className="section-card">
        <h2 className="section-title">Recent activities</h2>
        {activities ? (
          <>
            <ActivityList activities={activities.activities} routePrefix={routePrefix} sport={sport} />
            {activities.total_pages > 1 ? (
              <div className="pagination">
                <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Prev
                </button>
                <span>
                  {page} / {activities.total_pages}
                </span>
                <button
                  type="button"
                  disabled={page >= activities.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            ) : null}
          </>
        ) : null}
      </section>
    </main>
  );
}
