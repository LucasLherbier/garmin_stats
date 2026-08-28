import { Fragment } from 'react';

import type { Tone } from '../utils/tones';

export interface HeatmapCell {
  dow: number;
  slot: 'AM' | 'PM' | 'EV';
  count: number;
}

interface FocusHeatmapProps {
  cells: HeatmapCell[];
  tone?: Tone;
  title?: string;
}

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
const SLOTS: Array<'AM' | 'PM' | 'EV'> = ['AM', 'PM', 'EV'];

function cellKey(dow: number, slot: string) {
  return `${dow}-${slot}`;
}

export function FocusHeatmap({ cells, tone = 'hero', title = 'Focus heatmap' }: FocusHeatmapProps) {
  const lookup = new Map(cells.map((c) => [cellKey(c.dow, c.slot), c.count]));
  const maxCount = Math.max(1, ...cells.map((c) => c.count));

  return (
    <div className={`focus-heatmap tone-${tone}`}>
      <div className="focus-heatmap-head">
        <h3 className="section-title">{title}</h3>
        <span className="focus-heatmap-legend">
          <span className="focus-heatmap-legend-dot" aria-hidden />
          active
        </span>
      </div>
      <div className="focus-heatmap-grid">
        <div className="focus-heatmap-corner" aria-hidden />
        {DAY_LABELS.map((label, i) => (
          <div key={`d-${i}`} className="focus-heatmap-day">
            {label}
          </div>
        ))}
        {SLOTS.map((slot) => (
          <Fragment key={slot}>
            <div className="focus-heatmap-slot">{slot}</div>
            {DAY_LABELS.map((_, dow) => {
              const count = lookup.get(cellKey(dow, slot)) ?? 0;
              const intensity = count / maxCount;
              return (
                <div
                  key={`${slot}-${dow}`}
                  className={`focus-heatmap-cell${count > 0 ? ' active' : ''}`}
                  style={
                    count > 0
                      ? ({ '--heat': String(0.35 + intensity * 0.65) } as React.CSSProperties)
                      : undefined
                  }
                  title={count > 0 ? `${count} session${count === 1 ? '' : 's'}` : undefined}
                />
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
