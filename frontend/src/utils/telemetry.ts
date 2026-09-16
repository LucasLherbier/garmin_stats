import { formatDurationChart } from './format';

const METRICS = ['HeartRate', 'Cadence', 'Speed', 'Watts', 'Altitude'] as const;
export type TelemetryMetric = (typeof METRICS)[number];

export function metricValue(row: Record<string, unknown>, metric: TelemetryMetric): number {
  const raw = Number(row[metric] ?? 0);
  if (!Number.isFinite(raw)) return 0;
  return metric === 'Speed' ? raw * 3.6 : raw;
}

function parseElapsedSeconds(row: Record<string, unknown>): number {
  const elapsed = Number(row.elapsed_s);
  if (Number.isFinite(elapsed) && elapsed >= 0) return elapsed;

  const time = String(row.Time ?? '');
  const match = time.match(/(\d{2}):(\d{2}):(\d{2})/);
  if (!match) return 0;
  return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]);
}

function rollingAverage(values: number[], elapsed: number[], windowSec: number): number[] {
  if (!values.length) return [];
  const out: number[] = [];
  let start = 0;
  let sum = 0;
  let count = 0;

  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    count += 1;
    while (start < i && elapsed[i] - elapsed[start] > windowSec) {
      sum -= values[start];
      count -= 1;
      start += 1;
    }
    out.push(count > 0 ? sum / count : values[i]);
  }
  return out;
}

export function prepareTelemetryChartData(
  rows: Record<string, unknown>[],
  y1: TelemetryMetric,
  y2: TelemetryMetric | null,
  windowSec = 10,
) {
  const parsed = rows.map((row) => ({
    elapsed: parseElapsedSeconds(row),
    y1: metricValue(row, y1),
    y2: y2 ? metricValue(row, y2) : null,
  }));

  const y1Smoothed = rollingAverage(
    parsed.map((row) => row.y1),
    parsed.map((row) => row.elapsed),
    windowSec,
  );
  const y2Smoothed =
    y2 == null
      ? null
      : rollingAverage(
          parsed.map((row) => row.y2 ?? 0),
          parsed.map((row) => row.elapsed),
          windowSec,
        );

  const maxElapsed = parsed.length ? parsed[parsed.length - 1].elapsed : 0;

  return parsed.map((row, index) => ({
    elapsed: row.elapsed,
    time: formatDurationChart(row.elapsed),
    [y1]: y1Smoothed[index],
    ...(y2 ? { [y2]: y2Smoothed?.[index] ?? 0 } : {}),
    maxElapsed,
  }));
}

export function metricHasData(rows: Record<string, unknown>[], metric: TelemetryMetric): boolean {
  return rows.some((row) => {
    const value = Number(row[metric]);
    return Number.isFinite(value) && value !== 0;
  });
}

export const TELEMETRY_METRICS = METRICS;

export const TELEMETRY_METRIC_LABELS: Record<TelemetryMetric, string> = {
  HeartRate: 'Heart rate',
  Cadence: 'Cadence',
  Speed: 'Speed (km/h)',
  Watts: 'Power',
  Altitude: 'Altitude',
};
