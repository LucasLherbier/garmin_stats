import type { TimeRange } from '../types';

export const VOLUME_KEYS: Array<{ value: string; label: string }> = [
  { value: 'last_4', label: '4 weeks' },
  { value: 'last_12', label: '12 weeks' },
  { value: 'last_18', label: '18 weeks' },
  { value: 'last_all', label: 'YTD' },
  { value: 'all_time', label: 'All' },
];

/** Sport pages (/run, /bike, /swim) — no 4-week option. */
export const SPORT_VOLUME_KEYS = VOLUME_KEYS.filter((k) => k.value !== 'last_4');

/** Volume-summary row key used for metric cards (All → widest window available). */
export function volumeKeyToSummaryKey(key: string): string {
  if (key === 'all_time') return 'last_18';
  return key;
}

/** Map filter period to API time range for trends + activities. */
export function volumeKeyToTimeRange(key: string): TimeRange {
  switch (key) {
    case 'last_4':
      return '4_units';
    case 'last_12':
      return '6_units';
    case 'last_18':
    case 'last_all':
      return 'ytd';
    case 'all_time':
      return 'all';
    default:
      return '6_units';
  }
}
