import type { ReactNode, SVGProps } from 'react';

type SvgProps = SVGProps<SVGSVGElement>;

function IconBase({ children, ...props }: SvgProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" {...props}>
      {children}
    </svg>
  );
}

export const Icons = {
  run: (p: SvgProps) => (
    <IconBase {...p}><circle cx="13" cy="4" r="2" /><path d="M7 22l3-10 2 3 2-5 3 12" /></IconBase>
  ),
  swim: (p: SvgProps) => (
    <IconBase {...p}><path d="M12 22a7 7 0 0 0 7-7c0-4-7-13-7-13S5 11 5 15a7 7 0 0 0 7 7z" /></IconBase>
  ),
  bike: (p: SvgProps) => (
    <IconBase {...p}><circle cx="5.5" cy="17.5" r="3.5" /><circle cx="18.5" cy="17.5" r="3.5" /><path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2" /></IconBase>
  ),
  distance: (p: SvgProps) => (
    <IconBase {...p}><path d="M3 3v18h18" /><path d="M7 16l4-8 4 5 5-9" /></IconBase>
  ),
  duration: (p: SvgProps) => (
    <IconBase {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></IconBase>
  ),
  heart: (p: SvgProps) => (
    <IconBase {...p}><path d="M12 20.5 10.5 19C5.5 14.5 3 12.2 3 9.5a4.5 4.5 0 0 1 8-2.7A4.5 4.5 0 0 1 21 9.5c0 2.7-2.5 5-7.5 9.5Z" /></IconBase>
  ),
  sessions: (p: SvgProps) => (
    <IconBase {...p}><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 10h18" /></IconBase>
  ),
  trophy: (p: SvgProps) => (
    <IconBase {...p}><path d="M8 21h8M12 17v4M7 4h10l1 7H6L7 4zM9 11v6M15 11v6" /></IconBase>
  ),
  rank: (p: SvgProps) => (
    <IconBase {...p}><path d="M4 19V5M4 19h16M8 19V9M12 19V13M16 19V7" /></IconBase>
  ),
  speed: (p: SvgProps) => (
    <IconBase {...p}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" /></IconBase>
  ),
  elevation: (p: SvgProps) => (
    <IconBase {...p}><path d="m3 20 7-14 4 8 3-5 4 11H3z" /></IconBase>
  ),
  flame: (p: SvgProps) => (
    <IconBase {...p}><path d="M12 22c4-3 6-6 6-10a6 6 0 0 0-12 0c0 4 2 7 6 10z" /><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z" /></IconBase>
  ),
  temp: (p: SvgProps) => (
    <IconBase {...p}><path d="M14 14.76V5a2 2 0 0 0-4 0v9.76a4 4 0 1 0 4 0z" /></IconBase>
  ),
  week: (p: SvgProps) => (
    <IconBase {...p}><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 10h18" /></IconBase>
  ),
  month: (p: SvgProps) => (
    <IconBase {...p}><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></IconBase>
  ),
  target: (p: SvgProps) => (
    <IconBase {...p}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none" /></IconBase>
  ),
};

export type IconName = keyof typeof Icons;

const EMOJI_MAP: Record<string, IconName> = {
  '🏃': 'run', '🏃‍♂️': 'run',
  '🏊': 'swim', '🏊‍♂️': 'swim', '🌊': 'swim',
  '🚴': 'bike', '🚴‍♂️': 'bike', '🛣️': 'bike',
  '📏': 'distance',
  '⏱️': 'duration', '⏱': 'duration',
  '❤️': 'heart', '❤': 'heart',
  '🏋️': 'sessions', '🏋': 'sessions',
  '🏆': 'trophy',
  '📊': 'rank',
  '⚡': 'speed', '🏁': 'speed',
  '⛰️': 'elevation', '⛰': 'elevation',
  '🔥': 'flame',
  '🌡️': 'temp', '🌡': 'temp',
  '☀️': 'week', '☀': 'week',
  '📅': 'week',
  '🗓️': 'month', '🗓': 'month',
  '🎯': 'target',
  '📆': 'month',
};

export function resolveIcon(input?: string): IconName | undefined {
  if (!input) return undefined;
  if (input in Icons) return input as IconName;
  return EMOJI_MAP[input];
}

interface MetricIconProps {
  name?: IconName | string;
  className?: string;
}

export function MetricIcon({ name, className, fallbackEmoji }: MetricIconProps & { fallbackEmoji?: string }) {
  const resolved = typeof name === 'string' ? resolveIcon(name) : undefined;
  if (!resolved) {
    if (fallbackEmoji) {
      return <span className={className} aria-hidden>{fallbackEmoji}</span>;
    }
    return null;
  }
  const Icon = Icons[resolved];
  return <Icon className={className} aria-hidden />;
}
