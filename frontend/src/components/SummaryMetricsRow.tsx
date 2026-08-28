import { MetricCard } from './MetricCard';
import type { Tone } from '../utils/tones';

export type SummarySport = 'swimming' | 'cycling' | 'running' | 'gym';

interface SummaryMetricsRowProps {
  sport: SummarySport;
  distanceKm: number;
  duration: string;
  sessions: number;
  averageHr: number;
  elevationGainM: number;
  tint?: Tone;
}

function metricCols(count: number): string {
  if (count <= 2) return 'cols-2';
  if (count === 3) return 'cols-3';
  if (count === 4) return 'cols-4';
  return 'cols-5';
}

export function SummaryMetricsRow({
  sport,
  distanceKm,
  duration,
  sessions,
  averageHr,
  elevationGainM,
  tint = 'hero',
}: SummaryMetricsRowProps) {
  const showDistance = sport !== 'gym';
  const showElevation = sport !== 'swimming' && sport !== 'gym';

  const metrics = [
    showDistance
      ? {
          key: 'distance',
          label: 'Distance',
          value: distanceKm > 0 ? `${distanceKm.toFixed(1)} km` : '—',
          icon: 'distance' as const,
        }
      : null,
    {
      key: 'duration',
      label: 'Duration',
      value: duration,
      icon: 'duration' as const,
    },
    {
      key: 'sessions',
      label: 'Sessions',
      value: String(sessions),
      icon: 'sessions' as const,
    },
    {
      key: 'hr',
      label: 'Avg HR',
      value: averageHr > 0 ? `${Math.round(averageHr)} bpm` : '—',
      icon: 'heart' as const,
    },
    showElevation
      ? {
          key: 'elevation',
          label: 'Elev gain',
          value: elevationGainM > 0 ? `${Math.round(elevationGainM)} m` : '—',
          icon: 'elevation' as const,
        }
      : null,
  ].filter(Boolean) as Array<{
    key: string;
    label: string;
    value: string;
    icon: 'distance' | 'duration' | 'sessions' | 'heart' | 'elevation';
  }>;

  return (
    <div className={`metric-grid ${metricCols(metrics.length)} summary-metrics-row`}>
      {metrics.map((metric) => (
        <MetricCard
          key={metric.key}
          label={metric.label}
          value={metric.value}
          icon={metric.icon}
          tint={tint}
          centered
          compact
        />
      ))}
    </div>
  );
}
