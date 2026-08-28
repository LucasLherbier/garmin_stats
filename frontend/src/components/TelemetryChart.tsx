import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART, tooltipStyle } from '../chartTheme';

interface TelemetryChartProps {
  rows: Record<string, unknown>[];
  sport?: string;
}

const METRIC_LABELS: Record<string, string> = {
  HeartRate: 'Heart rate',
  Cadence: 'Cadence',
  Speed: 'Speed (km/h)',
  Watts: 'Power',
  Altitude: 'Altitude',
};

const ALL_METRICS = ['HeartRate', 'Cadence', 'Speed', 'Watts', 'Altitude'] as const;
type Metric = (typeof ALL_METRICS)[number];
type SecondMetric = Metric | 'none';

function metricHasData(rows: Record<string, unknown>[], metric: Metric): boolean {
  return rows.some((row) => {
    const value = Number(row[metric]);
    return Number.isFinite(value) && value !== 0;
  });
}

function pickMetrics(rows: Record<string, unknown>[]): Metric[] {
  const available = ALL_METRICS.filter((metric) => metricHasData(rows, metric));
  if (available.length) return available;

  const fallbacks: Metric[] = ['HeartRate', 'Altitude'];
  return fallbacks.filter((metric) => metric in (rows[0] ?? {}));
}

function defaultPair(metrics: Metric[], sport?: string): [Metric, SecondMetric] {
  const y1 =
    sport === 'cycling' && metrics.includes('Watts')
      ? 'Watts'
      : metrics.includes('HeartRate')
        ? 'HeartRate'
        : metrics[0];
  const preferredY2 =
    sport === 'cycling' && metrics.includes('Cadence')
      ? 'Cadence'
      : sport === 'running' && !metrics.includes('Cadence') && metrics.includes('Speed')
        ? 'Speed'
        : metrics.includes('Altitude')
          ? 'Altitude'
          : metrics.includes('Speed')
            ? 'Speed'
            : metrics.find((metric) => metric !== y1) ?? 'none';
  const y2 =
    preferredY2 === y1
      ? metrics.find((metric) => metric !== y1) ?? 'none'
      : preferredY2;
  return [y1, y2];
}

function metricValue(row: Record<string, unknown>, metric: Metric): number {
  const raw = Number(row[metric] ?? 0);
  if (!Number.isFinite(raw)) return 0;
  return metric === 'Speed' ? raw * 3.6 : raw;
}

export function TelemetryChart({ rows, sport }: TelemetryChartProps) {
  const metrics = useMemo(() => pickMetrics(rows), [rows]);
  const [y1, setY1] = useState<Metric | null>(null);
  const [y2, setY2] = useState<SecondMetric | null>(null);
  const [defaultY1, defaultY2] = useMemo(() => defaultPair(metrics, sport), [metrics, sport]);

  const activeY1 = y1 && metrics.includes(y1) ? y1 : defaultY1;
  const activeY2: SecondMetric =
    y2 === 'none' || (y2 && metrics.includes(y2))
      ? y2 ?? defaultY2
      : defaultY2;
  const secondMetric = activeY2 === 'none' ? null : activeY2;

  const data = useMemo(
    () =>
      rows.map((row) => ({
        time: String(row.Time ?? '').slice(11, 19),
        [activeY1]: metricValue(row, activeY1),
        ...(secondMetric ? { [secondMetric]: metricValue(row, secondMetric) } : {}),
      })),
    [rows, activeY1, secondMetric],
  );

  if (!rows.length || !metrics.length) return null;

  return (
    <div className="chart-card">
      <h3 className="section-title">Telemetry</h3>
      {!metrics.includes('Cadence') && metrics.includes('Speed') && sport === 'running' ? (
        <p className="section-caption">Cadence not in TCX — showing speed instead.</p>
      ) : null}
      <div className="metric-grid" style={{ marginBottom: 10 }}>
        <select
          className="form-field"
          value={activeY1}
          onChange={(e) => setY1(e.target.value as Metric)}
        >
          {metrics.map((m) => (
            <option key={m} value={m}>{METRIC_LABELS[m] ?? m}</option>
          ))}
        </select>
        <select
          className="form-field"
          value={activeY2}
          onChange={(e) => setY2(e.target.value === 'none' ? 'none' : (e.target.value as Metric))}
        >
          <option value="none">—</option>
          {metrics.map((m) => (
            <option key={m} value={m}>{METRIC_LABELS[m] ?? m}</option>
          ))}
        </select>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 2, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: CHART.tick, fontSize: 9 }}
            interval="preserveStartEnd"
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: CHART.accent, fontSize: 10 }}
            width={42}
            tickLine={false}
            axisLine={false}
          />
          {secondMetric ? (
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: CHART.chart, fontSize: 10 }}
              width={42}
              tickLine={false}
              axisLine={false}
            />
          ) : null}
          <Tooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 10, color: CHART.tick }} />
          <Line yAxisId="left" type="monotone" dataKey={activeY1} name={METRIC_LABELS[activeY1] ?? activeY1} stroke={CHART.accent} dot={false} strokeWidth={2} />
          {secondMetric ? (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey={secondMetric}
              name={METRIC_LABELS[secondMetric] ?? secondMetric}
              stroke={CHART.chart}
              dot={false}
              strokeWidth={2}
            />
          ) : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
