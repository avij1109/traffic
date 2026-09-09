import React, { useState, useEffect } from 'react';
import {
  Video,
  Power,
  WifiOff,
  Crosshair,
} from 'lucide-react';
import { Camera } from '../types/api';
import { api } from '../services/api';

interface CameraMatrixViewProps {
  onSelectCameraOnMap?: (cameraId: string) => void;
}

export const CameraMatrixView: React.FC<CameraMatrixViewProps> = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchCameras = async () => {
    try {
      const data = await api.getCameras();
      setCameras(data);
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    fetchCameras();
    const interval = setInterval(fetchCameras, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleBlackout = async (camera: Camera) => {
    setTogglingId(camera.id);
    const newStatus = camera.status === 'ACTIVE' ? 'OFFLINE' : 'ACTIVE';
    try {
      await api.updateCameraStatus(camera.id, newStatus);
      setCameras((prev) =>
        prev.map((c) => (c.id === camera.id ? { ...c, status: newStatus } : c))
      );
    } catch (err: unknown) {
      alert(`Failed to toggle camera: ${(err as Error).message}`);
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="space-y-4 font-tactical">
      {/* Top Header & Status Summary */}
      <div className="bg-[#101522] border border-hud-border rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-cyan-950 border border-cyan-500 flex items-center justify-center text-cyan-400">
            <Video className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
              12-SECTOR OPTICAL SURVEILLANCE MATRIX
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              HD ANPR CHECKPOINTS &bull; HIGHWAY SPEED TRAPS &bull; INTERSECTION SENSORS
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300">
              ONLINE:{' '}
              <strong className="text-emerald-400">
                {cameras.filter((c) => c.status === 'ACTIVE').length}
              </strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span className="text-slate-300">
              BLACKOUT / OFFLINE:{' '}
              <strong className="text-rose-400">
                {cameras.filter((c) => c.status !== 'ACTIVE').length}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* 12-Camera Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {cameras.map((cam) => {
          const isOffline = cam.status !== 'ACTIVE';
          const isBusy = togglingId === cam.id;

          return (
            <div
              key={cam.id}
              className={`bg-[#101522] border rounded-lg overflow-hidden flex flex-col transition-all group ${
                isOffline
                  ? 'border-rose-900/60 shadow-[0_0_15px_rgba(244,63,94,0.15)]'
                  : 'border-slate-800 hover:border-cyan-500/50'
              }`}
            >
              {/* Simulated Camera Viewfinder */}
              <div className="h-36 bg-[#070a10] relative flex items-center justify-center overflow-hidden border-b border-slate-800/80 scanline">
                {isOffline ? (
                  <div className="flex flex-col items-center justify-center text-rose-500 text-xs font-mono space-y-1">
                    <WifiOff className="w-8 h-8 animate-pulse" />
                    <span className="font-bold tracking-widest uppercase">SIGNAL LOST</span>
                    <span className="text-[10px] text-slate-500">SIMULATED BLACKOUT</span>
                  </div>
                ) : (
                  <>
                    {/* Viewfinder crosshairs & guides */}
                    <div className="absolute inset-2 border border-slate-800/50 pointer-events-none flex flex-col justify-between p-1.5">
                      <div className="flex justify-between text-[9px] font-mono text-cyan-400/70">
                        <span>REC [LIVE]</span>
                        <span>1080p 30FPS</span>
                      </div>
                      <div className="flex justify-center">
                        <Crosshair className="w-6 h-6 text-cyan-500/40" />
                      </div>
                      <div className="flex justify-between text-[9px] font-mono text-slate-500">
                        <span>{cam.zone}</span>
                        <span>FOV 94&deg;</span>
                      </div>
                    </div>

                    {/* Camera Feed Background Stylized Silhouette */}
                    <div className="opacity-20 text-cyan-400 font-mono text-[9px] text-center pointer-events-none select-none">
                      STREAM://{cam.id}.DELHI-POLICE.NET/RTSP
                      <br />
                      ANPR REID CONF 98.4%
                    </div>
                  </>
                )}

                {/* Top Status Pill */}
                <div className="absolute top-2 left-2 z-10">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border flex items-center gap-1 ${
                      isOffline
                        ? 'bg-rose-950 text-rose-300 border-rose-700'
                        : 'bg-emerald-950/80 text-emerald-300 border-emerald-700 backdrop-blur'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isOffline ? 'bg-rose-500' : 'bg-emerald-400 animate-ping'
                      }`}
                    />
                    {cam.status}
                  </span>
                </div>

                {/* Camera ID Badge */}
                <div className="absolute top-2 right-2 z-10">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-extrabold bg-slate-900/90 text-cyan-400 border border-slate-700">
                    {cam.id}
                  </span>
                </div>
              </div>

              {/* Camera Metadata & Blackout Action Controls */}
              <div className="p-3 flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="font-mono font-bold text-xs text-slate-100 truncate">
                    {cam.name}
                  </h3>
                  <div className="text-[11px] font-mono text-slate-400 mt-1 space-y-0.5">
                    <div>Zone: <span className="text-slate-200">{cam.zone}</span></div>
                    <div className="flex justify-between">
                      <span>Speed Limit:</span>
                      <span className="text-amber-400 font-bold">{cam.speed_limit_kmh} km/h</span>
                    </div>
                    <div className="flex justify-between">
                      <span>GPS:</span>
                      <span className="text-slate-400 font-mono">{cam.latitude.toFixed(4)}, {cam.longitude.toFixed(4)}</span>
                    </div>
                  </div>
                </div>

                {/* Simulated Blackout Action Toggle Button */}
                <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500">OPERATOR OVERRIDE</span>
                  <button
                    onClick={() => handleToggleBlackout(cam)}
                    disabled={isBusy}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono font-bold transition-all ${
                      isOffline
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-700 hover:bg-emerald-900'
                        : 'bg-rose-950/60 text-rose-300 border border-rose-800 hover:bg-rose-900'
                    }`}
                  >
                    <Power className="w-3 h-3" />
                    <span>{isOffline ? 'RESTORE FEED' : 'BLACKOUT CAM'}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
