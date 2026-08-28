import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { CHART, formatChartValue, tooltipStyle } from '../chartTheme';
import type { ChartPoint } from '../types';
import { formatDuration, formatDurationChart } from '../utils/format';

interface VolumeChartProps {
  points: ChartPoint[];
  yColumn: string;
  yLabel: string;
  title?: string;
  valueFormat?: 'number' | 'duration' | 'distance';
  periodLabel?: string;
}

function formatWeek(value: string) {
  if (!value) return '';
  const d = value.slice(5, 10);
  return d.replace('-', '/');
}

function resolveValueFormat(
  yColumn: string,
  valueFormat?: VolumeChartProps['valueFormat'],
): NonNullable<VolumeChartProps['valueFormat']> {
  if (valueFormat) return valueFormat;
  if (yColumn.includes('duration')) return 'duration';
  if (yColumn.includes('distance')) return 'distance';
  return 'number';
}

function formatValue(value: number, format: NonNullable<VolumeChartProps['valueFormat']>): string {
  if (format === 'duration') return formatDurationChart(value);
  if (format === 'distance') return formatChartValue(value, 1);
  return formatChartValue(value, 0);
}

export function VolumeChart({
  points,
  yColumn,
  yLabel,
  title,
  valueFormat,
  periodLabel = 'Week',
}: VolumeChartProps) {
  if (!points.length) {
    return <div className="empty">No chart data for this range.</div>;
  }

  const resolvedFormat = resolveValueFormat(yColumn, valueFormat);
  const data = points.map((p) => ({
    week: formatWeek(String(p.Week ?? '')),
    value: Number(p[yColumn] ?? 0),
  }));

  const average =
    data.reduce((sum, point) => sum + point.value, 0) / Math.max(data.length, 1);

  const gradId = `volFill-${yColumn}`;

  return (
    <div className="chart-card">
      {title ? <h3 className="section-title">{title}</h3> : null}
      <ResponsiveContainer width="100%" height={210}>
        <AreaChart data={data} margin={{ top: 12, right: 8, left: 2, bottom: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART.chartBright} stopOpacity={0.55} />
              <stop offset="45%" stopColor={CHART.chartMid} stopOpacity={0.28} />
              <stop offset="100%" stopColor={CHART.chartDeep} stopOpacity={0} />
            </linearGradient>
            <linearGradient id={`${gradId}-stroke`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={CHART.chartBright} />
              <stop offset="50%" stopColor={CHART.chartMid} />
              <stop offset="100%" stopColor={CHART.chartDeep} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="week"
            tick={{ fill: CHART.tick, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: CHART.tick, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={resolvedFormat === 'duration' ? 52 : 46}
            tickFormatter={(v) => formatValue(Number(v), resolvedFormat)}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v) => [
              resolvedFormat === 'duration'
                ? formatDuration(Number(v ?? 0))
                : formatValue(Number(v ?? 0), resolvedFormat),
              yLabel,
            ]}
            labelFormatter={(label) => `${periodLabel} ${label}`}
          />
          <ReferenceLine
            y={average}
            stroke={CHART.tick}
            strokeDasharray="6 4"
            strokeWidth={1.5}
            ifOverflow="extendDomain"
            label={{
              value: formatValue(average, resolvedFormat),
              position: 'insideTopRight',
              fill: CHART.tick,
              fontSize: 10,
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={`url(#${gradId}-stroke)`}
            fill={`url(#${gradId})`}
            strokeWidth={2}
            dot={{
              r: 4,
              fill: CHART.chartBright,
              stroke: '#0a0a0a',
              strokeWidth: 2,
            }}
            activeDot={{
              r: 6,
              fill: CHART.chartBright,
              stroke: '#fff',
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
