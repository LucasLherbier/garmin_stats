import { useMemo } from 'react';
import {
  CartesianGrid,
  LabelList,
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

interface PowerCurveChartProps {
  displayLabels: string[];
  values: number[];
  seconds: number[];
  npValues?: (number | null)[];
}

export function PowerCurveChart({ displayLabels, values, seconds, npValues }: PowerCurveChartProps) {
  if (values.length < 2) {
    return <div className="empty">No power curve for this activity.</div>;
  }

  const data = displayLabels.map((label, i) => {
    const rawNp = npValues?.[i];
    const np =
      rawNp != null && Number(rawNp) > 0 ? Math.round(Number(rawNp)) : null;
    return {
      label,
      seconds: seconds[i],
      watts: values[i],
      np,
    };
  });
  const hasNp = data.some((item) => item.np != null);

  const labelBySeconds = useMemo(
    () => Object.fromEntries(data.map((item) => [item.seconds, item.label])),
    [data],
  );

  const minSeconds = Math.min(...seconds);
  const maxSeconds = Math.max(...seconds);
  return (
    <div className="chart-card">
      <h3 className="section-title">Power curve</h3>
      <ChartNote
        parts={[
          'Peak power: best average over each duration',
          'NP: normalized power for that peak window',
        ]}
      />
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 24, right: 12, left: 2, bottom: 4 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="seconds"
            scale="log"
            domain={[minSeconds, maxSeconds]}
            type="number"
            allowDataOverflow
            ticks={seconds}
            tickFormatter={(value) => labelBySeconds[Number(value)] ?? ''}
            tick={{ fill: CHART.tick, fontSize: 9 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: CHART.tick, fontSize: 10 }}
            width={42}
            tickLine={false}
            axisLine={false}
            label={{ value: 'W', angle: 0, position: 'insideTopLeft', fill: CHART.tick, fontSize: 10 }}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, name) => {
              if (value == null || Number.isNaN(Number(value))) return [null, null];
              const label = name === 'watts' ? 'Peak power' : name === 'np' ? 'NP' : String(name);
              return [`${Math.round(Number(value))} W`, label];
            }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ''}
          />
          <Legend wrapperStyle={{ fontSize: 10, color: CHART.tick }} />
          <Line
            type="monotone"
            dataKey="watts"
            name="Peak power"
            stroke={CHART.accentMid}
            strokeWidth={2.5}
            dot={{ r: 4, fill: CHART.accentMid, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          >
            <LabelList
              dataKey="watts"
              position="top"
              formatter={(value) => `${Math.round(Number(value))}`}
              fill={CHART.tick}
              fontSize={9}
            />
          </Line>
          {hasNp ? (
            <Line
              type="monotone"
              dataKey="np"
              name="NP"
              stroke="#ff6b2c"
              strokeWidth={1.5}
              strokeDasharray="5 4"
              dot={{ r: 3, fill: '#ff6b2c', strokeWidth: 0 }}
              activeDot={{ r: 4 }}
              connectNulls={false}
              legendType="line"
            />
          ) : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
