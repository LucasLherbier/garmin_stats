import { MetricCard } from './MetricCard';
import type { Sport } from '../types';
import { formatDuration, formatSpeedKmh, paceFromTotals } from '../utils/format';
import type { Tone } from '../utils/tones';

interface SportSummaryMetricsProps {
  sport: Sport;
  distanceKm: number;
  durationSec: number;
  sessions: number;
  averageHr: number;
  elevationGainM: number;
  averageSwolf?: number;
  avgNpW?: number;
  tint?: Tone;
}

type MetricDef = {
  key: string;
  label: string;
  value: string;
  icon: 'distance' | 'duration' | 'sessions' | 'heart' | 'elevation' | 'speed';
};

function buildRows(
  sport: Sport,
  props: Omit<SportSummaryMetricsProps, 'sport' | 'tint'>,
): [MetricDef[], MetricDef[]] {
  const duration = formatDuration(props.durationSec);
  const distance =
    props.distanceKm > 0 ? `${props.distanceKm.toFixed(1)} km` : '—';
  const elevation =
    props.elevationGainM > 0 ? `${Math.round(props.elevationGainM)} m` : '—';
  const sessions = String(props.sessions);
  const hr =
    props.averageHr > 0 ? `${Math.round(props.averageHr)} bpm` : '—';

  if (sport === 'swimming') {
    const swolf =
      props.averageSwolf && props.averageSwolf > 0
        ? String(Math.round(props.averageSwolf))
        : '—';
    const speed = formatSpeedKmh(props.distanceKm, props.durationSec);
    return [
      [
        { key: 'distance', label: 'Distance', value: distance, icon: 'distance' },
        { key: 'duration', label: 'Duration', value: duration, icon: 'duration' },
        { key: 'swolf', label: 'SWOLF', value: swolf, icon: 'speed' },
      ],
      [
        { key: 'sessions', label: 'Sessions', value: sessions, icon: 'sessions' },
        { key: 'hr', label: 'Avg HR', value: hr, icon: 'heart' },
        { key: 'speed', label: 'Speed', value: speed, icon: 'speed' },
      ],
    ];
  }

  if (sport === 'cycling') {
    const np =
      props.avgNpW && props.avgNpW > 0 ? `${Math.round(props.avgNpW)} W` : '—';
    return [
      [
        { key: 'distance', label: 'Distance', value: distance, icon: 'distance' },
        { key: 'duration', label: 'Duration', value: duration, icon: 'duration' },
        { key: 'elevation', label: 'Elev gain', value: elevation, icon: 'elevation' },
      ],
      [
        { key: 'sessions', label: 'Sessions', value: sessions, icon: 'sessions' },
        { key: 'hr', label: 'Avg HR', value: hr, icon: 'heart' },
        { key: 'np', label: 'NP avg', value: np, icon: 'speed' },
      ],
    ];
  }

  const pace = paceFromTotals(props.distanceKm, props.durationSec);
  return [
    [
      { key: 'distance', label: 'Distance', value: distance, icon: 'distance' },
      { key: 'duration', label: 'Duration', value: duration, icon: 'duration' },
      { key: 'elevation', label: 'Elev gain', value: elevation, icon: 'elevation' },
    ],
    [
      { key: 'sessions', label: 'Sessions', value: sessions, icon: 'sessions' },
      { key: 'hr', label: 'Avg HR', value: hr, icon: 'heart' },
      { key: 'pace', label: 'Pace', value: pace, icon: 'speed' },
    ],
  ];
}

export function SportSummaryMetrics({
  sport,
  distanceKm,
  durationSec,
  sessions,
  averageHr,
  elevationGainM,
  averageSwolf,
  avgNpW,
  tint = 'hero',
}: SportSummaryMetricsProps) {
  const [row1, row2] = buildRows(sport, {
    distanceKm,
    durationSec,
    sessions,
    averageHr,
    elevationGainM,
    averageSwolf,
    avgNpW,
  });

  return (
    <div className="sport-summary-metrics">
      {[row1, row2].map((row, index) => (
        <div key={index} className="metric-grid cols-3 summary-metrics-row">
          {row.map((metric) => (
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
      ))}
    </div>
  );
}
