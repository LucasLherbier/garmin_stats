/** Prior-day rolling mean used as HRV baseline (Garmin-style short window). */
export const HRV_BASELINE_WINDOW_DAYS = 7;

/** Normal recovery zone: daily HRV within ±10% of rolling baseline. */
export const HRV_BAND_PCT = 0.1;

export interface HrvDailyPoint {
  time_period: string;
  value: number;
}

export interface HrvChartRow {
  week: string;
  value: number;
  baseline: number | null;
  bandLow: number | null;
  bandHigh: number | null;
  bandBase: number;
  bandWidth: number;
}

function formatDayLabel(isoDate: string): string {
  if (!isoDate) return '';
  return isoDate.slice(5, 10).replace('-', '/');
}

export function buildHrvChartRows(points: HrvDailyPoint[]): HrvChartRow[] {
  const sorted = [...points].sort((a, b) => a.time_period.localeCompare(b.time_period));

  return sorted.map((point, index) => {
    const prior = sorted.slice(Math.max(0, index - HRV_BASELINE_WINDOW_DAYS), index);
    const priorValues = prior.map((p) => p.value);
    const baseline =
      priorValues.length > 0
        ? priorValues.reduce((sum, v) => sum + v, 0) / priorValues.length
        : null;

    const bandLow = baseline != null ? baseline * (1 - HRV_BAND_PCT) : null;
    const bandHigh = baseline != null ? baseline * (1 + HRV_BAND_PCT) : null;
    const bandWidth =
      bandLow != null && bandHigh != null ? Math.max(0, bandHigh - bandLow) : 0;

    return {
      week: formatDayLabel(point.time_period),
      value: point.value,
      baseline,
      bandLow,
      bandHigh,
      bandBase: bandLow ?? 0,
      bandWidth,
    };
  });
}
