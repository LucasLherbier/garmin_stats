function normalizeApiBase(raw: string | undefined): string {
  const trimmed = (raw ?? '/api').trim().replace(/\/$/, '').replace(/[?#].*$/, '');
  if (!trimmed) return '/api';

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    try {
      const url = new URL(trimmed);
      const path = url.pathname.replace(/\/$/, '') || '/api';
      return `${url.origin}${path.endsWith('/api') ? path : '/api'}`;
    } catch {
      return '/api';
    }
  }

  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_BASE);

function apiUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE}${normalizedPath}`;
  if (!params) return url;

  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${url}?${query}` : url;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const json = JSON.parse(text) as {
        detail?: string | Array<{ msg?: string; loc?: unknown[] }>;
      };
      if (typeof json.detail === 'string') {
        message = json.detail;
      } else if (Array.isArray(json.detail)) {
        message = json.detail.map((item) => item.msg ?? 'Invalid request').join('; ');
      }
    } catch {
      /* use raw response body */
    }
    throw new Error(message || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>(apiUrl('/health')),

  overview: {
    weeklyTotals: () => request<import('../types').WeeklyTotals>(apiUrl('/overview/weekly-totals')),
    volumeChart: (sport: string, timeRange: string, granularity: string) =>
      request<{ points: import('../types').ChartPoint[]; y_column: string }>(
        apiUrl('/overview/volume-chart', { sport, time_range: timeRange, granularity }),
      ),
    benchmarks: (sport: string, granularity: string) =>
      request<{ periods: Record<string, unknown>[] }>(
        apiUrl('/overview/benchmarks', { sport, granularity }),
      ),
    weeklyBreakdown: () =>
      request<{ sports: Record<string, unknown>[] }>(apiUrl('/overview/weekly-breakdown')),
    activityHeatmap: (sport: 'swimming' | 'cycling' | 'running' | 'race') =>
      request<{
        sport: string;
        week_start: string | null;
        cells: Array<{ dow: number; slot: 'AM' | 'PM' | 'EV'; count: number }>;
      }>(apiUrl('/overview/activity-heatmap', { sport })),
  },

  sports: {
    volumeSummary: (sport: string) =>
      request<{ periods: Record<string, unknown>[] }>(apiUrl(`/sports/${sport}/volume-summary`)),
    trends: (sport: string, timeRange: string) =>
      request<{ points: import('../types').ChartPoint[] }>(
        apiUrl(`/sports/${sport}/trends`, { timeRange }),
      ),
    activities: (sport: string, timeRange: string, page = 1) =>
      request<{
        activities: import('../types').ActivitySummary[];
        total: number;
        page: number;
        total_pages: number;
      }>(apiUrl(`/sports/${sport}/activities`, { timeRange, page })),
    activityDetail: (activityId: number) =>
      request<{
        activity: Record<string, unknown>;
        sport: string;
        structure_summary: string | null;
        track: Array<{ lat: number; lon: number }> | null;
        splits: Record<string, unknown>[] | null;
        laps: Record<string, unknown>[] | null;
        telemetry: Record<string, unknown>[] | null;
        power_profile: {
          display_labels: string[];
          values: number[];
          seconds: number[];
        } | null;
        workout_laps: Record<string, unknown>[] | null;
      }>(apiUrl(`/sports/activities/${activityId}`)),
  },

  stats: {
    all: (metric: 'duration' | 'distance') =>
      request<{
        metric_choice: string;
        best_records: Array<{
          sport_name: string;
          records: Array<{ label: string; value: string; date: string; icon: string }>;
        }>;
        volume_records: Array<{
          sport_name: string;
          cards: Array<{ label: string; value: string; period: string; icon: string }>;
        }>;
        summary_rows: Array<{
          label: string;
          activityId: number;
          activityName?: string;
          day?: string;
          distance: number;
          duration?: string;
        }>;
      }>(apiUrl('/stats', { metric })),
  },

  race: {
    list: () => request<{ races: Array<{ index: number; display: string }> }>(apiUrl('/race/races')),
    detail: (raceIndex: number, granularity: string) =>
      request<{
        empty: boolean;
        training_volume: Array<{
          key: 'total' | 'weekly' | '8w';
          title: string;
          duration: string;
          sessions: string;
          elevation: string;
          swim: string;
          bike: string;
          run: string;
        }>;
        volume_icons: {
          duration: string;
          swim: string;
          bike: string;
          run: string;
        };
        distance_charts: Array<{
          name: string;
          display: string;
          emoji: string;
          y_axis_title: string;
          points: Array<{ time_period: string; total_distance: number }>;
        }>;
        training_load: {
          title: string;
          rows: Array<{
            time_period: string;
            activityTypeGrouped: string;
            duration: number;
            formatted_duration?: string;
          }>;
          totals: Array<{ time_period: string; total_duration: number; formatted_total: string }>;
          sport_colors: Record<string, string>;
          y_ticks: Array<{ value: number; label: string }>;
          y_max: number;
        };
        wellness: {
          granularity: string;
          points: Array<{
            time_period: string;
            avg_sleep_score: number | null;
            avg_hrv: number | null;
            avg_resting_hr: number | null;
            avg_body_battery_high: number | null;
            avg_body_battery_low: number | null;
            avg_stress: number | null;
            avg_sleep_duration_sec: number | null;
            day_count: number;
          }>;
          charts: Array<{
            key: string;
            label: string;
            y_axis_title: string;
            color: string;
            points: Array<{ time_period: string; value: number }>;
          }>;
        };
      }>(apiUrl(`/race/${raceIndex}`, { granularity })),
    activities: (
      raceIndex: number,
      sport: 'swimming' | 'cycling' | 'running' | 'gym',
      page = 1,
    ) =>
      request<{
        sport: string;
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
        activities: Array<{
          activityId: number;
          day?: string;
          activityName?: string;
          locationName?: string;
          distance: number;
          duration: string;
          averageHR: number;
          averageSpeed: number;
          pace?: string | null;
          elevationGain: number;
          trainingEffectLabel?: string;
          calories: number;
          sport: string;
        }>;
        summary: {
          distance_km: number;
          duration: string;
          sessions: number;
          average_hr: number;
          elevation_gain_m: number;
        };
      }>(apiUrl(`/race/${raceIndex}/activities`, { sport, page, pageSize: 5 })),
  },

  races: {
    results: () =>
      request<{ triathlon: import('../types').RaceResult[]; running: import('../types').RaceResult[] }>(
        apiUrl('/races/results'),
      ),
  },

  report: {
    sync: (password: string) =>
      request<{ ok: boolean; message: string; workflow_url: string }>(apiUrl('/report/sync'), {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    activitiesByDate: (dateStr: string) =>
      request<{ date: string; activities: import('../types').ReportActivity[] }>(
        apiUrl('/report/activities', { date_str: dateStr }),
      ),
    activityDetail: (activityId: number) =>
      request<{
        activity: Record<string, unknown>;
        sport: string;
        laps: Record<string, unknown>[];
        laps_display: Record<string, unknown>[];
        parse_status?: string;
      }>(apiUrl(`/report/activities/${activityId}`)),
    generate: (activityId: number, splitLists: Array<{ name: string; indices: number[] }>) =>
      request<{
        html: string;
        share_url: string | null;
        share_url_long?: string | null;
        share_expiry_days: number;
      }>(
        apiUrl('/report/generate'),
        {
          method: 'POST',
          body: JSON.stringify({ activity_id: activityId, split_lists: splitLists }),
        },
      ),
    download: (activityId: number) => apiUrl(`/report/download/${activityId}`),
    publish: (activityId: number) =>
      request<{
        html: string;
        share_url: string | null;
        share_url_long?: string | null;
        share_expiry_days: number;
      }>(
        apiUrl('/report/generate'),
        {
          method: 'POST',
          body: JSON.stringify({ activity_id: activityId, split_lists: [] }),
        },
      ),
  },
};
