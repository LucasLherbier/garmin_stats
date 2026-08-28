export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '0:00:00';
  const s = Math.abs(Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const sign = seconds < 0 ? '-' : '';
  if (h > 0) return `${sign}${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  return `${sign}${m}:${String(sec).padStart(2, '0')}`;
}

export function formatDurationDelta(seconds: number | null | undefined): string {
  if (seconds == null) return '';
  const sign = seconds > 0 ? '+' : seconds < 0 ? '-' : '';
  return `${sign}${formatDuration(Math.abs(seconds))}`;
}

/** Compact hh:mm for chart axes and tooltips. */
export function formatDurationChart(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '0:00';
  const s = Math.abs(Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sign = seconds < 0 ? '-' : '';
  return `${sign}${h}:${String(m).padStart(2, '0')}`;
}

export function formatDistance(km: number, digits = 1): string {
  return `${km.toFixed(digits)} km`;
}

export function formatPaceFromSpeedKmh(speedKmh: number): string {
  if (!speedKmh || speedKmh <= 0) return '—';
  const paceMin = 60 / speedKmh;
  const minutes = Math.floor(paceMin);
  const seconds = Math.floor((paceMin - minutes) * 60);
  return `${minutes}:${String(seconds).padStart(2, '0')} /km`;
}

export function formatSpeedKmh(distanceKm: number, durationSec: number, digits = 1): string {
  if (distanceKm <= 0 || durationSec <= 0) return '—';
  return `${(distanceKm / (durationSec / 3600)).toFixed(digits)} km/h`;
}

export function paceFromTotals(distanceKm: number, durationSec: number): string {
  if (distanceKm <= 0 || durationSec <= 0) return '—';
  return formatPaceFromSpeedKmh(distanceKm / (durationSec / 3600));
}

export function formatDelta(value: number, digits = 2, suffix = ''): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}${suffix}`;
}

export function formatActivityWhen(startTimeLocal?: unknown, day?: unknown): {
  dateLine: string;
  timeLine: string;
} {
  const raw = startTimeLocal ?? day;
  if (!raw) return { dateLine: '—', timeLine: '' };

  const parsed = new Date(String(raw));
  if (Number.isNaN(parsed.getTime())) {
    const dayStr = String(day ?? raw).slice(0, 10);
    return { dateLine: dayStr, timeLine: '' };
  }

  return {
    dateLine: parsed.toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }),
    timeLine: parsed.toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }),
  };
}
