import { useMemo } from 'react';

export type CalendarSport = 'swimming' | 'cycling' | 'running' | 'gym' | 'other';

export interface CalendarActivity {
  day: number;
  sport: CalendarSport;
  slot: 'AM' | 'PM' | 'EV';
}

interface ActivityMonthCalendarProps {
  year: number;
  month: number;
  activities: CalendarActivity[];
  title?: string;
  onPrevMonth?: () => void;
  onNextMonth?: () => void;
  canNextMonth?: boolean;
}

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

const LEGEND: Array<{ sport: CalendarSport; label: string; shape: 'circle' | 'square' | 'line' }> = [
  { sport: 'swimming', label: 'Swim', shape: 'circle' },
  { sport: 'running', label: 'Run', shape: 'square' },
  { sport: 'cycling', label: 'Bike', shape: 'line' },
  { sport: 'gym', label: 'Gym', shape: 'square' },
  { sport: 'other', label: 'Other', shape: 'line' },
];

const SLOT_ROW: Record<CalendarActivity['slot'], number> = {
  AM: 0,
  PM: 1,
  EV: 2,
};

function monthLabel(year: number, month: number) {
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  });
}

function calendarCells(year: number, month: number) {
  const firstDow = (new Date(year, month - 1, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells: Array<{ day: number | null; key: string }> = [];
  for (let i = 0; i < firstDow; i += 1) {
    cells.push({ day: null, key: `pad-start-${i}` });
  }
  for (let d = 1; d <= daysInMonth; d += 1) {
    cells.push({ day: d, key: `d-${d}` });
  }
  while (cells.length % 7 !== 0) {
    cells.push({ day: null, key: `pad-end-${cells.length}` });
  }
  return cells;
}

function ActivityMarker({ sport, shape }: { sport: CalendarSport; shape: 'circle' | 'square' | 'line' }) {
  return (
    <span
      className={`activity-cal-marker shape-${shape} sport-${sport}`}
      aria-hidden
    />
  );
}

export function ActivityMonthCalendar({
  year,
  month,
  activities,
  title = 'Training calendar',
  onPrevMonth,
  onNextMonth,
  canNextMonth = false,
}: ActivityMonthCalendarProps) {
  const byDay = useMemo(() => {
    const map = new Map<number, CalendarActivity[]>();
    for (const a of activities) {
      const list = map.get(a.day) ?? [];
      list.push(a);
      map.set(a.day, list);
    }
    return map;
  }, [activities]);

  const cells = useMemo(() => calendarCells(year, month), [year, month]);
  const today = new Date();
  const isToday = (day: number) =>
    today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === day;

  return (
    <div className="activity-month-cal">
      <div className="activity-month-cal-head">
        <div>
          <h3 className="section-title">{title}</h3>
          <p className="activity-month-cal-sub">{monthLabel(year, month)}</p>
        </div>
        <div className="activity-month-cal-nav">
          <button type="button" className="activity-month-cal-btn" onClick={onPrevMonth} aria-label="Previous month">
            ‹
          </button>
          <button
            type="button"
            className="activity-month-cal-btn"
            onClick={onNextMonth}
            disabled={!canNextMonth}
            aria-label="Next month"
          >
            ›
          </button>
        </div>
      </div>

      <div className="activity-month-cal-legend">
        {LEGEND.map((item) => (
          <span key={item.sport} className="activity-month-cal-legend-item">
            <ActivityMarker sport={item.sport} shape={item.shape} />
            {item.label}
          </span>
        ))}
      </div>

      <div className="activity-month-cal-grid">
        {DAY_LABELS.map((label, i) => (
          <div key={`lbl-${i}`} className="activity-month-cal-dow">
            {label}
          </div>
        ))}
        {cells.map((cell) => {
          if (cell.day === null) {
            return <div key={cell.key} className="activity-month-cal-day empty" aria-hidden />;
          }
          const dayActivities = byDay.get(cell.day) ?? [];
          const sorted = [...dayActivities].sort(
            (a, b) => SLOT_ROW[a.slot] - SLOT_ROW[b.slot],
          );
          const legendShape = (sport: CalendarSport) =>
            LEGEND.find((l) => l.sport === sport)?.shape ?? 'line';

          return (
            <div
              key={cell.key}
              className={`activity-month-cal-day${isToday(cell.day) ? ' today' : ''}${dayActivities.length ? ' has-activity' : ''}`}
              title={
                dayActivities.length
                  ? `${dayActivities.length} session${dayActivities.length === 1 ? '' : 's'}`
                  : undefined
              }
            >
              <span className="activity-month-cal-num">{cell.day}</span>
              <div className="activity-month-cal-markers">
                {sorted.map((a, i) => (
                  <ActivityMarker key={`${cell.day}-${i}`} sport={a.sport} shape={legendShape(a.sport)} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
