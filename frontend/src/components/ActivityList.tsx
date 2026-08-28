import { useNavigate } from 'react-router-dom';
import type { ActivitySummary, Sport } from '../types';
import { formatSpeedKmh } from '../utils/format';

interface ActivityListProps {
  activities: ActivitySummary[];
  routePrefix: string;
  sport?: Sport;
}

function formatFourthColumn(a: ActivitySummary, sport?: Sport): string {
  if (sport === 'running') {
    return a.pace ?? '—';
  }
  if (sport === 'cycling' || sport === 'swimming') {
    if (a.averageSpeed > 0) return `${a.averageSpeed.toFixed(1)} km/h`;
    return formatSpeedKmh(a.distance, parseDurationSec(a.duration));
  }
  if (a.pace) return a.pace;
  if (a.averageSpeed > 0) return `${a.averageSpeed.toFixed(1)} km/h`;
  return '—';
}

function fourthColumnLabel(_sport?: Sport): string {
  return 'Pace';
}

function parseDurationSec(duration: string): number {
  const parts = duration.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

function formatHr(hr: number): string {
  if (!hr || hr <= 0) return '—';
  return String(Math.round(hr));
}

export function ActivityList({ activities, routePrefix, sport }: ActivityListProps) {
  const navigate = useNavigate();
  const paceLabel = fourthColumnLabel(sport);

  const columns = [
    { key: 'date', label: 'Date' },
    { key: 'distance', label: 'Dist' },
    { key: 'time', label: 'Time' },
    { key: 'pace', label: paceLabel },
    { key: 'hr', label: 'HR' },
  ] as const;

  if (!activities.length) {
    return <div className="empty">No activities found.</div>;
  }

  return (
    <div className="race-activity-list">
      {activities.map((a) => {
        const values = {
          date: a.day ?? '—',
          distance: a.distance.toFixed(1),
          time: a.duration,
          pace: formatFourthColumn(a, sport),
          hr: formatHr(a.averageHR),
        };

        return (
          <button
            key={a.activityId}
            type="button"
            className="race-activity-row"
            onClick={() => navigate(`/${routePrefix}/activity/${a.activityId}`)}
          >
            {columns.map((col) => (
              <div key={col.key} className="race-activity-cell">
                <span className="lbl">{col.label}</span>
                <span className="val">{values[col.key]}</span>
              </div>
            ))}
          </button>
        );
      })}
    </div>
  );
}
