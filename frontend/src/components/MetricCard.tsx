import { MetricIcon, type IconName } from './Icons';
import { cx, type Tone } from '../utils/tones';

interface MetricCardProps {
  label: string;
  value: string;
  delta?: string;
  icon?: IconName | string;
  negativeDelta?: boolean;
  compact?: boolean;
  showChevron?: boolean;
  hideLabel?: boolean;
  centered?: boolean;
  /** Subtle sport tint — use sparingly (e.g. dashboard hero only). */
  tint?: Tone;
}

export function MetricCard({
  label,
  value,
  delta,
  icon,
  negativeDelta,
  compact,
  showChevron,
  hideLabel,
  centered,
  tint,
}: MetricCardProps) {
  const hasIcon = Boolean(icon);
  const showTextLabel = !hideLabel && (hasIcon ? Boolean(label) : true);

  return (
    <div
      className={cx(
        'metric-card',
        compact && 'compact',
        centered && 'centered',
        tint && `metric-card--${tint}`,
      )}
    >
      {centered ? (
        <>
          {hasIcon ? (
            <div className="icon-badge" aria-hidden>
              <MetricIcon name={icon} fallbackEmoji={typeof icon === 'string' ? icon : undefined} />
            </div>
          ) : null}
          <div className="value">{value}</div>
          {showTextLabel ? <div className="label">{label}</div> : null}
          {delta ? (
            <div className={cx('delta', negativeDelta && 'negative')}>{delta}</div>
          ) : null}
        </>
      ) : (
        <>
      <div className="metric-card-top">
        {hasIcon ? (
          <div className="icon-badge" aria-hidden>
            <MetricIcon name={icon} fallbackEmoji={typeof icon === 'string' ? icon : undefined} />
          </div>
        ) : (
          <div className="label">{label}</div>
        )}
        {showChevron ? (
          <div className="chevron" aria-hidden>
            ›
          </div>
        ) : null}
      </div>
      {showTextLabel ? <div className="label">{label}</div> : null}
      <div className="value">{value}</div>
      {delta ? (
        <div className={cx('delta', negativeDelta && 'negative')}>{delta}</div>
      ) : null}
        </>
      )}
    </div>
  );
}
