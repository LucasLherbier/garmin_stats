import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ActivityDetailPage } from './pages/ActivityDetailPage';
import { OverviewPage } from './pages/OverviewPage';
import { RacePage } from './pages/RacePage';
import { ResultsPage } from './pages/ResultsPage';
import { SportPage } from './pages/SportPage';
import { StatsPage } from './pages/StatsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="stats/activity/:activityId" element={<ActivityDetailPage />} />
          <Route path="race" element={<RacePage />} />
          <Route
            path="run"
            element={
              <SportPage sport="running" routePrefix="run" title="Run" />
            }
          />
          <Route
            path="swim"
            element={
              <SportPage sport="swimming" routePrefix="swim" title="Swim" />
            }
          />
          <Route
            path="bike"
            element={
              <SportPage sport="cycling" routePrefix="bike" title="Bike" />
            }
          />
          <Route path=":sport/activity/:activityId" element={<ActivityDetailPage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
