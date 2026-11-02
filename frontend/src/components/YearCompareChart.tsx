import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { CHART, formatChartValue, tooltipStyle } from '../chartTheme';
import { formatDurationChart } from '../utils/format';

export interface YearComparePoint {
  week: string;
  prior: number;
  current: number;
}

interface YearCompareChartProps {
  points: YearComparePoint[];
  priorYear: number;
  currentYear: number;
  metric: 'hours' | 'distance_km';
  height?: number;
}

const PRIOR_COLOR = '#f5c14a';
const CURRENT_COLOR = '#a78bfa';

function formatMetric(value: number, metric: 'hours' | 'distance_km') {
  if (metric === 'hours') return formatDurationChart(value);
  return formatChartValue(value, 1);
}

export function YearCompareChart({
  points,
  priorYear,
  currentYear,
  metric,
  height = 240,
}: YearCompareChartProps) {
  if (!points.length) {
    return <div className="empty">No comparison data.</div>;
  }

  const yLabel = metric === 'hours' ? 'Cumulative hours' : 'Cumulative km';

  return (
    <div className="chart-card">
      <h3 className="section-title">Cumulative volume · {priorYear} vs {currentYear}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={points} margin={{ top: 12, right: 8, left: 2, bottom: 0 }}>
          <defs>
            <linearGradient id="yearComparePrior" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={PRIOR_COLOR} stopOpacity={0.35} />
              <stop offset="100%" stopColor={PRIOR_COLOR} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="yearCompareCurrent" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CURRENT_COLOR} stopOpacity={0.4} />
              <stop offset="100%" stopColor={CURRENT_COLOR} stopOpacity={0} />
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
            width={metric === 'hours' ? 52 : 46}
            tickFormatter={(v) => formatMetric(Number(v), metric)}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v, name) => {
              const num = Number(v ?? 0);
              const label = name === 'prior' ? String(priorYear) : String(currentYear);
              const formatted =
                metric === 'hours' ? formatDurationChart(num) : formatChartValue(num, 1);
              return [formatted, label];
            }}
            labelFormatter={(label) => `Week ${label}`}
          />
          <Legend
            verticalAlign="top"
            align="right"
            wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
            formatter={(value) => (value === 'prior' ? String(priorYear) : String(currentYear))}
          />
          <Area
            type="monotone"
            dataKey="prior"
            name="prior"
            stroke={PRIOR_COLOR}
            fill="url(#yearComparePrior)"
            strokeWidth={2}
            dot={false}
          />
          <Area
            type="monotone"
            dataKey="current"
            name="current"
            stroke={CURRENT_COLOR}
            fill="url(#yearCompareCurrent)"
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
      <p className="section-caption">{yLabel} by week (same week index each year).</p>
    </div>
  );
}
