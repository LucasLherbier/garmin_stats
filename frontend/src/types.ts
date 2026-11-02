export type TimeRange = '4_units' | '6_units' | 'ytd' | 'all';
export type Granularity = 'week' | 'month';
export type Sport = 'running' | 'cycling' | 'swimming' | 'hiking';
export type OverviewSport = Sport | 'duration';

export interface WeeklyTotals {
  totals: {
    duration: number;
    duration_delta: number;
    trainings: number;
    trainings_delta: number;
  };
    sports: Array<{
    sport: string;
    label: string;
    distance: number;
    distance_delta: number;
    duration?: number;
  }>;
}

export interface ChartPoint {
  Week?: string;
  total_distance?: number;
  total_duration?: number;
  [key: string]: unknown;
}

export interface HomeYtdResponse {
  year: number;
  heatmap: { days: Array<{ date: string; count: number }> };
  weekly: {
    hours: Array<{ week: string; value: number }>;
    swim_km: Array<{ week: string; value: number }>;
    bike_km: Array<{ week: string; value: number }>;
    run_km: Array<{ week: string; value: number }>;
    hike_km: Array<{ week: string; value: number }>;
  };
  summary: {
    total_hours: number;
    weekly_avg_hours: number;
    total_swim_km: number;
    weekly_avg_swim_km: number;
    total_bike_km: number;
    weekly_avg_bike_km: number;
    total_run_km: number;
    weekly_avg_run_km: number;
    total_hike_km: number;
    weekly_avg_hike_km: number;
    total_sessions: number;
    weeks_in_period: number;
  };
}

export interface HistoryVolumeResponse {
  year: number;
  sport: string;
  metric: 'hours' | 'distance_km';
  points: Array<{ week: string; value: number; week_value: number }>;
  summary: { total: number; weekly_avg: number; weeks_in_period: number };
}

export interface YearCompareResponse {
  sport: string;
  metric: 'hours' | 'distance_km';
  prior_year: number;
  current_year: number;
  points: Array<{ week: string; prior: number; current: number }>;
  summary: {
    prior: { total: number; weekly_avg: number; weeks_in_period: number };
    current: { total: number; weekly_avg: number; weeks_in_period: number };
  };
}

/** One period filter of a sport page; `points` are the weeks the metrics sum over. */
export interface SportPeriodSummary {
  name: string;
  period_count: number;
  duration_total: number;
  nb_trainings: number;
  distance_total: number;
  elevationGain: number;
  averageHR: number | null;
  averageSwolf: number | null;
  avgNpW: number | null;
  points: ChartPoint[];
}

export interface ActivitySummary {
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
  averageSwolf?: number;
  trainingEffectLabel?: string;
}

export interface RaceResult {
  name: string;
  date: string;
  location: string;
  bib: string;
  duration: string;
  ranking: string;
  nb_athletes: string;
  ranking_category: string;
  ranking_gender: string;
  link: string;
  swimming?: string;
  swim_pace?: string;
  t1?: string;
  t2?: string;
  cycling?: string;
  cycling_pace?: string;
  running?: string;
  running_pace?: string;
}

export interface ReportActivity {
  activityId: number;
  activityName: string;
  activityTypeGrouped?: string;
  startDisplay: string;
  label: string;
}
