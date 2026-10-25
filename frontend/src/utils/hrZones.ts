/** Match actions/report_charts.py ATHLETE_MAX_HR */
export const ATHLETE_MAX_HR = 195;

const ZONE_COLORS = ['#312e81', '#4338ca', '#6366f1', '#a78bfa', '#fb7185'];

export type HrZoneSlice = { zone: number; seconds: number; pct: number; color: string };

function hrZoneIndex(hr: number, maxHr: number): number {
  const pct = hr / maxHr;
  if (pct < 0.6) return 0;
  if (pct < 0.7) return 1;
  if (pct < 0.8) return 2;
  if (pct < 0.9) return 3;
  return 4;
}

export function zoneSecondsFromHrSamples(hrValues: number[], maxHr = ATHLETE_MAX_HR): number[] {
  const zoneSeconds = [0, 0, 0, 0, 0];
  for (const hr of hrValues) {
    if (!Number.isFinite(hr) || hr <= 0) continue;
    zoneSeconds[hrZoneIndex(hr, maxHr)] += 1;
  }
  return zoneSeconds;
}

export function zoneSecondsFromLaps(
  laps: Array<{ avg_hr?: unknown; time_s?: unknown; duration_s?: unknown }>,
  maxHr = ATHLETE_MAX_HR,
): number[] {
  const zoneSeconds = [0, 0, 0, 0, 0];
  for (const lap of laps) {
    const hr = Number(lap.avg_hr);
    const dur = Number(lap.time_s ?? lap.duration_s ?? 0);
    if (!Number.isFinite(hr) || hr <= 0 || !Number.isFinite(dur) || dur <= 0) continue;
    zoneSeconds[hrZoneIndex(hr, maxHr)] += dur;
  }
  return zoneSeconds;
}

export function hrZoneSlices(zoneSeconds: number[]): HrZoneSlice[] {
  const total = zoneSeconds.reduce((a, b) => a + b, 0);
  if (total <= 0) return [];
  return zoneSeconds
    .map((seconds, index) => ({
      zone: index + 1,
      seconds,
      pct: Math.round((100 * seconds) / total),
      color: ZONE_COLORS[index],
    }))
    .filter((slice) => slice.seconds > 0);
}
