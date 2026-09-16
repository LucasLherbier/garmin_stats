import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ActivityDetailPage } from './pages/ActivityDetailPage';
import { SharedReportPage } from './pages/SharedReportPage';
import { OverviewPage } from './pages/OverviewPage';
import { RacePage } from './pages/RacePage';
import { ResultsPage } from './pages/ResultsPage';
import { SportPage } from './pages/SportPage';
import { StatsPage } from './pages/StatsPage';
import { activityPath } from './utils/paths';

function LegacyActivityRedirect() {
  const { activityId } = useParams<{ activityId: string }>();
  return <Navigate to={activityPath(activityId ?? '')} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/r/:token" element={<SharedReportPage />} />
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="activities/:activityId" element={<ActivityDetailPage />} />
          <Route path="race" element={<RacePage />} />
          <Route path="race/:raceSlug" element={<RacePage />} />
          <Route path="run" element={<SportPage sport="running" title="Run" />} />
          <Route path="swim" element={<SportPage sport="swimming" title="Swim" />} />
          <Route path="bike" element={<SportPage sport="cycling" title="Bike" />} />
          <Route path="stats/activity/:activityId" element={<LegacyActivityRedirect />} />
          <Route path=":sport/activity/:activityId" element={<LegacyActivityRedirect />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
