import { useMemo } from 'react';
import {
  hrZoneSlices,
  zoneSecondsFromHrSamples,
  zoneSecondsFromLaps,
} from '../utils/hrZones';
import { metricHasData, type TelemetryMetric } from '../utils/telemetry';

interface HeartRateZonesProps {
  telemetry?: Record<string, unknown>[] | null;
  laps?: Array<{ avg_hr?: unknown; time_s?: unknown; duration_s?: unknown }> | null;
  sport?: string;
}

function sectionTone(sport?: string): string {
  if (sport === 'cycling') return 'tone-bike';
  if (sport === 'running') return 'tone-run';
  if (sport === 'swimming') return 'tone-swim';
  return '';
}

export function HeartRateZones({ telemetry, laps, sport }: HeartRateZonesProps) {
  const slices = useMemo(() => {
    if (telemetry?.length && metricHasData(telemetry, 'HeartRate' as TelemetryMetric)) {
      const samples = telemetry
        .map((row) => Number(row.HeartRate))
        .filter((hr) => Number.isFinite(hr) && hr > 0);
      return hrZoneSlices(zoneSecondsFromHrSamples(samples));
    }
    if (laps?.length) {
      return hrZoneSlices(zoneSecondsFromLaps(laps));
    }
    return [];
  }, [telemetry, laps]);

  if (!slices.length) return null;

  return (
    <section className={`section-card ${sectionTone(sport)}`.trim()}>
      <h3 className="section-title">Heart Rate Zones</h3>
      <div className="hr-zones-bar" aria-hidden>
        {slices.map((slice) => (
          <div
            key={slice.zone}
            className="hr-zones-segment"
            style={{ flexGrow: slice.seconds, background: slice.color }}
          >
            {slice.pct >= 3 ? (
              <>
                <span className="hr-zones-zone">Z{slice.zone}</span>
                <span className="hr-zones-pct">{slice.pct}%</span>
              </>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
