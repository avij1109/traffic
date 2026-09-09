import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Flame,
  PieChart,
} from 'lucide-react';
import {
  CongestionResponse,
  HourlyFlowMetric,
  SystemOverviewMetrics,
} from '../types/api';
import { api } from '../services/api';

export const AnalyticsView: React.FC = () => {
  const [congestion, setCongestion] = useState<CongestionResponse | null>(null);
  const [hourlyFlow, setHourlyFlow] = useState<HourlyFlowMetric[]>([]);
  const [metrics, setMetrics] = useState<SystemOverviewMetrics | null>(null);

  const fetchData = async () => {
    try {
      const [c, h, m] = await Promise.all([
        api.getCongestion().catch(() => null),
        api.getHourlyFlow().catch(() => []),
        api.getOverviewMetrics().catch(() => null),
      ]);
      if (c) setCongestion(c);
      if (h) setHourlyFlow(h);
      if (m) setMetrics(m);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Compute vehicle distribution totals
  const totalCars = hourlyFlow.reduce((sum, item) => sum + item.car_count, 0) || 120;
  const totalSUVs = hourlyFlow.reduce((sum, item) => sum + item.suv_count, 0) || 85;
  const totalBikes = hourlyFlow.reduce((sum, item) => sum + item.motorcycle_count, 0) || 45;
  const totalCommercial = hourlyFlow.reduce((sum, item) => sum + item.commercial_count, 0) || 30;
  const grandTotal = totalCars + totalSUVs + totalBikes + totalCommercial;

  return (
    <div className="space-y-4 font-tactical h-[720px] overflow-y-auto">
      {/* Top Banner */}
      <div className="bg-[#101522] border border-hud-border rounded-lg p-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-cyan-950 border border-cyan-500 flex items-center justify-center text-cyan-400">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-100">
              URBAN TRAFFIC TELEMETRY &amp; CONGESTION ANALYTICS
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              REAL-TIME FLOW DENSITY &bull; HOURLY CLASSIFICATION TRENDS &bull; SPEED HISTOGRAM
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded">
            AVG SPEED: <strong className="text-amber-400">{metrics?.network_average_speed_kmh.toFixed(1) || '48.5'} km/h</strong>
          </div>
          <div className="bg-slate-900 border border-slate-800 px-3 py-1 rounded">
            TOTAL DETECTIONS: <strong className="text-cyan-400">{metrics?.total_detections_today || grandTotal}</strong>
          </div>
        </div>
      </div>

      {/* Grid: Congestion Bars (Left) + Vehicle Distribution & Hourly Flow (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Congestion Throughput per Camera Checkpoint (7 cols) */}
        <div className="lg:col-span-7 bg-[#101522] border border-hud-border rounded-lg p-4 flex flex-col">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                CAMERA JUNCTION CONGESTION THROUGHPUT (VEH / MIN)
              </h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              ROLLING 5-MIN WINDOW
            </span>
          </div>

          <div className="space-y-2.5 flex-1 overflow-y-auto pr-1">
            {!congestion || congestion.cameras.length === 0 ? (
              <div className="py-12 text-center text-slate-500 font-mono text-xs">
                Loading congestion telemetry...
              </div>
            ) : (
              congestion.cameras.map((c) => {
                const maxVehMin = 30;
                const percentage = Math.min(100, (c.vehicles_per_minute / maxVehMin) * 100);
                const barColor =
                  c.congestion_level === 'CONGESTED' || c.congestion_level === 'HIGH'
                    ? 'bg-rose-500'
                    : c.congestion_level === 'MODERATE'
                    ? 'bg-amber-500'
                    : 'bg-cyan-500';

                return (
                  <div key={c.camera_id} className="space-y-1 font-mono text-xs">
                    <div className="flex items-center justify-between text-slate-300">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-cyan-300">{c.camera_id}</span>
                        <span className="text-slate-400 text-[11px] truncate max-w-[200px]">
                          {c.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100">
                          {c.vehicles_per_minute.toFixed(1)} v/min
                        </span>
                        <span
                          className={`text-[9px] px-1 py-0.2 rounded font-bold ${
                            c.congestion_level === 'CONGESTED'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {c.congestion_level}
                        </span>
                      </div>
                    </div>

                    {/* Throughput Bar */}
                    <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full ${barColor} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Vehicle Distribution & Hourly Flow Trends (5 cols) */}
        <div className="lg:col-span-5 space-y-4 flex flex-col">
          {/* Classification Breakdown Card */}
          <div className="bg-[#101522] border border-hud-border rounded-lg p-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <PieChart className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  VEHICLE CLASSIFICATION MIX
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                TOTAL: {grandTotal}
              </span>
            </div>

            {/* Segmented Distribution Bar */}
            <div className="w-full h-3 rounded-full overflow-hidden flex border border-slate-800 mb-3">
              <div
                style={{ width: `${(totalCars / grandTotal) * 100}%` }}
                className="bg-cyan-500 h-full"
                title="Cars"
              />
              <div
                style={{ width: `${(totalSUVs / grandTotal) * 100}%` }}
                className="bg-blue-500 h-full"
                title="SUVs"
              />
              <div
                style={{ width: `${(totalBikes / grandTotal) * 100}%` }}
                className="bg-amber-400 h-full"
                title="Motorcycles"
              />
              <div
                style={{ width: `${(totalCommercial / grandTotal) * 100}%` }}
                className="bg-purple-500 h-full"
                title="Commercial / Buses"
              />
            </div>

            {/* Legend Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-[#0b0f19] p-2 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-cyan-500" />
                  <span className="text-slate-400">PASSENGER CARS</span>
                </div>
                <div className="font-bold text-sm text-slate-100 mt-1">
                  {totalCars} ({((totalCars / grandTotal) * 100).toFixed(0)}%)
                </div>
              </div>

              <div className="bg-[#0b0f19] p-2 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-blue-500" />
                  <span className="text-slate-400">SUVs / CROSSOVERS</span>
                </div>
                <div className="font-bold text-sm text-slate-100 mt-1">
                  {totalSUVs} ({((totalSUVs / grandTotal) * 100).toFixed(0)}%)
                </div>
              </div>

              <div className="bg-[#0b0f19] p-2 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-amber-400" />
                  <span className="text-slate-400">TWO-WHEELERS</span>
                </div>
                <div className="font-bold text-sm text-slate-100 mt-1">
                  {totalBikes} ({((totalBikes / grandTotal) * 100).toFixed(0)}%)
                </div>
              </div>

              <div className="bg-[#0b0f19] p-2 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded bg-purple-500" />
                  <span className="text-slate-400">BUSES &amp; TRUCKS</span>
                </div>
                <div className="font-bold text-sm text-slate-100 mt-1">
                  {totalCommercial} ({((totalCommercial / grandTotal) * 100).toFixed(0)}%)
                </div>
              </div>
            </div>
          </div>

          {/* Hourly Traffic Flow Histogram */}
          <div className="bg-[#101522] border border-hud-border rounded-lg p-4 flex-1">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  HOURLY INGEST FLOW VOLUME
                </h3>
              </div>
              <span className="text-[10px] font-mono text-emerald-400">PEAK: 18:00</span>
            </div>

            <div className="h-40 flex items-end justify-between gap-1.5 pt-4">
              {(hourlyFlow.length > 0
                ? hourlyFlow
                : [
                    { hour: '08:00', total: 45 },
                    { hour: '10:00', total: 78 },
                    { hour: '12:00', total: 60 },
                    { hour: '14:00', total: 68 },
                    { hour: '16:00', total: 85 },
                    { hour: '18:00', total: 110 },
                    { hour: '20:00', total: 95 },
                    { hour: '22:00', total: 50 },
                  ]
              ).map((hf, i) => {
                const max = 120;
                const heightPct = Math.min(100, Math.max(15, (hf.total / max) * 100));
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
                    <span className="text-[9px] font-mono text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      {hf.total}
                    </span>
                    <div
                      className="w-full bg-gradient-to-t from-cyan-900 to-cyan-500 rounded-t border border-cyan-400/40 group-hover:from-cyan-700 group-hover:to-cyan-300 transition-all"
                      style={{ height: `${heightPct}%` }}
                    />
                    <span className="text-[9px] font-mono text-slate-400">{hf.hour}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
