import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import { ActivityList } from '../components/ActivityList';
import { LoadMoreButton } from '../components/LoadMoreButton';
import { PageHeader } from '../components/PageHeader';
import { SegmentedControl } from '../components/SegmentedControl';
import { SportSummaryMetrics } from '../components/SportSummaryMetrics';
import { VolumeChart } from '../components/VolumeChart';
import type { ActivitySummary, Sport, SportPeriodSummary } from '../types';
import { SPORT_VOLUME_KEYS } from '../utils/sportFilters';
import { toneFromSport } from '../utils/tones';

const ACTIVITIES_PAGE_SIZE = 3;

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
  const [periods, setPeriods] = useState<SportPeriodSummary[]>([]);
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [hasMore, setHasMore] = useState(false);

  // One request holds every period filter: switching filters does not refetch.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.sports.summary(sport);
        if (!cancelled) setPeriods(result.periods);
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
  }, [sport]);

  const loadActivities = useCallback(
    async (offset: number, append: boolean) => {
      if (offset === 0) {
        setActivitiesLoading(true);
      } else {
        setLoadingMore(true);
      }
      try {
        const result = await api.sports.activities(sport, offset, ACTIVITIES_PAGE_SIZE);
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
    [sport],
  );

  useEffect(() => {
    setActivities([]);
    setHasMore(false);
    loadActivities(0, false);
  }, [loadActivities]);

  const selected = periods.find((p) => p.name === volumeKey);

  return (
    <main className="page">
      <PageHeader title={title} />

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      <section className={`section-card sport-panel tone-${toneFromSport(sport)}`}>
        <SegmentedControl options={SPORT_VOLUME_KEYS} value={volumeKey} onChange={setVolumeKey} />

        {selected ? (
          <SportSummaryMetrics
            sport={sport}
            distanceKm={selected.distance_total}
            durationSec={selected.duration_total}
            sessions={selected.nb_trainings}
            averageHr={selected.averageHR ?? 0}
            elevationGainM={selected.elevationGain}
            averageSwolf={selected.averageSwolf ?? 0}
            avgNpW={selected.avgNpW ?? 0}
            tint={toneFromSport(sport)}
          />
        ) : null}
      </section>

      <section className="section-card">
        <h2 className="section-title">Performance trends</h2>
        {selected ? (
          <VolumeChart
            points={selected.points}
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
