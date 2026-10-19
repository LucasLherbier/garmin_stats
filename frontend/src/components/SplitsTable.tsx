import {
  BIKE_SPLIT_DETAIL_COLUMNS,
  RUN_SPLIT_DETAIL_COLUMNS,
  SPLIT_DETAIL_COLUMNS,
} from '../constants/splitColumns';

export { BIKE_SPLIT_DETAIL_COLUMNS, RUN_SPLIT_DETAIL_COLUMNS, SPLIT_DETAIL_COLUMNS };

interface SplitsTableProps {
  rows: Record<string, unknown>[];
  title?: string;
  /** When set, only these columns are shown (in order). */
  columns?: readonly string[];
}

const PREFERRED_COLUMNS = [
  'Split',
  'Distance',
  'Time',
  'Moving Time',
  'Avg Moving Paces',
  'Avg Moving Pace',
  'Avg Pace',
  'Best Pace',
  'Avg HR',
  'Max HR',
  'Avg Heart Rate',
  'Avg Run Cadence',
  'Avg Bike Cadence',
  'Total Strokes',
  'Swim Stroke',
  'Calories',
  'Elevation Gain',
  'Elev Loss',
  'Avg Speed',
  'Avg Temperature',
  'Avg Power',
  'Normalized Power',
];

function columnOrder(allKeys: string[], fixed?: readonly string[]): string[] {
  if (fixed?.length) {
    return fixed.filter((col) => allKeys.includes(col));
  }
  const preferred = PREFERRED_COLUMNS.filter((c) => allKeys.includes(c));
  const rest = allKeys.filter((c) => !preferred.includes(c)).sort();
  return [...preferred, ...rest];
}

function formatSplitCell(column: string, value: unknown): string {
  if (value == null) return '—';

  if (column === 'Moving Time') {
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) return '—';
      return String(Math.round(value));
    }
    return String(value).replace(/\.\d+$/, '');
  }

  if (column === 'Time') {
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) return '—';
      return value.toFixed(1);
    }
    const text = String(value);
    const match = text.match(/^(.+?)(\.\d+)?$/);
    if (!match) return text;
    if (!match[2]) return text;
    const fraction = match[2].slice(1);
    return `${match[1]}.${fraction.charAt(0) ?? '0'}`;
  }

  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—';
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return String(value);
}

function filterSplitRows(rows: Record<string, unknown>[]): Record<string, unknown>[] {
  return rows.filter((row) => {
    const split = String(row.Split ?? '').trim().toLowerCase();
    return split && split !== 'summary' && split !== 'total';
  });
}

export function SplitsTable({ rows, title, columns: fixedColumns }: SplitsTableProps) {
  const filtered = filterSplitRows(rows);
  if (!filtered.length) return null;

  const allKeys = [
    ...new Set(filtered.flatMap((row) => Object.keys(row).filter((k) => !k.startsWith('_')))),
  ];
  const columns = columnOrder(allKeys, fixedColumns);
  if (!columns.length) return null;

  const isDetail = fixedColumns != null;

  return (
    <section className={`section-card splits-section ${isDetail ? 'splits-section--detail' : ''}`.trim()}>
      {title ? <h3 className="section-title">{title}</h3> : null}
      <div className="splits-table-wrap">
        <table className={`splits-table ${isDetail ? 'detail-splits-table' : ''}`.trim()}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatSplitCell(col, row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

