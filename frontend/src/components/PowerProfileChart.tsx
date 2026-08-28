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

  return (
    <div className="chart-card">
      <h3 className="section-title">Power profile</h3>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="72%">
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis dataKey="label" tick={{ fill: CHART.tick, fontSize: 10 }} />
          <PolarRadiusAxis tick={{ fill: CHART.tick, fontSize: 9 }} axisLine={false} />
          <Radar
            name="Peak W"
            dataKey="watts"
            stroke={CHART.accent}
            fill={CHART.accentFill}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
