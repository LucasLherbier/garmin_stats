import { MetricCard } from './MetricCard';
import { SegmentedControl } from './SegmentedControl';

export type RaceVolumeKey = 'total' | 'weekly' | '8w';

export interface RaceVolumeRow {
  key: RaceVolumeKey;
  title: string;
  duration: string;
  sessions: string;
  elevation: string;
  swim: string;
  bike: string;
  run: string;
}

const VOLUME_TAB_OPTIONS: Array<{ value: RaceVolumeKey; label: string }> = [
  { value: 'total', label: 'Total' },
  { value: 'weekly', label: 'Weekly' },
  { value: '8w', label: '8W' },
];

interface RaceVolumeMetricsProps {
  rows: RaceVolumeRow[];
  volumeKey: RaceVolumeKey;
  onVolumeKeyChange: (key: RaceVolumeKey) => void;
}

export function RaceVolumeMetrics({
  rows,
  volumeKey,
  onVolumeKeyChange,
}: RaceVolumeMetricsProps) {
  const selected = rows.find((row) => row.key === volumeKey) ?? rows[0];
  if (!selected) return null;

  const row1 = [
    { key: 'duration', label: 'Duration', value: selected.duration, icon: 'duration' as const, tint: 'hero' as const },
    { key: 'sessions', label: 'Sessions', value: selected.sessions, icon: 'sessions' as const, tint: 'hero' as const },
    {
      key: 'elevation',
      label: 'Elev gain',
      value: selected.elevation,
      icon: 'elevation' as const,
      tint: 'hero' as const,
    },
  ];

  const row2 = [
    { key: 'swim', label: 'Swim', value: selected.swim, icon: 'swim' as const, tint: 'swim' as const },
    { key: 'bike', label: 'Bike', value: selected.bike, icon: 'bike' as const, tint: 'bike' as const },
    { key: 'run', label: 'Run', value: selected.run, icon: 'run' as const, tint: 'run' as const },
  ];

  return (
    <>
      <SegmentedControl
        options={VOLUME_TAB_OPTIONS}
        value={volumeKey}
        onChange={onVolumeKeyChange}
      />
      <div className="sport-summary-metrics">
        {[row1, row2].map((row, index) => (
          <div key={index} className="metric-grid cols-3 summary-metrics-row">
            {row.map((metric) => (
              <MetricCard
                key={metric.key}
                label={metric.label}
                value={metric.value}
                icon={metric.icon}
                tint={metric.tint}
                centered
                compact
              />
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
