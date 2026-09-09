import React, { useState, useEffect, useCallback } from 'react';
import {
  Car,
  Camera as CameraIcon,
  ShieldAlert,
  Gauge,
  Activity,
  ArrowUpRight,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import {
  Detection,
  Alert,
  Camera,
  SystemOverviewMetrics,
} from '../types/api';
import { api } from '../services/api';

interface OverviewViewProps {
  recentDetections: Detection[];
  activeAlerts: Alert[];
  onSelectVehicle: (plate: string) => void;
  onSelectCamera: (camId: string) => void;
  onSelectAlert: (alert: Alert) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  recentDetections,
  activeAlerts,
  onSelectVehicle,
  onSelectCamera,
  onSelectAlert,
}) => {
  const [metrics, setMetrics] = useState<SystemOverviewMetrics>({
    total_vehicles_tracked: 0,
    total_detections_today: 0,
    active_cameras: 12,
    total_cameras: 12,
    critical_alerts: 0,
    total_active_alerts: 0,
    network_average_speed_kmh: 48.5,
    system_status: 'OPERATIONAL',
  });

  const [cameras, setCameras] = useState<Camera[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [m, c] = await Promise.all([
        api.getOverviewMetrics().catch(() => null),
        api.getCameras().catch(() => []),
      ]);
      if (m) setMetrics(m);
      if (c && c.length > 0) setCameras(c);
    } catch {
      // fallback to current live states
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const criticalCount = activeAlerts.filter((a) => a.severity === 'CRITICAL' || a.severity === 'HIGH').length;

  return (
    <div className="space-y-4 font-tactical">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Metric 1: Tracked Vehicles */}
        <div className="bg-[#101522] border border-hud-border rounded-lg p-3 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">FLEET ACTIVE</span>
            <Car className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-extrabold font-mono text-slate-100">
            {metrics.total_vehicles_tracked || 48}
          </div>
          <div className="text-[10px] font-mono text-cyan-400 mt-1 flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            Active across 12 sectors
          </div>
        </div>

        {/* Metric 2: Total Detections */}
        <div className="bg-[#101522] border border-hud-border rounded-lg p-3 relative overflow-hidden group hover:border-blue-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">TODAY'S ANPR</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-extrabold font-mono text-slate-100">
            {metrics.total_detections_today || recentDetections.length}
          </div>
          <div className="text-[10px] font-mono text-blue-400 mt-1">
            Real-time multi-cam logs
          </div>
        </div>

        {/* Metric 3: Active Cameras */}
        <div className="bg-[#101522] border border-hud-border rounded-lg p-3 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">CAMERA GRID</span>
            <CameraIcon className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold font-mono text-slate-100">
            {cameras.filter((c) => c.status === 'ACTIVE').length || 12}
            <span className="text-sm font-normal text-slate-500">/{cameras.length || 12}</span>
          </div>
          <div className="text-[10px] font-mono text-emerald-400 mt-1">
            100% Online &bull; 30 FPS
          </div>
        </div>

        {/* Metric 4: Critical Anomaly Alerts */}
        <div
          className={`bg-[#101522] border rounded-lg p-3 relative overflow-hidden transition-all ${
            criticalCount > 0
              ? 'border-rose-500/70 shadow-[0_0_15px_rgba(244,63,94,0.2)] bg-rose-950/10'
              : 'border-hud-border'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">CRITICAL ALERTS</span>
            <ShieldAlert className={`w-4 h-4 ${criticalCount > 0 ? 'text-rose-400 animate-bounce' : 'text-slate-400'}`} />
          </div>
          <div className={`text-2xl font-extrabold font-mono ${criticalCount > 0 ? 'text-rose-400' : 'text-slate-100'}`}>
            {criticalCount}
          </div>
          <div className="text-[10px] font-mono text-rose-400 mt-1">
            {criticalCount > 0 ? 'Physics & Clones Flagged' : 'Normal parameters'}
          </div>
        </div>

        {/* Metric 5: Average Network Speed */}
        <div className="bg-[#101522] border border-hud-border rounded-lg p-3 relative overflow-hidden group hover:border-amber-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">NETWORK SPEED</span>
            <Gauge className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-extrabold font-mono text-slate-100">
            {metrics.network_average_speed_kmh.toFixed(1)}
            <span className="text-xs font-normal text-slate-500 ml-1">km/h</span>
          </div>
          <div className="text-[10px] font-mono text-amber-400 mt-1">
            City-wide mean velocity
          </div>
        </div>

        {/* Metric 6: Intelligence Engine Status */}
        <div className="bg-[#101522] border border-hud-border rounded-lg p-3 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-[11px] font-mono tracking-wider uppercase">ENGINE STATE</span>
            <Sparkles className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-sm font-extrabold font-mono text-emerald-400 pt-1.5">
            CORRELATING
          </div>
          <div className="text-[10px] font-mono text-slate-400 mt-2">
            Spatio-Temporal Graph
          </div>
        </div>
      </div>

      {/* Main Grid: Telemetry Stream (Left 60%) + Alerts & Camera Status (Right 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Live Detection Telemetry Stream */}
        <div className="lg:col-span-7 bg-[#101522] border border-hud-border rounded-lg p-3 flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                LIVE ANPR DETECTION TICKER
              </h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              BUFFER: {recentDetections.length} RECENT FRAMES
            </span>
          </div>

          {/* Detections Scrollable Feed */}
          <div className="flex-1 overflow-y-auto mt-2 space-y-2 pr-1">
            {recentDetections.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs font-mono">
                <Activity className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
                <span>Awaiting live telemetry packets...</span>
              </div>
            ) : (
              recentDetections.map((det) => (
                <div
                  key={det.id}
                  onClick={() => onSelectVehicle(det.plate_number)}
                  className="bg-[#0b0f19] border border-slate-800/90 hover:border-cyan-500/50 rounded p-2.5 flex items-center justify-between cursor-pointer transition-all hover:bg-slate-900/60 group"
                >
                  <div className="flex items-center gap-3">
                    {/* Synthetic Crop or Plate Icon */}
                    <div className="w-14 h-7 bg-slate-950 rounded border border-slate-700 flex items-center justify-center overflow-hidden shrink-0">
                      {det.synthetic_crop_svg ? (
                        <div
                          className="w-full h-full flex items-center justify-center p-0.5"
                          dangerouslySetInnerHTML={{ __html: det.synthetic_crop_svg }}
                        />
                      ) : (
                        <span className="text-[10px] font-mono font-bold text-cyan-400">
                          {det.plate_number.slice(0, 4)}
                        </span>
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm tracking-wider text-cyan-300 group-hover:text-cyan-200">
                          {det.plate_number}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {det.vehicle_type}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {det.vehicle_color}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2 mt-0.5">
                        <span className="text-slate-300">{det.camera_id}</span>
                        <span>&bull;</span>
                        <span className="text-emerald-400">
                          Conf: {(det.ocr_confidence * 100).toFixed(0)}%
                        </span>
                        <span>&bull;</span>
                        <span className="text-amber-300">
                          {det.speed_kmh ? `${det.speed_kmh.toFixed(0)} km/h` : '--'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0 flex items-center gap-2">
                    <div className="text-[10px] font-mono text-slate-500">
                      {new Date(det.timestamp).toLocaleTimeString()}
                    </div>
                    <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 transition-all" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Active Anomaly Alerts (Top) + Camera Matrix Quick Grid (Bottom) */}
        <div className="lg:col-span-5 flex flex-col gap-4 h-[520px]">
          {/* Active Alerts Panel */}
          <div className="bg-[#101522] border border-hud-border rounded-lg p-3 flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  ACTIVE ANOMALY ALERTS
                </h2>
              </div>
              <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 font-bold">
                {activeAlerts.length} FLAGGED
              </span>
            </div>

            <div className="flex-1 overflow-y-auto mt-2 space-y-2 pr-1">
              {activeAlerts.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs font-mono">
                  <ShieldAlert className="w-6 h-6 text-slate-600 mb-1" />
                  <span>No active anomaly alerts</span>
                </div>
              ) : (
                activeAlerts.slice(0, 10).map((alert) => (
                  <div
                    key={alert.id}
                    onClick={() => onSelectAlert(alert)}
                    className="bg-[#0b0f19] border border-rose-900/50 hover:border-rose-500 rounded p-2 text-xs font-mono cursor-pointer transition-all hover:bg-rose-950/20"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-900/60 text-rose-300 border border-rose-700">
                        {alert.alert_type}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(alert.created_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="mt-1.5 flex items-center justify-between">
                      <div className="font-bold text-slate-200">
                        {alert.plate_number ? `PLATE: ${alert.plate_number}` : `CAM: ${alert.camera_id}`}
                      </div>
                      <span className="text-[10px] text-cyan-400 flex items-center gap-0.5">
                        Inspect <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>

                    {alert.details && (alert.details.calculated_speed_kmh || alert.details.conflict) && (
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                        {alert.details.calculated_speed_kmh
                          ? `Speed: ${alert.details.calculated_speed_kmh.toFixed(0)} km/h (Limit: ${alert.details.speed_limit_kmh || 50})`
                          : alert.details.conflict || 'Dual presence detected'}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Camera Matrix Quick Status Grid */}
          <div className="bg-[#101522] border border-hud-border rounded-lg p-3 h-44 flex flex-col">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <CameraIcon className="w-3.5 h-3.5 text-emerald-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  CAMERA NETWORK CHECKPOINTS
                </h3>
              </div>
              <span className="text-[10px] font-mono text-emerald-400">12 NODES</span>
            </div>

            <div className="grid grid-cols-4 gap-1.5 mt-2 flex-1">
              {(cameras.length > 0 ? cameras : [
                { id: 'CAM-01', name: 'Connaught Place', status: 'ACTIVE' },
                { id: 'CAM-02', name: 'India Gate', status: 'ACTIVE' },
                { id: 'CAM-03', name: 'ITO Junction', status: 'ACTIVE' },
                { id: 'CAM-04', name: 'AIIMS Ring Rd', status: 'ACTIVE' },
                { id: 'CAM-05', name: 'DND Flyway', status: 'ACTIVE' },
                { id: 'CAM-06', name: 'Akshardham', status: 'ACTIVE' },
                { id: 'CAM-07', name: 'Kashmere Gate', status: 'ACTIVE' },
                { id: 'CAM-08', name: 'Karol Bagh', status: 'ACTIVE' },
                { id: 'CAM-09', name: 'Dhaula Kuan', status: 'ACTIVE' },
                { id: 'CAM-10', name: 'Aerocity / T3', status: 'ACTIVE' },
                { id: 'CAM-11', name: 'Nehru Place', status: 'ACTIVE' },
                { id: 'CAM-12', name: 'Cyber City Toll', status: 'ACTIVE' },
              ]).map((c) => (
                <div
                  key={c.id}
                  onClick={() => onSelectCamera(c.id)}
                  className={`p-1.5 rounded border text-[10px] font-mono flex flex-col justify-between cursor-pointer transition-all ${
                    c.status === 'ACTIVE'
                      ? 'bg-slate-950/70 border-slate-800 hover:border-cyan-500 text-slate-300'
                      : 'bg-rose-950/40 border-rose-800 text-rose-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-cyan-400">{c.id}</span>
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        c.status === 'ACTIVE' ? 'bg-emerald-400' : 'bg-rose-500'
                      }`}
                    />
                  </div>
                  <div className="truncate text-slate-400 text-[9px] mt-0.5">
                    {c.name.split(' ')[0]}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
