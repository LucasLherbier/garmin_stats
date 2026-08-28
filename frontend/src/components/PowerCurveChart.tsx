import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART, tooltipStyle } from '../chartTheme';

interface PowerCurveChartProps {
  displayLabels: string[];
  values: number[];
  seconds: number[];
}

export function PowerCurveChart({ displayLabels, values, seconds }: PowerCurveChartProps) {
  if (values.length < 2) {
    return <div className="empty">No power curve for this activity.</div>;
  }

  const data = displayLabels.map((label, i) => ({
    label,
    seconds: seconds[i],
    watts: values[i],
  }));

  return (
    <div className="chart-card">
      <h3 className="section-title">Power curve</h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 2, bottom: 4 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="seconds"
            scale="log"
            domain={['dataMin', 'dataMax']}
            type="number"
            tickFormatter={(_, index) => data[index]?.label ?? ''}
            ticks={seconds}
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
            formatter={(value) => [`${Math.round(Number(value))} W`, 'Peak power']}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ''}
          />
          <Line
            type="monotone"
            dataKey="watts"
            name="Peak power"
            stroke={CHART.accentMid}
            strokeWidth={2.5}
            dot={{ r: 4, fill: CHART.accentMid, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
