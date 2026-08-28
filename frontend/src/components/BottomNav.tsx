import { NavLink } from 'react-router-dom';

const items = [
  {
    to: '/stats',
    label: 'Stats',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M3 3v18h18" /><path d="M7 16l4-8 4 5 5-9" /></svg>
    ),
  },
  {
    to: '/',
    label: 'Home',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1V9.5z" /></svg>
    ),
  },
  {
    to: '/run',
    label: 'Run',
    icon: (
      <svg viewBox="0 0 24 24"><circle cx="14" cy="4" r="2" /><path d="M12 8 8 22h3l2-7 3 2 2 5h3l-3.5-9L12 8z" /></svg>
    ),
  },
  {
    to: '/swim',
    label: 'Swim',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M2 12h4l2-3 4 6 4-6 2 3h4" /><path d="M2 17h20" /></svg>
    ),
  },
  {
    to: '/bike',
    label: 'Bike',
    icon: (
      <svg viewBox="0 0 24 24"><circle cx="5.5" cy="17" r="3.5" /><circle cx="18.5" cy="17" r="3.5" /><path d="M9 17h6M12 6l3 5M9 11l-2 6M15 11l2 6" /></svg>
    ),
  },
  {
    to: '/race',
    label: 'Race',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M4 15V9M4 15a2 2 0 1 0 4 0V9a2 2 0 1 0-4 0v6zm8 0V5M12 15a2 2 0 1 0 4 0V5a2 2 0 1 0-4 0v10zm8 0v-4M20 15a2 2 0 1 0 4 0v-4a2 2 0 1 0-4 0v4z" /></svg>
    ),
  },
  {
    to: '/results',
    label: 'Results',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M8 21h8M12 17v4M7 4h10l1 7H6L7 4zM9 11v6M15 11v6" /></svg>
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
          {item.icon}
        </NavLink>
      ))}
    </nav>
  );
}
