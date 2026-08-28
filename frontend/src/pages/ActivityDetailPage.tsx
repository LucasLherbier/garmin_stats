import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { PowerCurveChart } from '../components/PowerCurveChart';
import { PowerProfileChart } from '../components/PowerProfileChart';
import { RouteMap } from '../components/RouteMap';
import { SplitsTable } from '../components/SplitsTable';
import { RunSplitsTable, WorkoutPaceChart, type WorkoutLap } from '../components/WorkoutSplits';
import { TelemetryChart } from '../components/TelemetryChart';
import { formatActivityWhen } from '../utils/format';

function avgPowerFromTelemetry(rows: Record<string, unknown>[] | null | undefined): number | null {
  if (!rows?.length) return null;
  const watts = rows
    .map((row) => Number(row.Watts))
    .filter((value) => Number.isFinite(value) && value > 0);
  if (!watts.length) return null;
  return Math.round(watts.reduce((sum, value) => sum + value, 0) / watts.length);
}

function DetailMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-metric">
      <div className="lbl">{label}</div>
      <div className="val">{value}</div>
    </div>
  );
}

export function ActivityDetailPage() {
  const { sport, activityId } = useParams<{ sport?: string; activityId: string }>();
  const location = useLocation();
  const fromStats = location.pathname.startsWith('/stats/');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Awaited<ReturnType<typeof api.sports.activityDetail>> | null>(
    null,
  );

  useEffect(() => {
    if (!activityId) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.sports.activityDetail(Number(activityId));
        if (!cancelled) setDetail(data);
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
  }, [activityId]);

  const activity = detail?.activity;
  const backTo = fromStats ? '/stats' : `/${sport ?? 'run'}`;
  const laps = (detail?.laps ?? []) as WorkoutLap[];
  const hasWorkoutLaps = laps.length > 0 && detail?.sport === 'running';
  const when = formatActivityWhen(activity?.startTimeLocal ?? activity?.Day, activity?.Day);
  const locationName = String(activity?.locationName ?? '').trim();
  const isCycling = detail?.sport === 'cycling';
  const avgPower = useMemo(
    () => avgPowerFromTelemetry(detail?.telemetry),
    [detail?.telemetry],
  );

  return (
    <main className="page">
      <Link to={backTo} className="back-link">← Back</Link>

      {loading ? <div className="loading">Loading…</div> : null}
      {error ? <div className="error">{error}</div> : null}

      {activity ? (
        <>
          <h2 className="activity-detail-title">
            {String(activity.activityName ?? 'Activity')}
          </h2>
          <div className="activity-detail-meta">
            {[when.dateLine, when.timeLine, locationName].filter(Boolean).join(' · ')}
          </div>

          {detail?.structure_summary ? (
            <p className="activity-structure-summary">{detail.structure_summary}</p>
          ) : null}

          {detail?.track ? (
            <section className="section-card section-card--flush">
              <h3 className="section-title">Route</h3>
              <RouteMap points={detail.track} />
            </section>
          ) : null}

          {isCycling ? (
            <div className="detail-metrics">
              <DetailMetric
                label="Distance"
                value={`${Number(activity.distance ?? 0).toFixed(2)} km`}
              />
              <DetailMetric
                label="Elevation Gain"
                value={`${Math.round(Number(activity.elevationGain ?? 0))} m`}
              />
              <DetailMetric
                label="Moving Time"
                value={String(activity.durationFormatted ?? activity.duration ?? '—')}
              />
              <DetailMetric
                label="Avg Power"
                value={avgPower != null ? `${avgPower} W` : '—'}
              />
              <DetailMetric
                label="Avg Speed"
                value={`${Number(activity.averageSpeed ?? 0).toFixed(1)} km/h`}
              />
              <DetailMetric
                label="Calories"
                value={
                  activity.calories
                    ? `${Math.round(Number(activity.calories))} Cal`
                    : '—'
                }
              />
            </div>
          ) : (
            <div className="detail-metrics">
              <DetailMetric
                label="Distance"
                value={`${Number(activity.distance ?? 0).toFixed(2)} km`}
              />
              {activity.pace ? (
                <DetailMetric label="Avg Pace" value={String(activity.pace)} />
              ) : null}
              <DetailMetric
                label="Elapsed Time"
                value={String(activity.durationFormatted ?? activity.duration ?? '—')}
              />
              <DetailMetric
                label="Elevation Gain"
                value={`${Math.round(Number(activity.elevationGain ?? 0))} m`}
              />
              {activity.calories ? (
                <DetailMetric
                  label="Calories"
                  value={`${Math.round(Number(activity.calories))} Cal`}
                />
              ) : null}
              <DetailMetric
                label="Avg Heart Rate"
                value={`${Math.round(Number(activity.averageHR ?? 0))} bpm`}
              />
            </div>
          )}

          {detail?.telemetry?.length ? (
            <TelemetryChart rows={detail.telemetry} sport={detail.sport} />
          ) : null}

          {hasWorkoutLaps ? (
            <>
              <WorkoutPaceChart laps={laps} avgPaceLabel={activity.pace ? String(activity.pace) : undefined} />
              <RunSplitsTable laps={laps} />
            </>
          ) : null}

          {detail?.splits?.length ? (
            <SplitsTable rows={detail.splits} title={hasWorkoutLaps ? 'Split details' : 'Splits'} />
          ) : null}

          {!hasWorkoutLaps && !detail?.splits?.length && detail?.workout_laps?.length ? (
            <SplitsTable rows={detail.workout_laps} title="Splits" />
          ) : null}

          {isCycling && detail?.power_profile ? (
            <>
              <PowerProfileChart
                displayLabels={detail.power_profile.display_labels}
                values={detail.power_profile.values}
              />
              <PowerCurveChart
                displayLabels={detail.power_profile.display_labels}
                values={detail.power_profile.values}
                seconds={detail.power_profile.seconds}
              />
            </>
          ) : null}
        </>
      ) : null}
    </main>
  );
}
