import React, { useState, useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import {
  Camera,
  Detection,
  CongestionCameraMetric,
  VehicleTrajectoryResponse,
} from '../types/api';
import {
  Video,
  Car,
  Activity,
  Flame,
  Crosshair,
} from 'lucide-react';
import { api } from '../services/api';

interface LiveMapViewProps {
  cameras: Camera[];
  recentDetections: Detection[];
  selectedVehiclePlate?: string | null;
  onSelectVehicle: (plate: string) => void;
  onSelectCamera: (cameraId: string) => void;
}

// Controller to re-center map if needed
function MapController({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

export const LiveMapView: React.FC<LiveMapViewProps> = ({
  cameras,
  recentDetections,
  selectedVehiclePlate,
  onSelectVehicle,
  onSelectCamera,
}) => {
  const [showCameras, setShowCameras] = useState(true);
  const [showBreadcrumbs, setShowBreadcrumbs] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const [trajectoryData, setTrajectoryData] = useState<VehicleTrajectoryResponse | null>(null);
  const [congestionMap, setCongestionMap] = useState<Map<string, CongestionCameraMetric>>(new Map());

  const defaultCenter: [number, number] = [28.625, 77.225]; // Delhi NCR center

  // Fetch congestion data periodically
  useEffect(() => {
    const fetchCongestion = async () => {
      try {
        const data = await api.getCongestion();
        const cMap = new Map<string, CongestionCameraMetric>();
        data.cameras.forEach((c) => cMap.set(c.camera_id, c));
        setCongestionMap(cMap);
      } catch {
        // use fallback
      }
    };
    fetchCongestion();
    const interval = setInterval(fetchCongestion, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch trajectory if a vehicle is selected
  useEffect(() => {
    if (!selectedVehiclePlate) {
      setTrajectoryData(null);
      return;
    }
    api
      .getVehicleTrajectory(selectedVehiclePlate)
      .then((data) => setTrajectoryData(data))
      .catch(() => setTrajectoryData(null));
  }, [selectedVehiclePlate]);

  // Create custom DivIcons for cameras
  const createCameraIcon = (cam: Camera, congestion?: CongestionCameraMetric) => {
    const isOffline = cam.status !== 'ACTIVE';
    const isHighTraffic = congestion && (congestion.congestion_level === 'HIGH' || congestion.congestion_level === 'CONGESTED');
    const colorClass = isOffline
      ? 'border-rose-500 bg-rose-950 text-rose-300'
      : isHighTraffic
      ? 'border-amber-500 bg-amber-950 text-amber-300'
      : 'border-cyan-400 bg-[#101522] text-cyan-300';

    const pulseRing = !isOffline
      ? `<div class="absolute -inset-1.5 rounded-full border border-cyan-500/40 animate-ping opacity-60"></div>`
      : '';

    return L.divIcon({
      className: 'custom-camera-marker',
      html: `
        <div class="relative flex items-center justify-center cursor-pointer">
          ${pulseRing}
          <div class="w-8 h-8 rounded-full border-2 ${colorClass} flex flex-col items-center justify-center shadow-lg shadow-black/80 font-mono text-[9px] font-extrabold z-10 transition-transform hover:scale-125">
            <span>${cam.id.replace('CAM-', '')}</span>
          </div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  };

  // Group latest detection positions by camera coordinates for vehicle breadcrumbs
  const vehicleMarkers = useMemo(() => {
    const camLookup = new Map(cameras.map((c) => [c.id, c]));
    // Take latest 15 unique vehicles
    const seen = new Set<string>();
    const list: { detection: Detection; cam: Camera }[] = [];

    for (const det of recentDetections) {
      if (!seen.has(det.plate_number)) {
        seen.add(det.plate_number);
        const c = camLookup.get(det.camera_id);
        if (c) {
          list.push({ detection: det, cam: c });
        }
      }
      if (list.length >= 15) break;
    }
    return list;
  }, [cameras, recentDetections]);

  // Create custom DivIcon for vehicles
  const createVehicleIcon = (det: Detection, isSelected: boolean) => {
    const isSpeeding = det.speed_kmh > 70;
    const border = isSelected
      ? 'border-emerald-400 ring-2 ring-emerald-400 bg-emerald-950'
      : isSpeeding
      ? 'border-rose-500 bg-rose-950'
      : 'border-blue-400 bg-slate-900';

    return L.divIcon({
      className: 'custom-vehicle-marker',
      html: `
        <div class="relative flex items-center justify-center cursor-pointer">
          <div class="w-7 h-7 rounded border ${border} flex items-center justify-center text-[10px] font-mono font-bold text-white shadow-md">
            🚗
          </div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
  };

  return (
    <div className="relative w-full h-[640px] rounded-lg border border-hud-border overflow-hidden bg-[#0a0d14] flex flex-col">
      {/* Map Header / Layer Toggles HUD Bar */}
      <div className="bg-[#101522]/95 backdrop-blur-sm border-b border-hud-border px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-cyan-400 font-mono font-bold text-xs">
            <Crosshair className="w-4 h-4 animate-spin" />
            <span>GIS TACTICAL MAP — DELHI NCR SECTOR MATRIX</span>
          </div>
          {selectedVehiclePlate && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-700 text-cyan-300 font-mono text-xs font-bold">
              <span>TRACKING: {selectedVehiclePlate}</span>
              <button
                onClick={() => onSelectVehicle('')}
                className="text-slate-400 hover:text-white ml-1"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Layer Toggle Pills */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <button
            onClick={() => setShowCameras(!showCameras)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border transition-all ${
              showCameras
                ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            <span>CAMERAS ({cameras.length})</span>
          </button>

          <button
            onClick={() => setShowBreadcrumbs(!showBreadcrumbs)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border transition-all ${
              showBreadcrumbs
                ? 'bg-blue-950/60 border-blue-500/50 text-blue-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <Car className="w-3.5 h-3.5" />
            <span>FLEET VECTORS ({vehicleMarkers.length})</span>
          </button>

          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border transition-all ${
              showHeatmap
                ? 'bg-amber-950/60 border-amber-500/50 text-amber-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>CONGESTION HALOS</span>
          </button>

          <button
            onClick={() => setShowTrajectory(!showTrajectory)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border transition-all ${
              showTrajectory
                ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-300'
                : 'bg-slate-900 border-slate-800 text-slate-500'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>TRAJECTORIES</span>
          </button>
        </div>
      </div>

      {/* Leaflet Map Canvas */}
      <div className="flex-1 w-full h-full relative">
        <MapContainer
          center={defaultCenter}
          zoom={12}
          scrollWheelZoom={true}
          className="w-full h-full dark-map"
          style={{ height: '100%', width: '100%', background: '#0a0d14' }}
        >
          <MapController center={defaultCenter} zoom={12} />

          {/* CartoDB Dark Matter Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            maxZoom={18}
          />

          {/* Camera Checkpoints */}
          {showCameras &&
            cameras.map((cam) => {
              const congestion = congestionMap.get(cam.id);
              const icon = createCameraIcon(cam, congestion);

              return (
                <Marker
                  key={cam.id}
                  position={[cam.latitude, cam.longitude]}
                  icon={icon}
                  eventHandlers={{
                    click: () => onSelectCamera(cam.id),
                  }}
                >
                  <Popup>
                    <div className="font-mono text-xs p-1 space-y-1 text-slate-200">
                      <div className="font-bold text-cyan-400 flex items-center justify-between border-b border-slate-700 pb-1">
                        <span>{cam.id}: {cam.name}</span>
                        <span className={`px-1 rounded text-[9px] ${cam.status === 'ACTIVE' ? 'bg-emerald-900 text-emerald-300' : 'bg-rose-900 text-rose-300'}`}>
                          {cam.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        Zone: <span className="text-slate-100">{cam.zone}</span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        Speed Limit: <span className="text-amber-400 font-bold">{cam.speed_limit_kmh} km/h</span>
                      </div>
                      {congestion && (
                        <div className="text-[11px] text-slate-300">
                          Traffic Flow:{' '}
                          <span className="text-emerald-400 font-bold">
                            {congestion.vehicles_per_minute.toFixed(1)} veh/min
                          </span>{' '}
                          ({congestion.congestion_level})
                        </div>
                      )}
                      <div className="pt-1">
                        <button
                          onClick={() => onSelectCamera(cam.id)}
                          className="w-full py-1 bg-cyan-900 hover:bg-cyan-800 text-cyan-200 rounded text-[10px] font-bold"
                        >
                          OPEN CAMERA FEED &bull; MATRIX
                        </button>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

          {/* Congestion Heatmap / Halo Circles */}
          {showHeatmap &&
            cameras.map((cam) => {
              const metric = congestionMap.get(cam.id);
              const intensity = metric ? metric.intensity : 0.3;
              const color = metric && (metric.congestion_level === 'HIGH' || metric.congestion_level === 'CONGESTED')
                ? '#ef4444'
                : metric && metric.congestion_level === 'MODERATE'
                ? '#f59e0b'
                : '#06b6d4';

              return (
                <CircleMarker
                  key={`halo-${cam.id}`}
                  center={[cam.latitude, cam.longitude]}
                  radius={20 + intensity * 25}
                  pathOptions={{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.15 + intensity * 0.25,
                    weight: 1,
                  }}
                />
              );
            })}

          {/* Active Fleet Breadcrumb Markers */}
          {showBreadcrumbs &&
            vehicleMarkers.map(({ detection: det, cam }) => {
              // Slight random jitter around camera so multiple vehicles don't overlap exactly
              const hash = det.plate_number.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
              const offsetLat = ((hash % 10) - 5) * 0.0015;
              const offsetLng = (((hash * 3) % 10) - 5) * 0.0015;
              const pos: [number, number] = [cam.latitude + offsetLat, cam.longitude + offsetLng];
              const isSelected = selectedVehiclePlate === det.plate_number;

              return (
                <Marker
                  key={`veh-${det.id}`}
                  position={pos}
                  icon={createVehicleIcon(det, isSelected)}
                  eventHandlers={{
                    click: () => onSelectVehicle(det.plate_number),
                  }}
                >
                  <Popup>
                    <div className="font-mono text-xs p-1 space-y-1 text-slate-200">
                      <div className="font-bold text-emerald-400 border-b border-slate-700 pb-1 flex items-center justify-between">
                        <span>{det.plate_number}</span>
                        <span className="text-[10px] text-slate-400">{det.vehicle_type}</span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        Camera: <span className="text-cyan-400">{det.camera_id}</span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        Speed: <span className="text-amber-400 font-bold">{det.speed_kmh.toFixed(0)} km/h</span>
                      </div>
                      <div className="text-[11px] text-slate-300">
                        OCR Conf: <span className="text-emerald-400">{(det.ocr_confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="pt-1">
                        <button
                          onClick={() => onSelectVehicle(det.plate_number)}
                          className="w-full py-1 bg-emerald-900 hover:bg-emerald-800 text-emerald-200 rounded text-[10px] font-bold"
                        >
                          OPEN VEHICLE DOSSIER
                        </button>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

          {/* Reconstructed Trajectory Polyline for Selected Vehicle */}
          {showTrajectory && trajectoryData && trajectoryData.visited_cameras.length > 1 && (
            <>
              <Polyline
                positions={trajectoryData.visited_cameras.map((h) => [h.latitude, h.longitude] as [number, number])}
                pathOptions={{
                  color: '#10b981',
                  weight: 4,
                  dashArray: '6, 6',
                  opacity: 0.85,
                }}
              />
              {/* Highlight checkpoints along trajectory */}
              {trajectoryData.visited_cameras.map((hop, idx) => (
                <CircleMarker
                  key={`hop-${hop.detection_id}-${idx}`}
                  center={[hop.latitude, hop.longitude]}
                  radius={8}
                  pathOptions={{
                    color: '#10b981',
                    fillColor: '#047857',
                    fillOpacity: 0.9,
                    weight: 2,
                  }}
                >
                  <Popup>
                    <div className="font-mono text-xs text-slate-200">
                      <div className="font-bold text-emerald-400">HOP #{idx + 1}: {hop.camera_id}</div>
                      <div>{hop.camera_name}</div>
                      <div className="text-slate-400">{new Date(hop.timestamp).toLocaleTimeString()}</div>
                      <div className="text-amber-400 font-bold">Speed: {hop.speed_kmh.toFixed(0)} km/h</div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </>
          )}
        </MapContainer>

        {/* Map Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-[#101522]/90 backdrop-blur border border-slate-800 rounded p-2.5 text-[10px] font-mono z-[1000] text-slate-300 space-y-1.5 shadow-xl">
          <div className="font-bold text-slate-200 uppercase tracking-wider border-b border-slate-800 pb-1">
            HUD MAP LEGEND
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full border border-cyan-400 bg-[#101522]" />
            <span>Camera Checkpoint (Nominal)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full border border-amber-400 bg-amber-950" />
            <span>High Density / Congestion Surge</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded border border-rose-500 bg-rose-950 text-center" />
            <span>High Speed / Anomaly Warning</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-5 h-0.5 bg-emerald-400" />
            <span>Reconstructed Route Polyline</span>
          </div>
        </div>
      </div>
    </div>
  );
};
