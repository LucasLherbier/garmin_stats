import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { CHART, formatChartValue, tooltipStyle } from '../chartTheme';
import type { ChartPoint } from '../types';
import { formatDuration, formatDurationChart } from '../utils/format';

export type ChartColorTheme = 'purple' | 'orange';

interface VolumeChartProps {
  points: ChartPoint[];
  yColumn: string;
  yLabel: string;
  title?: string;
  valueFormat?: 'number' | 'duration' | 'distance';
  periodLabel?: string;
  colorTheme?: ChartColorTheme;
  /** Area fill (default) or dot-only line for sparse daily data */
  display?: 'area' | 'dots';
}

const THEME_COLORS = {
  purple: {
    bright: CHART.chartBright,
    mid: CHART.chartMid,
    deep: CHART.chartDeep,
  },
  orange: {
    bright: CHART.accentBright,
    mid: CHART.accentMid,
    deep: CHART.accentDeep,
  },
} as const;

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

function safeNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function VolumeChart({
  points,
  yColumn,
  yLabel,
  title,
  valueFormat,
  periodLabel = 'Week',
  colorTheme = 'purple',
  display = 'area',
}: VolumeChartProps) {
  if (!points.length) {
    return <div className="empty">No chart data for this range.</div>;
  }

  const colors = THEME_COLORS[colorTheme];
  const resolvedFormat = resolveValueFormat(yColumn, valueFormat);
  const data = points.map((p) => ({
    week: formatWeek(String(p.Week ?? '')),
    value: safeNumber(p[yColumn]),
  }));

  const definedValues = data
    .map((point) => point.value)
    .filter((value): value is number => value != null);

  if (!definedValues.length) {
    return <div className="empty">No chart data for this range.</div>;
  }

  const average =
    definedValues.reduce((sum, point) => sum + point, 0) / Math.max(definedValues.length, 1);

  const gradId = `volFill-${yColumn}-${colorTheme}`;

  const commonAxes = (
    <>
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
        formatter={(v) => {
          const num = Number(v ?? 0);
          if (!Number.isFinite(num)) return ['—', yLabel];
          return [
            resolvedFormat === 'duration'
              ? formatDuration(num)
              : formatValue(num, resolvedFormat),
            yLabel,
          ];
        }}
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
    </>
  );

  return (
    <div className="chart-card">
      {title ? <h3 className="section-title">{title}</h3> : null}
      <ResponsiveContainer width="100%" height={210}>
        {display === 'dots' ? (
          <LineChart data={data} margin={{ top: 12, right: 8, left: 2, bottom: 0 }}>
            {commonAxes}
            <Line
              type="monotone"
              dataKey="value"
              stroke={colors.mid}
              strokeWidth={2}
              connectNulls={false}
              dot={{
                r: 4,
                fill: colors.bright,
                stroke: '#0a0a0a',
                strokeWidth: 2,
              }}
              activeDot={{
                r: 6,
                fill: colors.bright,
                stroke: '#fff',
                strokeWidth: 2,
              }}
            />
          </LineChart>
        ) : (
          <AreaChart data={data} margin={{ top: 12, right: 8, left: 2, bottom: 0 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={colors.bright} stopOpacity={0.55} />
                <stop offset="45%" stopColor={colors.mid} stopOpacity={0.28} />
                <stop offset="100%" stopColor={colors.deep} stopOpacity={0} />
              </linearGradient>
              <linearGradient id={`${gradId}-stroke`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={colors.bright} />
                <stop offset="50%" stopColor={colors.mid} />
                <stop offset="100%" stopColor={colors.deep} />
              </linearGradient>
            </defs>
            {commonAxes}
            <Area
              type="monotone"
              dataKey="value"
              stroke={`url(#${gradId}-stroke)`}
              fill={`url(#${gradId})`}
              strokeWidth={2}
              connectNulls
              dot={{
                r: 4,
                fill: colors.bright,
                stroke: '#0a0a0a',
                strokeWidth: 2,
              }}
              activeDot={{
                r: 6,
                fill: colors.bright,
                stroke: '#fff',
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
