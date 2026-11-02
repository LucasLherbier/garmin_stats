import { cx, type Tone } from '../utils/tones';

interface ExplorerStatBlockProps {
  title: string;
  total: string;
  weeklyAvg: string;
  tint?: Tone;
  /** Home explorer: two neutral cells (total + weekly), no sport-colored borders. */
  layout?: 'combined' | 'split';
}

/** YTD stats beside explorer charts — title-first, no icon. */
export function ExplorerStatBlock({
  title,
  total,
  weeklyAvg,
  tint,
  layout = 'combined',
}: ExplorerStatBlockProps) {
  if (layout === 'split') {
    return (
      <div className="explorer-stat-stack">
        <div className="explorer-stat-cell">
          <div className="explorer-stat-label">Total {title}</div>
          <div className="explorer-stat-total">{total}</div>
        </div>
        <div className="explorer-stat-cell">
          <div className="explorer-stat-label">Weekly avg</div>
          <div className="explorer-stat-total">{weeklyAvg}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={cx('explorer-stat-block', tint && `explorer-stat-block--${tint}`)}>
      <div className="explorer-stat-title">{title}</div>
      <div className="explorer-stat-total">{total}</div>
      <div className="explorer-stat-avg">
        <span>Weekly avg</span>
        <strong>{weeklyAvg}</strong>
      </div>
    </div>
  );
}
