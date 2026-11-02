export const VOLUME_KEYS: Array<{ value: string; label: string }> = [
  { value: 'last_4', label: '4 weeks' },
  { value: 'last_12', label: '12 weeks' },
  { value: 'last_18', label: '18 weeks' },
  { value: 'last_all', label: 'YTD' },
  { value: 'all_time', label: 'All' },
];

/** Sport pages (/run, /bike, /swim) — no 4-week option. Values match /sports/{sport}/summary period names. */
export const SPORT_VOLUME_KEYS = VOLUME_KEYS.filter((k) => k.value !== 'last_4');
