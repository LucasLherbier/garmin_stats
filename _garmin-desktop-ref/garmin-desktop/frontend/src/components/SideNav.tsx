import { NavLink } from 'react-router-dom';
import { NAV_ITEMS } from './BottomNav';
import { SyncButton } from './SyncButton';

/**
 * Desktop navigation (shown >= 1024 px via theme.css, hidden on mobile).
 * Same tabs, same routes as BottomNav — only the presentation changes.
 */
export function SideNav() {
  return (
    <aside className="side-nav">
      <div className="side-nav-brand">
        <div className="side-nav-logo" aria-hidden>
          <svg viewBox="0 0 24 24">
            <path d="M2 12h4l2.5-6 4 12 2.5-6H22" />
          </svg>
        </div>
        <div>
          <div className="side-nav-title">Garmin Stats</div>
          <div className="side-nav-sub">Training analytics</div>
        </div>
      </div>

      <nav className="side-nav-links" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `side-nav-link${isActive ? ' active' : ''}`
            }
          >
            <span className="side-nav-icon">{item.icon}</span>
            <span className="side-nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="side-nav-footer">
        <SyncButton />
        <div className="side-nav-footer-text">
          <strong>Garmin sync</strong>
          <span>Upload the latest data</span>
        </div>
      </div>
    </aside>
  );
}
