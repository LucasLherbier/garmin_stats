import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { CHART, formatChartValue, tooltipStyle } from '../chartTheme';
import { ChartNote } from './ChartNote';
import { buildHrvChartRows, HRV_BASELINE_WINDOW_DAYS, HRV_BAND_PCT } from '../utils/hrvBaseline';

const RECOVERY_FILL = 'rgba(34, 197, 94, 0.28)';
const RECOVERY_STROKE = 'rgba(74, 222, 128, 0.45)';
const BASELINE_STROKE = 'rgba(74, 222, 128, 0.65)';

interface HrvRecoveryChartProps {
  points: Array<{ time_period: string; value: number }>;
  title?: string;
  height?: number;
}

export function HrvRecoveryChart({ points, title = 'HRV', height = 148 }: HrvRecoveryChartProps) {
  const data = buildHrvChartRows(points);

  if (!data.length) {
    return <div className="empty">No chart data for this range.</div>;
  }

  const chartMargin =
    height <= 150 ? { top: 4, right: 6, left: 0, bottom: 0 } : { top: 12, right: 8, left: 2, bottom: 0 };

  return (
    <div className="chart-card">
      {title ? <h3 className="section-title">{title}</h3> : null}
      <ChartNote
        parts={[
          `Green band: ±${Math.round(HRV_BAND_PCT * 100)}% of your ${HRV_BASELINE_WINDOW_DAYS}-day rolling baseline (prior days only)`,
          'Typical normal recovery zone',
        ]}
      />
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={chartMargin}>
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
            width={46}
            tickFormatter={(v) => formatChartValue(Number(v), 0)}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0]?.payload as (typeof data)[number];
              return (
                <div style={tooltipStyle}>
                  <div style={{ marginBottom: 6, color: CHART.tick }}>Day {label}</div>
                  <div>HRV: {formatChartValue(row.value, 0)} ms</div>
                  {row.baseline != null ? (
                    <>
                      <div>Baseline: {formatChartValue(row.baseline, 0)} ms</div>
                      <div>
                        Normal: {formatChartValue(row.bandLow ?? 0, 0)}–
                        {formatChartValue(row.bandHigh ?? 0, 0)} ms
                      </div>
                    </>
                  ) : (
                    <div style={{ color: CHART.tick, marginTop: 4 }}>
                      Baseline builds after {HRV_BASELINE_WINDOW_DAYS} prior day(s) of data
                    </div>
                  )}
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="bandBase"
            stackId="recovery"
            stroke="none"
            fill="transparent"
            connectNulls={false}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="bandWidth"
            stackId="recovery"
            stroke={RECOVERY_STROKE}
            strokeWidth={1}
            fill={RECOVERY_FILL}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="baseline"
            stroke={BASELINE_STROKE}
            strokeWidth={1.5}
            strokeDasharray="5 4"
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#06b6d4"
            strokeWidth={2}
            connectNulls={false}
            dot={{
              r: 4,
              fill: '#22d3ee',
              stroke: '#0a0a0a',
              strokeWidth: 2,
            }}
            activeDot={{
              r: 6,
              fill: '#22d3ee',
              stroke: '#fff',
              strokeWidth: 2,
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
