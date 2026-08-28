import { Outlet } from 'react-router-dom';
import { BottomNav } from './BottomNav';

export function Layout() {
  return (
    <div className="app-shell">
      <Outlet />
      <div className="bottom-nav-wrap">
        <BottomNav />
      </div>
    </div>
  );
}
