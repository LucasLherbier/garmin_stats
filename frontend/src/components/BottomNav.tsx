import { NavLink } from 'react-router-dom';

/** Home=A Stats=C Swim=W2 Bike=B Run=R2 Prep=Z6 Results=B */
const items = [
  {
    to: '/',
    label: 'Dashboard',
    shortLabel: 'Home',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.5z" />
      </svg>
    ),
  },
  {
    to: '/stats',
    label: 'Stats',
    shortLabel: 'Stats',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M4 20V10M10 20V4M16 20v-6M22 20V8" />
      </svg>
    ),
  },
  {
    to: '/swim',
    label: 'Swim',
    shortLabel: 'Swim',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M12 22a7 7 0 0 0 7-7c0-4-7-13-7-13S5 11 5 15a7 7 0 0 0 7 7z" />
      </svg>
    ),
  },
  {
    to: '/bike',
    label: 'Bike',
    shortLabel: 'Bike',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <circle cx="5.5" cy="17.5" r="3.5" />
        <circle cx="18.5" cy="17.5" r="3.5" />
        <path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2" />
      </svg>
    ),
  },
  {
    to: '/run',
    label: 'Run',
    shortLabel: 'Run',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <circle cx="13" cy="4" r="2" />
        <path d="M7 22l3-10 2 3 2-5 3 12" />
      </svg>
    ),
  },
  {
    to: '/race',
    label: 'Race prep',
    shortLabel: 'Prep',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <circle cx="12" cy="12" r="8" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    to: '/results',
    label: 'Results',
    shortLabel: 'Results',
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
        <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
        <path d="M4 22h16" />
        <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22" />
        <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22" />
        <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
      </svg>
    ),
  },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main navigation">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => (isActive ? 'active' : undefined)}
          end={item.to === '/'}
          aria-label={item.label}
          title={item.label}
        >
          <span className="bottom-nav-icon">{item.icon}</span>
          <span className="bottom-nav-label">{item.shortLabel}</span>
        </NavLink>
      ))}
    </nav>
  );
}
