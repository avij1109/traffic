import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Car,
  ShieldAlert,
  Clock,
  Compass,
  TrendingUp,
  FileText,
  Navigation,
} from 'lucide-react';
import {
  Vehicle,
  VehicleTrajectoryResponse,
} from '../types/api';
import { api } from '../services/api';

interface VehicleSearchViewProps {
  initialPlate?: string | null;
  onViewOnMap: (plate: string) => void;
}

export const VehicleSearchView: React.FC<VehicleSearchViewProps> = ({
  initialPlate,
  onViewOnMap,
}) => {
  const [query, setQuery] = useState(initialPlate || '');
  const [vehicleTypeFilter, setVehicleTypeFilter] = useState('ALL');
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [trajectory, setTrajectory] = useState<VehicleTrajectoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [dossierLoading, setDossierLoading] = useState(false);

  // Search vehicles
  const searchVehicles = useCallback(async () => {
    setLoading(true);
    try {
      const vType = vehicleTypeFilter === 'ALL' ? undefined : vehicleTypeFilter;
      const isFlagged = flaggedOnly ? true : undefined;
      const results = await api.searchVehicles(query || undefined, vType, isFlagged, 40);
      setVehicles(results);

      // Auto-select first or matching initial plate
      if (results.length > 0) {
        const found = initialPlate ? results.find((v) => v.plate_number === initialPlate) : results[0];
        if (found) loadDossier(found.plate_number, found);
      } else if (initialPlate) {
        // try fetching single vehicle
        try {
          const single = await api.getVehicle(initialPlate);
          setSelectedVehicle(single);
          loadDossier(initialPlate, single);
        } catch {
          // not found
        }
      }
    } catch {
      // error handling
    } finally {
      setLoading(false);
    }
  }, [query, vehicleTypeFilter, flaggedOnly, initialPlate]);

  useEffect(() => {
    const timer = setTimeout(() => {
      searchVehicles();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchVehicles]);

  // Load full dossier for a plate
  const loadDossier = async (plate: string, vehicleInfo?: Vehicle) => {
    setDossierLoading(true);
    try {
      const [traj, veh] = await Promise.all([
        api.getVehicleTrajectory(plate).catch(() => null),
        vehicleInfo ? Promise.resolve(vehicleInfo) : api.getVehicle(plate).catch(() => null),
      ]);

      if (veh) setSelectedVehicle(veh);
      setTrajectory(traj);
    } catch {
      // ignore
    } finally {
      setDossierLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[700px] font-tactical">
      {/* Left Column: Search & Vehicle Directory (4 cols) */}
      <div className="lg:col-span-4 bg-[#101522] border border-hud-border rounded-lg p-3 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              VEHICLE REGISTRY DIRECTORY
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {vehicles.length} MATCHES
          </span>
        </div>

        {/* Search Input */}
        <div className="mt-3 relative">
          <input
            type="text"
            placeholder="Search plate (e.g. DL, HR, 9921)..."
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            className="w-full bg-[#0b0f19] border border-slate-700 focus:border-cyan-500 rounded px-3 py-1.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none tracking-wider"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-2.5 top-2 text-slate-500 hover:text-slate-300 text-xs"
            >
              ✕
            </button>
          )}
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
          {['ALL', 'CAR', 'SUV', 'MOTORCYCLE', 'COMMERCIAL'].map((type) => (
            <button
              key={type}
              onClick={() => setVehicleTypeFilter(type)}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all ${
                vehicleTypeFilter === type
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {type}
            </button>
          ))}

          <button
            onClick={() => setFlaggedOnly(!flaggedOnly)}
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all ml-auto ${
              flaggedOnly
                ? 'bg-rose-950 text-rose-300 border border-rose-600'
                : 'bg-slate-900 border border-slate-800 text-slate-500 hover:text-slate-300'
            }`}
          >
            FLAGGED ONLY
          </button>
        </div>

        {/* Vehicles List */}
        <div className="flex-1 overflow-y-auto mt-3 space-y-1.5 pr-1">
          {loading ? (
            <div className="h-40 flex items-center justify-center text-xs font-mono text-slate-500">
              Searching police database...
            </div>
          ) : vehicles.length === 0 ? (
            <div className="h-40 flex flex-col items-center justify-center text-xs font-mono text-slate-500">
              <Car className="w-6 h-6 text-slate-600 mb-1" />
              <span>No vehicles found matching query</span>
            </div>
          ) : (
            vehicles.map((v) => {
              const isSelected = selectedVehicle?.plate_number === v.plate_number;
              return (
                <div
                  key={v.plate_number}
                  onClick={() => loadDossier(v.plate_number, v)}
                  className={`p-2.5 rounded border text-xs font-mono cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-cyan-950/40 border-cyan-500/70 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                      : 'bg-[#0b0f19] border-slate-800 hover:border-slate-700 hover:bg-slate-900/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm tracking-wider text-slate-100">
                      {v.plate_number}
                    </span>
                    {v.is_flagged && (
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                        FLAGGED
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                    <span>{v.make_model || `${v.color} ${v.vehicle_type}`}</span>
                    <span className="text-cyan-400 font-bold">
                      {v.total_sightings} passes
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Vehicle Dossier, HSRP Plate & Trajectory (8 cols) */}
      <div className="lg:col-span-8 bg-[#101522] border border-hud-border rounded-lg p-4 flex flex-col h-full overflow-y-auto">
        {!selectedVehicle ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs">
            <FileText className="w-12 h-12 text-slate-700 mb-2" />
            <span>Select a vehicle from the directory to open tactical dossier</span>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Top Dossier Header Card with HSRP Plate */}
            <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                {/* Authentic Indian High Security Registration Plate (HSRP) Component */}
                <div className="relative inline-flex items-center bg-gradient-to-b from-white via-slate-100 to-slate-200 text-slate-950 border-2 border-slate-400 rounded-md px-3 py-1.5 shadow-md select-none font-mono">
                  {/* Left Blue Strip with IND & Ashoka Chakra symbol */}
                  <div className="bg-[#002b80] text-white flex flex-col items-center justify-center px-1.5 py-0.5 rounded-sm -ml-1 mr-2.5 h-full">
                    <span className="text-[7px] font-bold text-amber-300 leading-tight">☸</span>
                    <span className="text-[9px] font-black tracking-tighter">IND</span>
                  </div>
                  {/* Embossed Registration Plate Text */}
                  <span className="text-lg font-black tracking-[0.2em] uppercase font-mono text-slate-900 drop-shadow-[0_1px_1px_rgba(0,0,0,0.3)]">
                    {selectedVehicle.plate_number}
                  </span>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-base text-slate-100 font-mono">
                      {selectedVehicle.make_model || 'Unknown Make/Model'}
                    </h3>
                    {selectedVehicle.is_ev && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">
                        ⚡ EV
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-mono text-slate-400 flex items-center gap-3 mt-1">
                    <span>Classification: <strong className="text-slate-200">{selectedVehicle.vehicle_type}</strong></span>
                    <span>&bull;</span>
                    <span>Color: <strong className="text-slate-200">{selectedVehicle.color}</strong></span>
                  </div>
                </div>
              </div>

              {/* Action Button: View on GIS Map */}
              <button
                onClick={() => onViewOnMap(selectedVehicle.plate_number)}
                className="flex items-center gap-2 px-3.5 py-2 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/50 hover:bg-cyan-900 font-mono text-xs font-bold transition-all shadow-[0_0_12px_rgba(6,182,212,0.2)]"
              >
                <Navigation className="w-3.5 h-3.5" />
                <span>TRACE ON GIS MAP</span>
              </button>
            </div>

            {/* Flagged Alert Banner if vehicle is flagged */}
            {selectedVehicle.is_flagged && (
              <div className="bg-rose-950/40 border border-rose-600/70 rounded-lg p-3 text-xs font-mono flex items-center gap-3 text-rose-300">
                <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 animate-pulse" />
                <div>
                  <span className="font-bold text-rose-200 uppercase">SECURITY FLAG ACTIVE: </span>
                  <span>{selectedVehicle.flag_reason || 'Flagged for suspicious transit patterns'}</span>
                </div>
              </div>
            )}

            {/* AI Next-Camera Predictive Routing Badge */}
            {trajectory && trajectory.predicted_next_cameras && trajectory.predicted_next_cameras.length > 0 && (
              <div className="bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-600/50 rounded-lg p-3 text-xs font-mono">
                <div className="flex items-center gap-2 text-cyan-400 font-bold mb-2">
                  <Compass className="w-4 h-4 animate-spin" />
                  <span>PREDICTIVE ROUTE HEURISTICS (MARKOV TRANSITION GRAPH)</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {trajectory.predicted_next_cameras.map((pred, i) => (
                    <div
                      key={pred.camera_id}
                      className="bg-[#0b0f19] border border-slate-800 rounded p-2 flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200">
                          #{i + 1} {pred.camera_id}
                        </span>
                        <span className="text-emerald-400 font-bold">
                          {(pred.probability * 100).toFixed(0)}% PROB
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 truncate mt-1">
                        {pred.name}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1">
                        Est. Arrival: ~{pred.est_arrival_seconds}s
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trajectory Timeline: Multi-Camera Sightings */}
            <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-3 text-xs font-mono">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-400" />
                  <span className="font-bold text-slate-200 uppercase tracking-wider">
                    CHRONOLOGICAL CAMERA PASS TIMELINE
                  </span>
                </div>
                {trajectory && (
                  <span className="text-slate-400">
                    TOTAL DISTANCE: <strong className="text-cyan-400">{trajectory.total_distance_km.toFixed(1)} km</strong>
                  </span>
                )}
              </div>

              {dossierLoading ? (
                <div className="py-8 text-center text-slate-500">Reconstructing spatio-temporal path...</div>
              ) : !trajectory || trajectory.visited_cameras.length === 0 ? (
                <div className="py-6 text-center text-slate-500">No trajectory records found for this vehicle.</div>
              ) : (
                <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                  {trajectory.visited_cameras.map((hop, index) => {
                    const segment = trajectory.segments[index - 1];
                    return (
                      <div key={hop.detection_id} className="relative">
                        {/* Dot indicator */}
                        <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-cyan-500 border-2 border-[#0b0f19] ring-2 ring-cyan-500/30" />

                        {/* Segment Hop Card */}
                        <div className="bg-[#101522] border border-slate-800 rounded p-2.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-cyan-400 text-sm">
                                HOP #{index + 1}: {hop.camera_id}
                              </span>
                              <span className="text-slate-300 font-medium">
                                {hop.camera_name}
                              </span>
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                                {hop.zone}
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-400">
                              {new Date(hop.timestamp).toLocaleString()}
                            </span>
                          </div>

                          <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-400">
                            <div>
                              Recorded Speed:{' '}
                              <strong className="text-amber-300">
                                {hop.speed_kmh.toFixed(0)} km/h
                              </strong>
                            </div>
                            <div>
                              Confidence:{' '}
                              <strong className="text-emerald-400">
                                {(hop.confidence * 100).toFixed(0)}%
                              </strong>
                            </div>
                          </div>

                          {/* Transition Segment Details (if hopped from previous camera) */}
                          {segment && (
                            <div className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] flex items-center justify-between text-slate-400">
                              <div className="flex items-center gap-2">
                                <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
                                <span>
                                  Transit: {segment.distance_km.toFixed(1)} km in {segment.travel_time_seconds.toFixed(0)}s
                                </span>
                              </div>
                              <div>
                                Transit Velocity:{' '}
                                <strong
                                  className={
                                    segment.is_impossible
                                      ? 'text-rose-400 font-bold'
                                      : segment.is_speeding
                                      ? 'text-amber-400 font-bold'
                                      : 'text-slate-200'
                                  }
                                >
                                  {segment.calculated_speed_kmh.toFixed(0)} km/h
                                </strong>
                                {segment.is_impossible && (
                                  <span className="ml-1 text-rose-400 font-bold">
                                    [IMPOSSIBLE TRAVEL FLAGGED]
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
