interface SplitsTableProps {
  rows: Record<string, unknown>[];
  title?: string;
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

function columnOrder(columns: string[]): string[] {
  const preferred = PREFERRED_COLUMNS.filter((c) => columns.includes(c));
  const rest = columns.filter((c) => !preferred.includes(c)).sort();
  return [...preferred, ...rest];
}

function formatCell(value: unknown): string {
  if (value == null) return '—';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '—';
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return String(value);
}

export function SplitsTable({ rows, title }: SplitsTableProps) {
  if (!rows.length) return null;

  const columns = columnOrder([
    ...new Set(rows.flatMap((row) => Object.keys(row).filter((k) => !k.startsWith('_')))),
  ]);

  return (
    <section className="section-card splits-section">
      {title ? <h3 className="section-title">{title}</h3> : null}
      <div className="splits-table-wrap">
        <table className="splits-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
