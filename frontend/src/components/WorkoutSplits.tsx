import { formatDuration } from '../utils/format';

export interface WorkoutLap {
  split?: number | string;
  distance_km?: number;
  distance_m?: number;
  avg_pace_s_km?: number;
  avg_pace_s_100m?: number;
  elevation_gain_m?: number;
  avg_hr?: number;
  time_s?: number;
  duration_s?: number;
}

function fmtPaceShort(seconds?: number | null): string {
  if (seconds == null || !Number.isFinite(seconds)) return '—';
  const s = Math.round(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

function lapDurationS(lap: WorkoutLap): number {
  return Number(lap.time_s ?? lap.duration_s ?? 0);
}

interface WorkoutPaceChartProps {
  laps: WorkoutLap[];
  avgPaceLabel?: string;
}

export function WorkoutPaceChart({ laps, avgPaceLabel }: WorkoutPaceChartProps) {
  const usable = laps.filter(
    (lap) => lap.avg_pace_s_km && Number(lap.distance_km ?? 0) > 0,
  );
  if (!usable.length) return null;

  const paces = usable.map((l) => Number(l.avg_pace_s_km));
  const minP = Math.min(...paces);
  const maxP = Math.max(...paces);
  const pad = Math.max(15, (maxP - minP) * 0.15);
  const yMin = minP - pad;
  const yMax = maxP + pad;
  const totalDist = usable.reduce((sum, l) => sum + Number(l.distance_km ?? 0), 0);
  const avgPace = totalDist > 0
    ? usable.reduce((sum, l) => sum + Number(l.avg_pace_s_km) * Number(l.distance_km ?? 0), 0) / totalDist
    : paces.reduce((a, b) => a + b, 0) / paces.length;

  const yPos = (pace: number) => ((pace - yMin) / (yMax - yMin)) * 100;
  const avgLineTop = yPos(avgPace);
  const avgLabel = avgPaceLabel ?? `${fmtPaceShort(avgPace)} /km`;

  return (
    <section className="workout-section">
      <h3 className="section-title">Workout analysis</h3>
      <div className="workout-chart">
        <div className="workout-chart-y">
          <span>{fmtPaceShort(yMin)}</span>
          <span>{fmtPaceShort((yMin + yMax) / 2)}</span>
          <span>{fmtPaceShort(yMax)}</span>
        </div>
        <div className="workout-chart-bars">
          <div
            className="workout-avg-line"
            style={{ top: `${avgLineTop}%` }}
            title={`Avg pace ${avgLabel}`}
          />
          {usable.map((lap, i) => {
            const pace = Number(lap.avg_pace_s_km);
            const dist = Number(lap.distance_km ?? 0);
            const widthPct = totalDist ? (dist / totalDist) * 100 : 100 / usable.length;
            const topPct = yPos(pace);
            const heightPct = Math.max(8, 100 - topPct);
            return (
              <div
                key={`${lap.split ?? i}`}
                className="workout-bar-wrap"
                style={{ width: `${widthPct}%` }}
              >
                <div
                  className="workout-bar"
                  style={{ height: `${heightPct}%` }}
                  title={`Split ${lap.split}: ${fmtPaceShort(pace)}/km`}
                />
              </div>
            );
          })}
        </div>
      </div>
      <div className="workout-avg-legend">Avg pace · {avgLabel}</div>
    </section>
  );
}

interface RunSplitsTableProps {
  laps: WorkoutLap[];
}

export function RunSplitsTable({ laps }: RunSplitsTableProps) {
  const paces = laps.map((l) => l.avg_pace_s_km).filter((p): p is number => p != null && Number.isFinite(p));
  const fastest = paces.length ? Math.min(...paces) : null;

  if (!laps.length) return null;

  return (
    <section className="workout-section">
      <h3 className="section-title">Splits</h3>
      <div className="run-splits-wrap">
        <table className="run-splits-table">
          <thead>
            <tr>
              <th>KM</th>
              <th>Pace</th>
              <th aria-label="Pace bar" />
              <th>Elev</th>
              <th>HR</th>
            </tr>
          </thead>
          <tbody>
            {laps.map((lap, i) => {
              const paceS = lap.avg_pace_s_km;
              const paceTxt = fmtPaceShort(paceS);
              const elev = lap.elevation_gain_m;
              const elevTxt = elev != null && Number.isFinite(Number(elev)) ? Math.round(Number(elev)) : '—';
              const hr = lap.avg_hr;
              const hrTxt = hr != null && Number.isFinite(Number(hr)) ? Math.round(Number(hr)) : '—';

              let barPct = 35;
              if (paceS && fastest) {
                const intensity = fastest / paceS;
                barPct = Math.round(35 + 65 * Math.min(intensity, 1.15));
              }

              return (
                <tr key={`${lap.split ?? i}`}>
                  <td>{lap.split ?? i + 1}</td>
                  <td>{paceTxt}</td>
                  <td className="split-bar-cell">
                    <span className="split-bar" style={{ width: `${barPct}%` }} />
                  </td>
                  <td>{elevTxt}</td>
                  <td>{hrTxt}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function cyclingLapPowerW(lap: Record<string, unknown>): number | null {
  const np = lap.normalized_power_w ?? lap.avg_power_w;
  const value = Number(np);
  return Number.isFinite(value) ? value : null;
}

function lapDurationFromRecord(lap: Record<string, unknown>): number {
  return Number(lap.time_s ?? lap.duration_s ?? 0);
}

interface BikeWorkoutSplitsTableProps {
  laps: Record<string, unknown>[];
}

export function BikeWorkoutSplitsTable({ laps }: BikeWorkoutSplitsTableProps) {
  if (!laps.length) return null;

  const powerVals = laps.map(cyclingLapPowerW).filter((p): p is number => p != null);
  const peak = powerVals.length ? Math.max(...powerVals) : null;

  return (
    <section className="section-card tone-bike splits-section">
      <h3 className="section-title">Splits</h3>
      <div className="splits-table-wrap">
        <table className="splits-table bike-splits-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>NP</th>
              <th aria-label="Intensity bar" />
              <th>HR</th>
            </tr>
          </thead>
          <tbody>
            {laps.map((lap, i) => {
              const durS = lapDurationFromRecord(lap);
              const timeTxt = durS > 0 ? formatDuration(durS) : '—';
              const npW = cyclingLapPowerW(lap);
              const npTxt = npW != null ? String(Math.round(npW)) : '—';
              const hr = Number(lap.avg_hr);
              const hrTxt = Number.isFinite(hr) ? String(Math.round(hr)) : '—';

              let barPct = 35;
              let barColor = '#3f3f46';
              if (npW != null && peak) {
                const intensity = npW / peak;
                barPct = Math.round(35 + 65 * Math.min(intensity, 1));
                barColor = intensity >= 0.85 ? '#ff6b2c' : '#ff8f5c';
              }

              return (
                <tr key={`${String(lap.split ?? i)}`}>
                  <td className="split-time">{timeTxt}</td>
                  <td className="split-pace">{npTxt}</td>
                  <td className="split-bar-cell">
                    <span className="split-bar-track">
                      <span
                        className="split-bar-fill"
                        style={{
                          width: `${barPct}%`,
                          background: barColor,
                        }}
                      />
                    </span>
                  </td>
                  <td className="split-hr">{hrTxt}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export { lapDurationS, fmtPaceShort };
