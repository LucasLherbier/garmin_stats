import { useEffect, useState } from 'react';

/** Reactive CSS media query: re-renders when the query result flips. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

/** Desktop shell breakpoint: sidebar + wide pages at >= 1024 px. */
export const DESKTOP_QUERY = '(min-width: 1024px)';

export function useIsDesktop(): boolean {
  return useMediaQuery(DESKTOP_QUERY);
}
