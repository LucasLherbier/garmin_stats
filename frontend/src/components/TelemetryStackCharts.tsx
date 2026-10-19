import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART, formatChartValue, tooltipStyle } from '../chartTheme';
import { formatDurationChart } from '../utils/format';
import {
  metricHasData,
  prepareTelemetryChartData,
  TELEMETRY_METRIC_LABELS,
  type TelemetryMetric,
} from '../utils/telemetry';

interface TelemetryStackChartsProps {
  rows: Record<string, unknown>[];
  sport: string;
  avgNpW?: number | null;
}

const STACK_CONFIG: Record<
  TelemetryMetric,
  { color: string; fill: string; unit: string; reportLabel: string }
> = {
  HeartRate: {
    color: '#a78bfa',
    fill: 'rgba(167, 139, 250, 0.12)',
    unit: 'bpm',
    reportLabel: 'Heart Rate',
  },
  Altitude: {
    color: '#6366f1',
    fill: 'rgba(99, 102, 241, 0.12)',
    unit: 'm',
    reportLabel: 'Altitude',
  },
  Watts: {
    color: '#ff6b2c',
    fill: 'rgba(255, 107, 44, 0.12)',
    unit: 'W',
    reportLabel: 'Power',
  },
  Speed: {
    color: '#a78bfa',
    fill: 'rgba(167, 139, 250, 0.12)',
    unit: 'km/h',
    reportLabel: 'Speed',
  },
  Cadence: {
    color: '#a78bfa',
    fill: 'rgba(167, 139, 250, 0.12)',
    unit: 'rpm',
    reportLabel: 'Cadence',
  },
};

function stackMetrics(sport: string, rows: Record<string, unknown>[]): TelemetryMetric[] {
  const order: TelemetryMetric[] =
    sport === 'cycling'
      ? ['HeartRate', 'Altitude', 'Watts']
      : ['HeartRate', 'Altitude', 'Speed'];
  return order.filter((metric) => metricHasData(rows, metric));
}

function renderTelemetryTooltip(metric: TelemetryMetric, unit: string, props: unknown) {
  const { active, payload, label } = props as {
    active?: boolean;
    payload?: ReadonlyArray<{ value?: number }>;
    label?: string | number;
  };
  if (!active || !payload?.length) return null;
  const value = Number(payload[0].value);
  return (
    <div style={tooltipStyle}>
      <div style={{ color: CHART.tick, marginBottom: 4 }}>{formatDurationChart(Number(label))}</div>
      <div style={{ fontWeight: 600 }}>
        {TELEMETRY_METRIC_LABELS[metric] ?? metric}: {formatChartValue(value, 0)} {unit}
      </div>
    </div>
  );
}

function SingleTelemetryChart({
  rows,
  metric,
  avgNpW,
  maxElapsed,
  xTicks,
}: {
  rows: Record<string, unknown>[];
  metric: TelemetryMetric;
  avgNpW?: number | null;
  maxElapsed: number;
  xTicks: number[];
}) {
  const config = STACK_CONFIG[metric];
  const data = useMemo(
    () => prepareTelemetryChartData(rows, metric, null, 30),
    [rows, metric],
  );

  const yDomain = useMemo(() => {
    const values = data
      .map((row) => Number((row as Record<string, unknown>)[metric]))
      .filter((v) => Number.isFinite(v));
    if (!values.length) return [0, 1] as [number, number];
    let yMin = Math.min(...values);
    let yMax = Math.max(...values);
    if (metric === 'Watts' && avgNpW != null && avgNpW > 0) {
      yMin = Math.min(yMin, avgNpW);
      yMax = Math.max(yMax, avgNpW);
    }
    const pad = Math.max((yMax - yMin) * 0.08, 1);
    return [yMin - pad, yMax + pad] as [number, number];
  }, [data, metric, avgNpW]);

  return (
    <div className="telemetry-stack-item">
      <div className="telemetry-chart-title">
        {config.reportLabel}
        <span className="telemetry-chart-sub"> · 30s rolling avg</span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="elapsed"
            type="number"
            domain={[0, maxElapsed || 'auto']}
            ticks={xTicks}
            tickFormatter={(value) => formatDurationChart(Number(value))}
            tick={{ fill: '#71717a', fontSize: 9 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={yDomain}
            tick={{ fill: '#71717a', fontSize: 9 }}
            width={40}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `${formatChartValue(Number(value), 0)} ${config.unit}`}
          />
          <Tooltip
            content={(props) => renderTelemetryTooltip(metric, config.unit, props)}
            cursor={{ stroke: 'rgba(255,255,255,0.15)', strokeWidth: 1 }}
          />
          {metric === 'Watts' && avgNpW != null && avgNpW > 0 ? (
            <ReferenceLine
              y={avgNpW}
              stroke="#ff6b2c"
              strokeDasharray="4 3"
              strokeOpacity={0.85}
              label={{
                value: `NP ${avgNpW}W`,
                position: 'insideTopRight',
                fill: '#ff6b2c',
                fontSize: 8,
              }}
            />
          ) : null}
          <Area
            type="monotone"
            dataKey={metric}
            stroke="none"
            fill={config.fill}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey={metric}
            stroke={config.color}
            dot={false}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TelemetryStackCharts({ rows, sport, avgNpW }: TelemetryStackChartsProps) {
  const metrics = useMemo(() => stackMetrics(sport, rows), [sport, rows]);
  const maxElapsed = useMemo(() => {
    if (!metrics.length) return 0;
    const data = prepareTelemetryChartData(rows, metrics[0], null, 30);
    return data.length ? Number(data[data.length - 1].maxElapsed ?? data[data.length - 1].elapsed) : 0;
  }, [rows, metrics]);

  const xTicks = useMemo(() => {
    if (maxElapsed <= 0) return [0];
    const count = 5;
    return Array.from({ length: count }, (_, index) => (maxElapsed * index) / (count - 1));
  }, [maxElapsed]);

  if (!metrics.length) return null;

  const tone = sport === 'cycling' ? 'tone-bike' : sport === 'running' ? 'tone-run' : '';

  return (
    <section className={`section-card chart-card ${tone}`.trim()}>
      <h3 className="section-title">Telemetry</h3>
      <div className="telemetry-stack">
        {metrics.map((metric) => (
          <SingleTelemetryChart
            key={metric}
            rows={rows}
            metric={metric}
            avgNpW={avgNpW}
            maxElapsed={maxElapsed}
            xTicks={xTicks}
          />
        ))}
      </div>
    </section>
  );
}
