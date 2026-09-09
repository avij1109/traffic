import React, { useState, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Zap,
  FastForward,
  Copy,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { SimulatorStatus } from '../types/api';

interface DemoControlsProps {
  onAnomalyTriggered?: (type: string, message: string) => void;
}

export const DemoControls: React.FC<DemoControlsProps> = ({ onAnomalyTriggered }) => {
  const [status, setStatus] = useState<SimulatorStatus>({
    is_running: true,
    fleet_size: 50,
    speed_multiplier: 2.5,
    total_events_generated: 0,
    events_per_minute: 0,
    uptime_seconds: 0,
  });
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getSimulatorStatus();
      setStatus(data);
    } catch {
      // simulator might not be launched or backend starting up
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const showNotification = (msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 4000);
  };

  const handleTogglePlay = async () => {
    setLoading(true);
    try {
      if (status.is_running) {
        await api.pauseSimulator();
        showNotification('Simulator PAUSED');
      } else {
        await api.resumeSimulator();
        showNotification('Simulator RESUMED');
      }
      await fetchStatus();
    } catch (err: unknown) {
      showNotification(`Operation failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSpeedChange = async (mult: number) => {
    try {
      await api.setSimulatorSpeed(mult);
      showNotification(`Speed set to ${mult}x`);
      await fetchStatus();
    } catch (err: unknown) {
      showNotification(`Failed to set speed: ${(err as Error).message}`);
    }
  };

  const handleInjectClonedPlate = async () => {
    setLoading(true);
    try {
      const res = await api.injectAnomaly('CLONED_PLATE');
      const msg = `Cloned Plate anomaly injected! Dual vectors dispatched. (${res.events_count || 2} telemetry packets)`;
      showNotification(msg);
      if (onAnomalyTriggered) onAnomalyTriggered('CLONED_PLATE', msg);
    } catch (err: unknown) {
      showNotification(`Clone injection failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInjectImpossibleSpeed = async () => {
    setLoading(true);
    try {
      const res = await api.injectAnomaly('IMPOSSIBLE_TRAVEL');
      const msg = `Impossible Speed anomaly injected! Super-sonic hop recorded. (${res.events_count || 2} events)`;
      showNotification(msg);
      if (onAnomalyTriggered) onAnomalyTriggered('IMPOSSIBLE_TRAVEL', msg);
    } catch (err: unknown) {
      showNotification(`Speed injection failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await api.setSimulatorSpeed(1.0);
      await api.resumeSimulator();
      showNotification('Simulator reset to normal 1.0x baseline.');
      await fetchStatus();
    } catch (err: unknown) {
      showNotification(`Reset failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#101522] border border-hud-border rounded-lg p-3 text-xs font-mono shadow-lg relative overflow-hidden">
      {/* Subtle top indicator bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />

      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Play/Pause and Engine status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">
              SIMULATOR ENGINE:
            </span>
            <button
              onClick={handleTogglePlay}
              disabled={loading}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-bold transition-all ${
                status.is_running
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30'
                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30'
              }`}
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : status.is_running ? (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>PAUSE</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>START</span>
                </>
              )}
            </button>
          </div>

          {/* Speed selector pills */}
          <div className="flex items-center gap-1 bg-slate-900/90 p-0.5 rounded border border-slate-800">
            <FastForward className="w-3 h-3 text-cyan-400 ml-1.5 mr-0.5" />
            {[1.0, 2.5, 5.0, 10.0].map((multiplier) => (
              <button
                key={multiplier}
                onClick={() => handleSpeedChange(multiplier)}
                className={`px-2 py-1 rounded text-[11px] font-bold transition-all ${
                  Math.abs(status.speed_multiplier - multiplier) < 0.1
                    ? 'bg-cyan-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {multiplier}x
              </button>
            ))}
          </div>

          {/* Fleet & Throughput Telemetry */}
          <div className="hidden md:flex items-center gap-3 text-slate-400 border-l border-slate-800 pl-3">
            <div>
              FLEET: <span className="text-cyan-300 font-bold">{status.fleet_size}</span>
            </div>
            <div>
              GENERATED: <span className="text-slate-200 font-bold">{status.total_events_generated}</span>
            </div>
            <div>
              RATE: <span className="text-emerald-400 font-bold">{status.events_per_minute.toFixed(0)}</span>/min
            </div>
          </div>
        </div>

        {/* Demo Anomaly Injection Buttons */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider hidden lg:inline">
            JUDGE DEMO INJECTORS:
          </span>

          <button
            onClick={handleInjectClonedPlate}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-purple-950/60 text-purple-300 border border-purple-600/50 hover:bg-purple-900/60 font-bold hover:shadow-[0_0_12px_rgba(168,85,247,0.3)] transition-all"
            title="Inject simultaneous sighting of identical plate in divergent locations"
          >
            <Copy className="w-3.5 h-3.5 text-purple-400" />
            <span>INJECT CLONED PLATE</span>
          </button>

          <button
            onClick={handleInjectImpossibleSpeed}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-950/60 text-rose-300 border border-rose-600/50 hover:bg-rose-900/60 font-bold hover:shadow-[0_0_12px_rgba(244,63,94,0.3)] transition-all"
            title="Inject vehicle traveling between distant cameras at supersonic speed"
          >
            <Zap className="w-3.5 h-3.5 text-rose-400" />
            <span>INJECT IMPOSSIBLE SPEED</span>
          </button>

          <button
            onClick={handleReset}
            disabled={loading}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 font-bold transition-all"
            title="Reset simulation parameters to default baseline"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">RESET</span>
          </button>
        </div>
      </div>

      {/* Floating feedback notification toast */}
      {feedback && (
        <div className="mt-2.5 p-2 rounded bg-slate-900/95 border border-cyan-500/50 text-cyan-300 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{feedback}</span>
          </div>
          <span className="text-[10px] text-slate-500">Auto-dismiss</span>
        </div>
      )}
    </div>
  );
};
