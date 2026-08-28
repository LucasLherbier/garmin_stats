export type TimeRange = '4_units' | '6_units' | 'ytd' | 'all';
export type Granularity = 'week' | 'month';
export type Sport = 'running' | 'cycling' | 'swimming';
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
