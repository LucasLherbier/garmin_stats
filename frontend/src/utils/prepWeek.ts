/** Monday 00:00 local for the calendar week containing `date`. */
function mondayOfWeek(date: Date): Date {
  const d = new Date(date);
  d.setHours(12, 0, 0, 0);
  const day = d.getDay();
  const daysFromMonday = (day + 6) % 7;
  d.setDate(d.getDate() - daysFromMonday);
  return d;
}

function parseIsoDate(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T12:00:00`);
}

/** Same cap as API `analysis_end_date`: today or race day, whichever is earlier. */
export function prepReferenceDate(prepEnd: string): Date {
  const end = parseIsoDate(prepEnd);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return today.getTime() < end.getTime() ? today : end;
}

/**
 * 1-based prep week (Monday-aligned), matching training block weeks in the app.
 * Returns null if the reference date is before prep start.
 */
export function prepWeekNumber(prepStart: string, prepEnd: string): number | null {
  const reference = prepReferenceDate(prepEnd);
  const startMonday = mondayOfWeek(parseIsoDate(prepStart));
  const refMonday = mondayOfWeek(reference);
  if (refMonday.getTime() < startMonday.getTime()) {
    return null;
  }
  const msPerWeek = 7 * 24 * 60 * 60 * 1000;
  return Math.floor((refMonday.getTime() - startMonday.getTime()) / msPerWeek) + 1;
}
