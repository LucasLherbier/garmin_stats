/** Bike lap CSV columns — keep in sync with report_html._BIKE_SPLIT_DETAIL_COLUMNS */
export const BIKE_SPLIT_DETAIL_COLUMNS = [
  'Split',
  'Distance',
  'Time',
  'Moving Time',
  'Avg HR',
  'Max HR',
  'Avg Bike Cadence',
  'Calories',
  'Elevation Gain',
  'Elev Loss',
  'Avg Speed',
  'Avg Temperature',
  'Avg Power',
  'Normalized Power',
  'Avg Moving Speed',
  'Max Bike Cadence',
  'Max Power',
  'Max Speed',
] as const;

/** Run lap CSV columns — keep in sync with report_html._RUN_SPLIT_DETAIL_COLUMNS */
export const RUN_SPLIT_DETAIL_COLUMNS = [
  'Split',
  'Distance',
  'Time',
  'Moving Time',
  'Avg Moving Pace',
  'Avg Pace',
  'Best Pace',
  'Avg HR',
  'Max HR',
  'Avg Run Cadence',
  'Calories',
  'Elevation Gain',
  'Elev Loss',
  'Avg Speed',
  'Avg Temperature',
  'Max Run Cadence',
  'Max Speed',
] as const;

/** @deprecated use BIKE_SPLIT_DETAIL_COLUMNS */
export const SPLIT_DETAIL_COLUMNS = BIKE_SPLIT_DETAIL_COLUMNS;
