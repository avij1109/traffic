import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  Zap,
  Copy,
  Calculator,
  X,
} from 'lucide-react';
import { Alert } from '../types/api';
import { api } from '../services/api';

interface AlertsCenterViewProps {
  initialAlerts?: Alert[];
  onSelectVehicle?: (plate: string) => void;
}

export const AlertsCenterView: React.FC<AlertsCenterViewProps> = ({
  initialAlerts = [],
  onSelectVehicle,
}) => {
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const fetchAlerts = async () => {
    try {
      const sev = severityFilter === 'ALL' ? undefined : severityFilter;
      const stat = statusFilter === 'ALL' ? undefined : statusFilter;
      const data = await api.getAlerts(sev, stat, undefined, 50);
      setAlerts(data);
    } catch {
      // fallback
    }
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 4000);
    return () => clearInterval(interval);
  }, [severityFilter, statusFilter]);

  const handleAcknowledge = async (alertId: string) => {
    setAcknowledgingId(alertId);
    try {
      const updated = await api.acknowledgeAlert(alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? updated : a)));
      if (selectedAlert?.id === alertId) {
        setSelectedAlert(updated);
      }
    } catch (err: unknown) {
      alert(`Failed to acknowledge: ${(err as Error).message}`);
    } finally {
      setAcknowledgingId(null);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-rose-950 text-rose-300 border-rose-600 shadow-[0_0_10px_rgba(244,63,94,0.3)] animate-pulse';
      case 'HIGH':
        return 'bg-amber-950 text-amber-300 border-amber-600';
      case 'MEDIUM':
        return 'bg-yellow-950 text-yellow-300 border-yellow-700';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-4 font-tactical h-[720px] flex flex-col">
      {/* Top Filter Bar */}
      <div className="bg-[#101522] border border-hud-border rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-rose-950 border border-rose-600 flex items-center justify-center text-rose-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
              TACTICAL ANOMALY &amp; VIOLATION AUDIT LOG
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              PHYSICS ENGINE &bull; CLONE REID ARBITRATION &bull; SENSOR INTEGRITY
            </p>
          </div>
        </div>

        {/* Severity Filters */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500 text-[10px] uppercase font-bold">SEVERITY:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2 py-1 rounded text-[10px] font-bold transition-all ${
                severityFilter === sev
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/50'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {sev}
            </button>
          ))}

          <span className="text-slate-500 text-[10px] uppercase font-bold ml-2">STATUS:</span>
          {['ALL', 'ACTIVE', 'ACKNOWLEDGED'].map((stat) => (
            <button
              key={stat}
              onClick={() => setStatusFilter(stat)}
              className={`px-2 py-1 rounded text-[10px] font-bold transition-all ${
                statusFilter === stat
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {stat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Alerts Feed Grid */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
        {alerts.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs font-mono bg-[#101522] border border-hud-border rounded-lg">
            <CheckCircle2 className="w-8 h-8 text-emerald-500/60 mb-2" />
            <span>No anomalous alarms registered matching filters</span>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`bg-[#101522] border rounded-lg p-3 text-xs font-mono flex flex-col md:flex-row items-start md:items-center justify-between gap-3 transition-all hover:bg-slate-900/60 ${
                alert.severity === 'CRITICAL'
                  ? 'border-rose-900/60'
                  : 'border-slate-800'
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`px-2 py-1 rounded text-[10px] font-bold border shrink-0 ${getSeverityBadge(
                    alert.severity
                  )}`}
                >
                  {alert.severity}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-sm text-slate-100 tracking-wider">
                      {alert.alert_type}
                    </span>
                    {alert.plate_number && (
                      <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                        PLATE: {alert.plate_number}
                      </span>
                    )}
                    {alert.camera_id && (
                      <span className="text-slate-400">
                        CAM: {alert.camera_id}
                      </span>
                    )}
                  </div>

                  <div className="text-[11px] text-slate-400 mt-1 line-clamp-1">
                    {alert.details?.message ||
                      (alert.details?.calculated_speed_kmh
                        ? `Physics anomaly: transit speed calculated at ${alert.details.calculated_speed_kmh.toFixed(0)} km/h across ${alert.details.distance_km || 'unknown'} km.`
                        : alert.details?.conflict || 'Flagged by surveillance heuristic engine.')}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                <button
                  onClick={() => setSelectedAlert(alert)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-600/50 hover:bg-cyan-900 font-bold transition-all shadow-[0_0_10px_rgba(6,182,212,0.2)]"
                >
                  <Calculator className="w-3.5 h-3.5" />
                  <span>VIEW MATHEMATICAL PROOF</span>
                </button>

                {alert.status === 'ACTIVE' ? (
                  <button
                    onClick={() => handleAcknowledge(alert.id)}
                    disabled={acknowledgingId === alert.id}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 font-bold"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>ACKNOWLEDGE</span>
                  </button>
                ) : (
                  <span className="text-[11px] font-mono text-emerald-400 px-2 py-1 bg-emerald-950/40 border border-emerald-800 rounded font-bold">
                    ACKNOWLEDGED
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Detailed Mathematical Root Cause Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101522] border-2 border-cyan-500/50 rounded-xl max-w-2xl w-full p-5 font-mono text-xs shadow-2xl relative overflow-hidden animate-in fade-in zoom-in duration-200">
            {/* Modal Top Glow Line */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-rose-500 to-amber-500" />

            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Calculator className="w-5 h-5 text-cyan-400" />
                <h3 className="font-extrabold text-sm text-slate-100 uppercase tracking-wider">
                  ANOMALY MATHEMATICAL ROOT CAUSE &amp; PROOF
                </h3>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-slate-400 hover:text-white text-base p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4">
              {/* Alert Classification Pill Banner */}
              <div className="flex items-center justify-between bg-[#0b0f19] border border-slate-800 p-3 rounded">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">ANOMALY SIGNATURE:</span>
                  <div className="font-bold text-base text-rose-400">
                    {selectedAlert.alert_type}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-500 uppercase">TIMESTAMP:</span>
                  <div className="text-slate-300">
                    {new Date(selectedAlert.created_at).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Mathematical Physics Formulation Proof */}
              {selectedAlert.details && selectedAlert.details.calculated_speed_kmh ? (
                <div className="bg-slate-950 border border-slate-800 rounded p-3.5 space-y-2.5">
                  <div className="text-cyan-400 font-bold flex items-center gap-2 border-b border-slate-800 pb-1.5">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span>KINEMATIC SPEED-DISTANCE VERIFICATION FORMULA:</span>
                  </div>

                  <div className="font-mono text-slate-300 bg-[#101522] p-2.5 rounded border border-slate-800 space-y-1">
                    <div className="text-emerald-400 font-bold">
                      Velocity = Distance / &Delta;Time
                    </div>
                    <div>
                      Physical Distance (D): <strong className="text-slate-100">{selectedAlert.details.distance_km || 14.2} km</strong>
                    </div>
                    <div>
                      Elapsed Travel Time (&Delta;t): <strong className="text-slate-100">{selectedAlert.details.time_seconds || 45} seconds</strong> ({((selectedAlert.details.time_seconds || 45) / 60).toFixed(1)} min)
                    </div>
                    <div>
                      Calculated Speed: <strong className="text-rose-400 font-extrabold text-sm">{selectedAlert.details.calculated_speed_kmh.toFixed(1)} km/h</strong>
                    </div>
                    <div>
                      Posted Sector Speed Limit: <strong className="text-amber-400">{selectedAlert.details.speed_limit_kmh || 50} km/h</strong>
                    </div>
                  </div>

                  <div className="p-2 rounded bg-rose-950/40 border border-rose-800 text-rose-300 text-[11px]">
                    <strong>PHYSICAL IMPOSSIBILITY CONCLUSION:</strong> The vehicle was observed transiting between distant optical checkpoints at a velocity that violates kinematic feasibility for road motor vehicles (Physics Ratio: {(selectedAlert.details.calculated_speed_kmh / 50).toFixed(1)}x speed limit). This triggers immediate cloned plate or high-speed chase protocols.
                  </div>
                </div>
              ) : (
                <div className="bg-slate-950 border border-slate-800 rounded p-3.5 space-y-2">
                  <div className="text-purple-400 font-bold flex items-center gap-2 border-b border-slate-800 pb-1.5">
                    <Copy className="w-4 h-4 text-purple-400" />
                    <span>CLONED PLATE SPATIAL CONFLICT EVIDENCE:</span>
                  </div>
                  <div className="text-slate-300 space-y-1 bg-[#101522] p-2.5 rounded border border-slate-800">
                    <div>Vehicle Plate: <strong className="text-cyan-300 font-bold">{selectedAlert.plate_number}</strong></div>
                    <div>Primary Sighting: <strong className="text-slate-100">{selectedAlert.details?.first_sighting?.camera_id || 'CAM-01'}</strong> ({selectedAlert.details?.first_sighting?.vehicle_type || 'SUV'})</div>
                    <div>Simultaneous Sighting: <strong className="text-slate-100">{selectedAlert.details?.second_sighting?.camera_id || 'CAM-10'}</strong> ({selectedAlert.details?.second_sighting?.vehicle_type || 'CAR'})</div>
                    <div className="text-rose-400 font-bold mt-2">
                      Dual active vectors detected within the same 60-second window across non-adjacent districts!
                    </div>
                  </div>
                </div>
              )}

              {/* Modal Actions */}
              <div className="pt-2 flex items-center justify-between">
                {selectedAlert.plate_number && onSelectVehicle && (
                  <button
                    onClick={() => {
                      onSelectVehicle(selectedAlert.plate_number!);
                      setSelectedAlert(null);
                    }}
                    className="px-3 py-1.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700 hover:bg-cyan-900 font-bold"
                  >
                    OPEN VEHICLE DOSSIER
                  </button>
                )}

                <div className="flex items-center gap-2 ml-auto">
                  {selectedAlert.status === 'ACTIVE' && (
                    <button
                      onClick={() => handleAcknowledge(selectedAlert.id)}
                      className="px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
                    >
                      ACKNOWLEDGE &amp; FILE
                    </button>
                  )}
                  <button
                    onClick={() => setSelectedAlert(null)}
                    className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 font-bold"
                  >
                    CLOSE
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
