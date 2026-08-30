import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { CHART, tooltipStyle } from '../chartTheme';
import { formatDurationChart } from '../utils/format';

export interface VolumeStackRow {
  time_period: string;
  activityTypeGrouped: string;
  duration: number;
  formatted_duration?: string;
}

interface VolumeStackChartProps {
  rows: VolumeStackRow[];
  totals: Array<{ time_period: string; formatted_total: string }>;
  sportColors: Record<string, string>;
  yTicks?: Array<{ value: number; label: string }>;
  yMax?: number;
  title?: string;
  horizontal?: boolean;
}

function safeDuration(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

export function VolumeStackChart({
  rows,
  sportColors,
  yTicks,
  yMax,
  title,
  horizontal = false,
}: VolumeStackChartProps) {
  if (!rows.length) {
    return <div className="empty">No training load data.</div>;
  }

  const periods = [...new Set(rows.map((r) => r.time_period))].sort();
  const sports = [...new Set(rows.map((r) => r.activityTypeGrouped))];

  const chartData = periods.map((period) => {
    const entry: Record<string, string | number> = {
      time_period: period.slice(5, 10).replace('-', '/'),
      _raw_period: period,
    };
    for (const sport of sports) {
      const match = rows.find(
        (r) => r.time_period === period && r.activityTypeGrouped === sport,
      );
      entry[sport] = safeDuration(match?.duration);
      entry[`${sport}__formatted`] = match?.formatted_duration ?? '0:00:00';
    }
    return entry;
  });

  const periodTotals = chartData.map((entry) =>
    sports.reduce((sum, sport) => sum + safeDuration(entry[sport]), 0),
  );
  const averageTotal =
    periodTotals.reduce((sum, value) => sum + value, 0) / Math.max(periodTotals.length, 1);

  const tickLabels = yTicks?.length
    ? Object.fromEntries(yTicks.map((t) => [t.value, t.label]))
    : undefined;

  const formatDurationTick = (value: number) => tickLabels?.[value] ?? String(value);

  const tooltipFormatter = (value: unknown, name: unknown, item: { payload?: Record<string, unknown> }) => {
    const sport = String(name ?? '');
    const formatted = item.payload?.[`${sport}__formatted`];
    if (typeof formatted === 'string' && formatted) return [formatted, sport];
    const num = safeDuration(value);
    return [formatDurationChart(num), sport];
  };

  const barGradId = 'stackBarPurple';

  return (
    <div className="chart-card">
      {title ? <h3 className="section-title">{title}</h3> : null}
      <ResponsiveContainer width="100%" height={horizontal ? Math.max(240, periods.length * 42) : 240}>
        {horizontal ? (
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
          >
            <defs>
              <linearGradient id={barGradId} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={CHART.chartBright} />
                <stop offset="50%" stopColor={CHART.chartMid} />
                <stop offset="100%" stopColor={CHART.chartDeep} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={CHART.grid} horizontal={false} />
            <XAxis
              type="number"
              domain={[0, yMax ?? 'auto']}
              ticks={yTicks?.map((t) => t.value)}
              tickFormatter={formatDurationTick}
              tick={{ fill: CHART.tick, fontSize: 9 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="time_period"
              tick={{ fill: CHART.tick, fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={tooltipFormatter} />
            <Legend wrapperStyle={{ fontSize: 10, color: CHART.tick }} />
            <ReferenceLine
              x={averageTotal}
              stroke={CHART.tick}
              strokeDasharray="6 4"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
              label={{
                value: formatDurationChart(averageTotal),
                position: 'insideTop',
                fill: CHART.tick,
                fontSize: 9,
              }}
            />
            {sports.map((sport) => (
              <Bar
                key={sport}
                dataKey={sport}
                stackId="volume"
                fill={sportColors[sport] ?? `url(#${barGradId})`}
                radius={[0, 3, 3, 0]}
              />
            ))}
          </BarChart>
        ) : (
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: 2, bottom: 0 }}>
            <defs>
              <linearGradient id={barGradId} x1="0" y1="1" x2="0" y2="0">
                <stop offset="0%" stopColor={CHART.chartDeep} />
                <stop offset="50%" stopColor={CHART.chartMid} />
                <stop offset="100%" stopColor={CHART.chartBright} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={CHART.grid} vertical={false} />
            <XAxis
              dataKey="time_period"
              tick={{ fill: CHART.tick, fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, yMax ?? 'auto']}
              ticks={yTicks?.map((t) => t.value)}
              tickFormatter={formatDurationTick}
              tick={{ fill: CHART.tick, fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              width={52}
            />
            <Tooltip contentStyle={tooltipStyle} formatter={tooltipFormatter} />
            <Legend wrapperStyle={{ fontSize: 10, color: CHART.tick }} />
            <ReferenceLine
              y={averageTotal}
              stroke={CHART.tick}
              strokeDasharray="6 4"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
              label={{
                value: formatDurationChart(averageTotal),
                position: 'insideTopRight',
                fill: CHART.tick,
                fontSize: 9,
              }}
            />
            {sports.map((sport) => (
              <Bar
                key={sport}
                dataKey={sport}
                stackId="volume"
                fill={sportColors[sport] ?? `url(#${barGradId})`}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
