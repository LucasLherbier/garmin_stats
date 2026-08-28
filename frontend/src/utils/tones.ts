export type Tone = 'swim' | 'bike' | 'run' | 'hero' | 'gold';

const ICON_TONE: Record<string, Tone> = {
  swim: 'swim',
  bike: 'bike',
  run: 'run',
  heart: 'run',
  trophy: 'gold',
  rank: 'gold',
  flame: 'bike',
  speed: 'bike',
  elevation: 'run',
  distance: 'hero',
  duration: 'hero',
  sessions: 'hero',
  target: 'gold',
};

export function toneFromSport(input?: string): Tone {
  const s = (input ?? '').toLowerCase();
  if (s.includes('swim')) return 'swim';
  if (s.includes('cycl') || s.includes('bike')) return 'bike';
  if (s.includes('run')) return 'run';
  return 'hero';
}

export function toneFromIcon(icon?: string): Tone {
  if (!icon) return 'hero';
  return ICON_TONE[icon] ?? toneFromSport(icon);
}

export function toneFromPath(pathname: string): Tone {
  if (pathname.startsWith('/swim')) return 'swim';
  if (pathname.startsWith('/bike')) return 'bike';
  if (pathname.startsWith('/run')) return 'run';
  if (pathname.startsWith('/results') || pathname.startsWith('/stats')) return 'gold';
  if (pathname.startsWith('/race')) return 'hero';
  return 'hero';
}

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}
