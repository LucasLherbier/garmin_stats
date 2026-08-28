import { MapContainer, Polyline, TileLayer } from 'react-leaflet';
import { CHART } from '../chartTheme';
import 'leaflet/dist/leaflet.css';

interface RouteMapProps {
  points: Array<{ lat: number; lon: number }>;
}

export function RouteMap({ points }: RouteMapProps) {
  if (!points || points.length < 2) {
    return null;
  }

  const latLngs = points.map((p) => [p.lat, p.lon] as [number, number]);
  const center = latLngs[Math.floor(latLngs.length / 2)];

  return (
    <div className="map-container map-container--light">
      <MapContainer center={center} zoom={13} scrollWheelZoom={false} zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        <Polyline
          positions={latLngs}
          pathOptions={{ color: CHART.route, weight: 5, opacity: 0.9 }}
        />
      </MapContainer>
    </div>
  );
}
