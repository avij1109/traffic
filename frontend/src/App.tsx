import React, { useState, useEffect } from 'react';
import { Header, NavTab } from './components/Header';
import { DemoControls } from './components/DemoControls';
import { OverviewView } from './components/OverviewView';
import { LiveMapView } from './components/LiveMapView';
import { VehicleSearchView } from './components/VehicleSearchView';
import { CameraMatrixView } from './components/CameraMatrixView';
import { AlertsCenterView } from './components/AlertsCenterView';
import { AnalyticsView } from './components/AnalyticsView';
import { useWebSocket } from './hooks/useWebSocket';
import { Camera, Detection, Alert } from './types/api';
import { api } from './services/api';
import { ShieldAlert, X } from 'lucide-react';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedVehiclePlate, setSelectedVehiclePlate] = useState<string | null>(null);
  const [floatingAlert, setFloatingAlert] = useState<Alert | null>(null);

  // Real-time WebSocket hook
  const {
    isConnected: isWsConnected,
    detections: liveDetections,
    alerts: liveAlerts,
    latestAlert,
  } = useWebSocket();

  // Baseline initial state from REST API
  const [initialDetections, setInitialDetections] = useState<Detection[]>([]);
  const [initialAlerts, setInitialAlerts] = useState<Alert[]>([]);

  // Initial fetch for cameras, recent detections, and alerts
  useEffect(() => {
    const init = async () => {
      try {
        const [cams, dets, alts] = await Promise.all([
          api.getCameras().catch(() => []),
          api.getRecentDetections(50).catch(() => []),
          api.getAlerts(undefined, 'ACTIVE', undefined, 20).catch(() => []),
        ]);
        if (cams.length > 0) setCameras(cams);
        if (dets.length > 0) setInitialDetections(dets);
        if (alts.length > 0) setInitialAlerts(alts);
      } catch {
        // backend might be bootstrapping
      }
    };
    init();
  }, []);

  // Merge live WebSocket data with REST baseline
  const mergedDetections = liveDetections.length > 0 ? liveDetections : initialDetections;
  const mergedAlerts = liveAlerts.length > 0 ? liveAlerts : initialAlerts;

  // Flash floating banner on incoming critical alert
  useEffect(() => {
    if (latestAlert && (latestAlert.severity === 'CRITICAL' || latestAlert.severity === 'HIGH')) {
      setFloatingAlert(latestAlert);
      const timer = setTimeout(() => setFloatingAlert(null), 8000);
      return () => clearTimeout(timer);
    }
  }, [latestAlert]);

  const handleSelectVehicle = (plate: string) => {
    setSelectedVehiclePlate(plate);
    setCurrentTab('search');
  };

  const handleViewVehicleOnMap = (plate: string) => {
    setSelectedVehiclePlate(plate);
    setCurrentTab('map');
  };

  const handleSelectCamera = (_camId: string) => {
    setCurrentTab('map');
  };

  const handleSelectAlert = (alert: Alert) => {
    if (alert.plate_number) {
      setSelectedVehiclePlate(alert.plate_number);
    }
    setCurrentTab('alerts');
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0a0d14] text-slate-100 overflow-hidden font-tactical">
      {/* HUD Header */}
      <Header
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        activeAlertCount={mergedAlerts.filter((a) => a.status === 'ACTIVE').length}
        isWsConnected={isWsConnected}
      />

      {/* Demo Controls Bar */}
      <div className="px-4 py-2 bg-[#0c101a] border-b border-hud-border shrink-0">
        <DemoControls
          onAnomalyTriggered={(_type, _msg) => {
            // switch to alerts tab when an anomaly is injected to showcase it
            setTimeout(() => setCurrentTab('alerts'), 1000);
          }}
        />
      </div>

      {/* Floating Critical Alert Toast Bar */}
      {floatingAlert && (
        <div className="mx-4 mt-2 p-2.5 rounded-lg bg-rose-950/90 border border-rose-500/70 text-rose-200 flex items-center justify-between shadow-[0_0_20px_rgba(244,63,94,0.4)] animate-bounce z-40 font-mono text-xs">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 animate-pulse" />
            <div>
              <span className="font-extrabold text-white uppercase">
                [{floatingAlert.severity}] {floatingAlert.alert_type}:
              </span>{' '}
              <span>{floatingAlert.plate_number ? `Plate ${floatingAlert.plate_number}` : `Camera ${floatingAlert.camera_id}`} &bull;</span>{' '}
              <span className="text-slate-300">
                {floatingAlert.details?.calculated_speed_kmh
                  ? `Speed ${floatingAlert.details.calculated_speed_kmh.toFixed(0)} km/h recorded!`
                  : floatingAlert.details?.conflict || 'Flagged by surveillance engine'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                handleSelectAlert(floatingAlert);
                setFloatingAlert(null);
              }}
              className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px]"
            >
              INVESTIGATE
            </button>
            <button
              onClick={() => setFloatingAlert(null)}
              className="text-rose-400 hover:text-white p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Command Center Viewport */}
      <main className="flex-1 p-4 overflow-y-auto">
        {currentTab === 'overview' && (
          <OverviewView
            recentDetections={mergedDetections}
            activeAlerts={mergedAlerts}
            onSelectVehicle={handleSelectVehicle}
            onSelectCamera={handleSelectCamera}
            onSelectAlert={handleSelectAlert}
          />
        )}

        {currentTab === 'map' && (
          <LiveMapView
            cameras={cameras}
            recentDetections={mergedDetections}
            selectedVehiclePlate={selectedVehiclePlate}
            onSelectVehicle={handleSelectVehicle}
            onSelectCamera={handleSelectCamera}
          />
        )}

        {currentTab === 'search' && (
          <VehicleSearchView
            initialPlate={selectedVehiclePlate}
            onViewOnMap={handleViewVehicleOnMap}
          />
        )}

        {currentTab === 'matrix' && (
          <CameraMatrixView onSelectCameraOnMap={handleSelectCamera} />
        )}

        {currentTab === 'alerts' && (
          <AlertsCenterView
            initialAlerts={mergedAlerts}
            onSelectVehicle={handleSelectVehicle}
          />
        )}

        {currentTab === 'analytics' && <AnalyticsView />}
      </main>

      {/* Command Center Footer Ticker */}
      <footer className="bg-[#0b0f19] border-t border-hud-border px-4 py-1.5 flex items-center justify-between text-[11px] font-mono text-slate-500 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-cyan-400 font-bold">NODE: DELHI-HQ-CLUSTER-01</span>
          <span>&bull;</span>
          <span>INGEST LATENCY: ~12ms</span>
          <span>&bull;</span>
          <span>ANPR OCR ENGINE: ACTIVE</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">SIH 2026 PS-26127</span>
          <span className="text-slate-600">|</span>
          <span className="text-emerald-400">STATUS: GREEN (ALL SYSTEMS NOMINAL)</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
