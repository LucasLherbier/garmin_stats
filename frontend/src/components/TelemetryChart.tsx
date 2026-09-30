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
import { ChartNote } from './ChartNote';
import { formatDurationChart } from '../utils/format';
import {
  metricHasData,
  prepareTelemetryChartData,
  TELEMETRY_METRIC_LABELS,
  TELEMETRY_METRICS,
  type TelemetryMetric,
} from '../utils/telemetry';

interface TelemetryChartProps {
  rows: Record<string, unknown>[];
  sport?: string;
}

type SecondMetric = TelemetryMetric | 'none';

function pickMetrics(rows: Record<string, unknown>[]): TelemetryMetric[] {
  const available = TELEMETRY_METRICS.filter((metric) => metricHasData(rows, metric));
  if (available.length) return available;

  const fallbacks: TelemetryMetric[] = ['HeartRate', 'Altitude'];
  return fallbacks.filter((metric) => metric in (rows[0] ?? {}));
}

function defaultPair(metrics: TelemetryMetric[], sport?: string): [TelemetryMetric, SecondMetric] {
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

export function TelemetryChart({ rows, sport }: TelemetryChartProps) {
  const metrics = useMemo(() => pickMetrics(rows), [rows]);
  const [y1, setY1] = useState<TelemetryMetric | null>(null);
  const [y2, setY2] = useState<SecondMetric | null>(null);
  const [defaultY1, defaultY2] = useMemo(() => defaultPair(metrics, sport), [metrics, sport]);

  const activeY1 = y1 && metrics.includes(y1) ? y1 : defaultY1;
  const activeY2: SecondMetric =
    y2 === 'none' || (y2 && metrics.includes(y2))
      ? y2 ?? defaultY2
      : defaultY2;
  const secondMetric = activeY2 === 'none' ? null : activeY2;

  const data = useMemo(
    () => prepareTelemetryChartData(rows, activeY1, secondMetric, 30),
    [rows, activeY1, secondMetric],
  );

  const maxElapsed = data.length ? Number(data[data.length - 1].maxElapsed ?? data[data.length - 1].elapsed) : 0;
  const xTicks = useMemo(() => {
    if (maxElapsed <= 0) return [0];
    const count = 5;
    return Array.from({ length: count }, (_, index) => (maxElapsed * index) / (count - 1));
  }, [maxElapsed]);

  if (!rows.length || !metrics.length) return null;

  return (
    <div className="chart-card">
      <h3 className="section-title">Telemetry</h3>
      <ChartNote
        parts={[
          '30 s rolling average',
          'Full activity duration on the x-axis',
        ]}
      />
      {!metrics.includes('Cadence') && metrics.includes('Speed') && sport === 'running' ? (
        <ChartNote parts={['Cadence not in TCX — showing speed instead']} />
      ) : null}
      <div className="metric-grid" style={{ marginBottom: 10 }}>
        <select
          className="form-field"
          value={activeY1}
          onChange={(e) => setY1(e.target.value as TelemetryMetric)}
        >
          {metrics.map((m) => (
            <option key={m} value={m}>{TELEMETRY_METRIC_LABELS[m] ?? m}</option>
          ))}
        </select>
        <select
          className="form-field"
          value={activeY2}
          onChange={(e) => setY2(e.target.value === 'none' ? 'none' : (e.target.value as TelemetryMetric))}
        >
          <option value="none">—</option>
          {metrics.map((m) => (
            <option key={m} value={m}>{TELEMETRY_METRIC_LABELS[m] ?? m}</option>
          ))}
        </select>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 2, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="elapsed"
            type="number"
            domain={[0, maxElapsed || 'auto']}
            ticks={xTicks}
            tickFormatter={(value) => formatDurationChart(Number(value))}
            tick={{ fill: CHART.tick, fontSize: 9 }}
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
          <Tooltip
            contentStyle={tooltipStyle}
            labelFormatter={(value) => formatDurationChart(Number(value))}
          />
          <Legend wrapperStyle={{ fontSize: 10, color: CHART.tick }} />
          <Line yAxisId="left" type="monotone" dataKey={activeY1} name={TELEMETRY_METRIC_LABELS[activeY1] ?? activeY1} stroke={CHART.accent} dot={false} strokeWidth={2} />
          {secondMetric ? (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey={secondMetric}
              name={TELEMETRY_METRIC_LABELS[secondMetric] ?? secondMetric}
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
