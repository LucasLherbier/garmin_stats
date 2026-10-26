import { Outlet } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { SideNav } from './SideNav';

export function Layout() {
  return (
    <div className="app-shell">
      <SideNav />
      <Outlet />
      <div className="bottom-nav-wrap">
        <BottomNav />
      </div>
    </div>
  );
}
