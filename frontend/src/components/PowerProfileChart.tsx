import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts';
import { CHART } from '../chartTheme';

interface PowerProfileChartProps {
  displayLabels: string[];
  values: number[];
}

export function PowerProfileChart({ displayLabels, values }: PowerProfileChartProps) {
  if (!values.length) {
    return <div className="empty">No power curve for this activity.</div>;
  }

  const data = displayLabels.map((label, i) => ({
    label,
    watts: values[i],
  }));
  const vMax = Math.max(...values);

  return (
    <div className="chart-card">
      <h3 className="section-title">Power profile</h3>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="72%">
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarRadiusAxis
            angle={90}
            domain={[0, vMax]}
            tick={{ fill: CHART.tick, fontSize: 8 }}
            tickCount={5}
            axisLine={false}
            tickFormatter={(v) => `${Math.round(Number(v))}`}
          />
          <PolarAngleAxis
            dataKey="label"
            tick={{ fill: CHART.tick, fontSize: 10 }}
          />
          <Radar
            dataKey="watts"
            stroke={CHART.accent}
            fill={CHART.accentFill}
            strokeWidth={2}
            legendType="none"
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
