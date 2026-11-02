import { useMemo } from 'react';

export interface HeatmapDay {
  date: string;
  count: number;
}

interface TrainingYtdHeatmapProps {
  year: number;
  days: HeatmapDay[];
  title?: string;
}

const DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function localIso(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function mondayOnOrBefore(d: Date) {
  const x = new Date(d);
  const dow = (x.getDay() + 6) % 7;
  x.setDate(x.getDate() - dow);
  x.setHours(0, 0, 0, 0);
  return x;
}

function level(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count === 3) return 3;
  return 4;
}

export function TrainingYtdHeatmap({ year, days, title = 'When you train' }: TrainingYtdHeatmapProps) {
  const countByDate = useMemo(() => {
    const m = new Map<string, number>();
    for (const d of days) m.set(d.date, d.count);
    return m;
  }, [days]);

  const { gridStart, numWeeks, cells, monthTicks } = useMemo(() => {
    const jan1 = new Date(year, 0, 1);
    const today = new Date();
    const end =
      today.getFullYear() === year
        ? new Date(today.getFullYear(), today.getMonth(), today.getDate())
        : new Date(year, 11, 31);
    const gridStart = mondayOnOrBefore(jan1);
    const msDay = 86400000;
    const numWeeks = Math.ceil((end.getTime() - gridStart.getTime()) / (7 * msDay)) + 1;

    const cells: Array<{
      key: string;
      date: Date | null;
      count: number;
      inYear: boolean;
    }> = [];

    for (let row = 0; row < 7; row += 1) {
      for (let col = 0; col < numWeeks; col += 1) {
        const date = new Date(gridStart.getTime() + (col * 7 + row) * msDay);
        const inYear = date.getFullYear() === year;
        const inRange = inYear && date >= jan1 && date <= end;
        cells.push({
          key: `${col}-${row}`,
          date: inRange ? date : null,
          count: inRange ? (countByDate.get(localIso(date)) ?? 0) : 0,
          inYear: inRange,
        });
      }
    }

    const monthTicks: Array<{ col: number; label: string }> = [];
    for (let m = 0; m < 12; m += 1) {
      const first = new Date(year, m, 1);
      if (first > end) break;
      const col = Math.floor((first.getTime() - gridStart.getTime()) / (7 * msDay));
      monthTicks.push({ col, label: MONTH_LABELS[m] });
    }

    return { numWeeks, cells, monthTicks };
  }, [countByDate, year]);

  return (
    <div className="training-heatmap">
      <div className="training-heatmap-head">
        <h2 className="section-title">{title}</h2>
        <span className="section-caption">YTD {year} · all sessions (incl. hike/walk)</span>
      </div>
      <div className="training-heatmap-scroll">
        <div
          className="training-heatmap-months"
          style={{ gridTemplateColumns: `repeat(${numWeeks}, minmax(4px, 1fr))` }}
        >
          {monthTicks.map((t) => (
            <span key={t.label} className="training-heatmap-month" style={{ gridColumnStart: t.col + 1 }}>
              {t.label}
            </span>
          ))}
        </div>
        <div className="training-heatmap-body">
          <div className="training-heatmap-dows">
            {DOW_LABELS.map((lbl, i) => (
              <span key={lbl} className={i % 2 === 0 ? '' : 'training-heatmap-dow-muted'}>
                {lbl}
              </span>
            ))}
          </div>
          <div
            className="training-heatmap-grid"
            style={{ gridTemplateColumns: `repeat(${numWeeks}, minmax(4px, 1fr))` }}
          >
            {cells.map((cell) => {
              if (!cell.inYear || !cell.date) {
                return <span key={cell.key} className="training-heatmap-cell training-heatmap-cell--pad" />;
              }
              const lv = level(cell.count);
              const titleText = `${cell.date.toLocaleDateString(undefined, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
              })} · ${cell.count} ${cell.count === 1 ? 'session' : 'sessions'}`;
              return (
                <span
                  key={cell.key}
                  className={`training-heatmap-cell training-heatmap-cell--l${lv}`}
                  title={titleText}
                />
              );
            })}
          </div>
        </div>
      </div>
      <div className="training-heatmap-legend" aria-hidden>
        <span>Less</span>
        <span className="training-heatmap-cell training-heatmap-cell--l0" />
        <span className="training-heatmap-cell training-heatmap-cell--l1" />
        <span className="training-heatmap-cell training-heatmap-cell--l2" />
        <span className="training-heatmap-cell training-heatmap-cell--l3" />
        <span className="training-heatmap-cell training-heatmap-cell--l4" />
        <span>More</span>
      </div>
    </div>
  );
}
