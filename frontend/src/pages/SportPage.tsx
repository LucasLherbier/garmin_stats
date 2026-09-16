import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { ActivityList } from '../components/ActivityList';
import { LoadMoreButton } from '../components/LoadMoreButton';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import { SportSummaryMetrics } from '../components/SportSummaryMetrics';
import { VolumeChart } from '../components/VolumeChart';
import type { ActivitySummary, Sport } from '../types';
import { SPORT_VOLUME_KEYS, volumeKeyToSummaryKey, volumeKeyToTimeRange } from '../utils/sportFilters';
import { toneFromSport } from '../utils/tones';

interface SportPageProps {
  sport: Sport;
  title: string;
}

export function SportPage({ sport, title }: SportPageProps) {
  const [volumeKey, setVolumeKey] = useState('last_12');
  const [loading, setLoading] = useState(true);
  const [activitiesLoading, setActivitiesLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [volume, setVolume] = useState<Record<string, unknown>[]>([]);
  const [trends, setTrends] = useState<Awaited<ReturnType<typeof api.sports.trends>> | null>(null);
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [hasMore, setHasMore] = useState(false);

  const timeRange = useMemo(() => volumeKeyToTimeRange(volumeKey), [volumeKey]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [v, t] = await Promise.all([
          api.sports.volumeSummary(sport),
          api.sports.trends(sport, timeRange),
        ]);
        if (!cancelled) {
          setVolume(v.periods);
          setTrends(t);
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
  }, [sport, timeRange]);

  const loadActivities = useCallback(
    async (offset: number, append: boolean) => {
      if (offset === 0) {
        setActivitiesLoading(true);
      } else {
        setLoadingMore(true);
      }
      try {
        const result = await api.sports.activities(sport, timeRange, offset);
        setActivities((prev) => (append ? [...prev, ...result.activities] : result.activities));
        setHasMore(result.has_more);
      } catch (e) {
        if (offset === 0) {
          setError(e instanceof Error ? e.message : 'Failed to load activities');
        }
      } finally {
        if (offset === 0) {
          setActivitiesLoading(false);
        } else {
          setLoadingMore(false);
        }
      }
    },
    [sport, timeRange],
  );

  useEffect(() => {
    setActivities([]);
    setHasMore(false);
    loadActivities(0, false);
  }, [loadActivities]);

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
        {activitiesLoading ? <div className="loading">Loading activities…</div> : null}
        {!activitiesLoading ? (
          <>
            <ActivityList activities={activities} sport={sport} />
            <LoadMoreButton
              hasMore={hasMore}
              loading={loadingMore}
              onClick={() => loadActivities(activities.length, true)}
            />
          </>
        ) : null}
      </section>
    </main>
  );
}
