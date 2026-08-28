import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { RaceVolumeMetrics, type RaceVolumeKey } from '../components/RaceVolumeMetrics';
import { SegmentedControl } from '../components/SegmentedControl';
import { VolumeChart } from '../components/VolumeChart';
import { VolumeStackChart } from '../components/VolumeStackChart';
import type { Granularity } from '../types';

type RaceChartView = 'swimming' | 'cycling' | 'running' | 'volume';
type RaceActivityTab = 'swimming' | 'cycling' | 'running' | 'gym';

const CHART_VIEW_OPTIONS: Array<{ value: RaceChartView; label: string }> = [
  { value: 'swimming', label: 'Swim' },
  { value: 'cycling', label: 'Bike' },
  { value: 'running', label: 'Run' },
  { value: 'volume', label: 'Volume' },
];

const ACTIVITY_TAB_OPTIONS: Array<{ value: RaceActivityTab; label: string }> = [
  { value: 'swimming', label: 'Swim' },
  { value: 'cycling', label: 'Bike' },
  { value: 'running', label: 'Run' },
  { value: 'gym', label: 'Gym' },
];

type RaceActivity = Awaited<
  ReturnType<typeof api.race.activities>
>['activities'][number];

function formatActivityPace(activity: RaceActivity, tab: RaceActivityTab): string {
  if (tab === 'running' && activity.pace) return activity.pace;
  if (tab === 'cycling' && activity.averageSpeed > 0) {
    return `${activity.averageSpeed.toFixed(1)} km/h`;
  }
  return '—';
}

function activityDetailPath(activity: RaceActivity, tab: RaceActivityTab): string | null {
  if (tab === 'gym') return null;
  const prefix = tab === 'swimming' ? 'swim' : tab === 'cycling' ? 'bike' : 'run';
  return `/${prefix}/activity/${activity.activityId}`;
}

function activityCellValues(activity: RaceActivity, tab: RaceActivityTab) {
  return {
    date: activity.day ?? '—',
    distance: tab === 'gym' ? '—' : `${activity.distance.toFixed(1)}`,
    time: activity.duration,
    pace:
      tab === 'gym'
        ? activity.calories > 0
          ? String(Math.round(activity.calories))
          : '—'
        : formatActivityPace(activity, tab),
    hr: activity.averageHR > 0 ? String(Math.round(activity.averageHR)) : '—',
  };
}

function activityColumns(tab: RaceActivityTab) {
  return [
    { key: 'date', label: 'Date' },
    { key: 'distance', label: 'Dist' },
    { key: 'time', label: 'Time' },
    { key: tab === 'gym' ? 'pace' : 'pace', label: tab === 'gym' ? 'Cal' : 'Pace' },
    { key: 'hr', label: 'HR' },
  ] as const;
}

export function RacePage() {
  const navigate = useNavigate();
  const [races, setRaces] = useState<Array<{ index: number; display: string }>>([]);
  const [raceIndex, setRaceIndex] = useState(0);
  const [granularity, setGranularity] = useState<Granularity>('week');
  const [chartView, setChartView] = useState<RaceChartView>('swimming');
  const [activityTab, setActivityTab] = useState<RaceActivityTab>('swimming');
  const [volumeKey, setVolumeKey] = useState<RaceVolumeKey>('total');
  const [activityPage, setActivityPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activitiesError, setActivitiesError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Awaited<ReturnType<typeof api.race.detail>> | null>(null);
  const [activitiesData, setActivitiesData] = useState<
    Awaited<ReturnType<typeof api.race.activities>> | null
  >(null);

  const activityCols = useMemo(() => activityColumns(activityTab), [activityTab]);

  useEffect(() => {
    api.race
      .list()
      .then((res) => {
        setRaces(res.races);
        if (res.races.length) setRaceIndex(res.races[0].index);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load races'));
  }, []);

  useEffect(() => {
    if (!races.length) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.race.detail(raceIndex, granularity);
        if (!cancelled) setDetail(result);
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
  }, [raceIndex, granularity, races.length]);

  useEffect(() => {
    setActivityPage(1);
  }, [raceIndex, activityTab]);

  useEffect(() => {
    if (!races.length || detail?.empty) return;

    let cancelled = false;

    async function loadActivities() {
      setActivitiesLoading(true);
      setActivitiesError(null);
      try {
        const result = await api.race.activities(raceIndex, activityTab, activityPage);
        if (!cancelled) setActivitiesData(result);
      } catch (e) {
        if (!cancelled) {
          setActivitiesError(e instanceof Error ? e.message : 'Failed to load activities');
        }
      } finally {
        if (!cancelled) setActivitiesLoading(false);
      }
    }

    loadActivities();
    return () => {
      cancelled = true;
    };
  }, [raceIndex, activityTab, activityPage, races.length, detail?.empty]);

  const activeDistanceChart = useMemo(
    () => detail?.distance_charts.find((chart) => chart.name === chartView),
    [detail?.distance_charts, chartView],
  );

  const volumePoints = useMemo(
    () =>
      (detail?.training_load.totals ?? []).map((row) => ({
        Week: row.time_period,
        total_duration: row.total_duration,
      })),
    [detail?.training_load.totals],
  );

  return (
    <main className="page">
      <PageHeader title="Race prep" />

      {races.length ? (
        <select
          className="form-field"
          value={raceIndex}
          onChange={(e) => setRaceIndex(Number(e.target.value))}
        >
          {races.map((r) => (
            <option key={r.index} value={r.index}>
              {r.display}
            </option>
          ))}
        </select>
      ) : null}

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}
      {detail?.empty ? <div className="empty">No preparation data for this race.</div> : null}

      {detail && !detail.empty ? (
        <>
          <section className="section-card tone-hero training-volume-hero">
            <h2 className="section-title">Trainings Volume</h2>
            <RaceVolumeMetrics
              rows={detail.training_volume}
              volumeKey={volumeKey}
              onVolumeKeyChange={setVolumeKey}
            />
          </section>

          <section className="section-card">
            <h2 className="section-title">Distance over time</h2>
            <SegmentedControl
              options={[
                { value: 'week' as const, label: 'Week' },
                { value: 'month' as const, label: 'Month' },
              ]}
              value={granularity}
              onChange={setGranularity}
            />
            <div style={{ height: 10 }} />
            <SegmentedControl
              options={CHART_VIEW_OPTIONS}
              value={chartView}
              onChange={setChartView}
            />
            <div style={{ height: 10 }} />
            {chartView === 'volume' ? (
              volumePoints.length ? (
                <VolumeChart
                  points={volumePoints}
                  yColumn="total_duration"
                  yLabel="Duration"
                  title="Total volume"
                  valueFormat="duration"
                  periodLabel={granularity === 'week' ? 'Week' : 'Month'}
                />
              ) : (
                <div className="empty">No volume data for this period.</div>
              )
            ) : activeDistanceChart ? (
              <VolumeChart
                points={activeDistanceChart.points.map((p) => ({
                  Week: p.time_period,
                  total_distance: p.total_distance,
                }))}
                yColumn="total_distance"
                yLabel={activeDistanceChart.y_axis_title}
                title={`${activeDistanceChart.display} volume`}
                valueFormat="distance"
                periodLabel={granularity === 'week' ? 'Week' : 'Month'}
              />
            ) : (
              <div className="empty">No distance data for this sport.</div>
            )}
          </section>

          <section className="section-card">
            <VolumeStackChart
              rows={detail.training_load.rows}
              totals={detail.training_load.totals}
              sportColors={detail.training_load.sport_colors}
              yTicks={detail.training_load.y_ticks}
              yMax={detail.training_load.y_max}
              title={detail.training_load.title}
              horizontal
            />
          </section>

          <section className="section-card">
            <h2 className="section-title">Recovery & wellness</h2>
            <p className="section-caption">
              Daily wellness metrics averaged by {granularity}.
            </p>
            {detail.wellness?.charts.some((chart) => chart.points.length) ? (
              detail.wellness.charts.map((chart) =>
                chart.points.length ? (
                  <VolumeChart
                    key={chart.key}
                    points={chart.points.map((p) => ({
                      Week: p.time_period,
                      value: p.value,
                    }))}
                    yColumn="value"
                    yLabel={chart.y_axis_title}
                    title={chart.label}
                    periodLabel={granularity === 'week' ? 'Week' : 'Month'}
                  />
                ) : null,
              )
            ) : (
              <div className="empty">No wellness data for this period.</div>
            )}
          </section>

          <section className="section-card">
            <h2 className="section-title">Training block activities</h2>
            <SegmentedControl
              options={ACTIVITY_TAB_OPTIONS}
              value={activityTab}
              onChange={setActivityTab}
            />
            <div style={{ height: 10 }} />
            {activitiesLoading ? <div className="loading">Loading activities…</div> : null}
            {activitiesError ? <div className="error">{activitiesError}</div> : null}
            {!activitiesLoading && activitiesData && !activitiesData.activities.length ? (
              <div className="empty">No activities for this sport in the training block.</div>
            ) : null}
            {activitiesData?.activities.length ? (
              <>
                <div className="race-activity-list">
                  {activitiesData.activities.map((activity) => {
                    const detailPath = activityDetailPath(activity, activityTab);
                    const values = activityCellValues(activity, activityTab);
                    return (
                      <button
                        key={activity.activityId}
                        type="button"
                        className="race-activity-row"
                        disabled={!detailPath}
                        onClick={() => {
                          if (detailPath) navigate(detailPath);
                        }}
                      >
                        {activityCols.map((col) => (
                          <div key={col.key} className="race-activity-cell">
                            <span className="lbl">{col.label}</span>
                            <span className="val">{values[col.key]}</span>
                          </div>
                        ))}
                      </button>
                    );
                  })}
                </div>
                {activitiesData.total_pages > 1 ? (
                  <div className="pagination">
                    <button
                      type="button"
                      disabled={activityPage <= 1}
                      onClick={() => setActivityPage((p) => p - 1)}
                    >
                      Prev
                    </button>
                    <span>
                      {activityPage} / {activitiesData.total_pages}
                    </span>
                    <button
                      type="button"
                      disabled={activityPage >= activitiesData.total_pages}
                      onClick={() => setActivityPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                ) : null}
              </>
            ) : null}
          </section>
        </>
      ) : null}
    </main>
  );
}
