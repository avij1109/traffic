import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Radio,
  Clock,
  MapPin,
  Search,
  Video,
  BarChart3,
  LayoutDashboard,
  BellRing,
} from 'lucide-react';

export type NavTab = 'overview' | 'map' | 'search' | 'matrix' | 'alerts' | 'analytics';

interface HeaderProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  activeAlertCount: number;
  isWsConnected: boolean;
  onOpenAlertsModal?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onSelectTab,
  activeAlertCount,
  isWsConnected,
}) => {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [currentDate, setCurrentDate] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
      setCurrentDate(
        now.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        }).toUpperCase()
      );
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'DASHBOARD', icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: 'map', label: 'GIS MAP', icon: <MapPin className="w-4 h-4" /> },
    { id: 'search', label: 'DOSSIER / SEARCH', icon: <Search className="w-4 h-4" /> },
    { id: 'matrix', label: 'CAMERA MATRIX', icon: <Video className="w-4 h-4" /> },
    { id: 'alerts', label: 'ALERTS FEED', icon: <ShieldAlert className="w-4 h-4" /> },
    { id: 'analytics', label: 'ANALYTICS', icon: <BarChart3 className="w-4 h-4" /> },
  ];

  return (
    <header className="bg-[#0b0f19] border-b border-hud-border px-4 py-2.5 flex items-center justify-between select-none z-30 shrink-0">
      {/* Brand & Badge */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.4)]">
              <ShieldAlert className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[#0b0f19]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-sm tracking-wider text-slate-100 uppercase">
                POLICE COMMAND CENTER
              </h1>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                PROD-v2.6
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400 tracking-wide">
              DELHI NCR TRAFFIC SURVEILLANCE &amp; ANPR INTELLIGENCE LAYER
            </p>
          </div>
        </div>

        <div className="h-7 w-px bg-slate-800 hidden md:block" />

        {/* Live System Status Tag */}
        <div className="hidden lg:flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] font-mono font-semibold tracking-wider text-emerald-400 uppercase">
            ANPR INGEST ACTIVE
          </span>
        </div>
      </div>

      {/* Nav Tabs */}
      <nav className="hidden xl:flex items-center gap-1 bg-slate-950/80 p-1 rounded-lg border border-slate-800/80">
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-mono font-semibold tracking-wider transition-all ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
              }`}
            >
              {item.icon}
              {item.label}
              {item.id === 'alerts' && activeAlertCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-rose-600 text-white animate-pulse">
                  {activeAlertCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: Alerts Badge, Clock, WS Ping */}
      <div className="flex items-center gap-3">
        {/* Active Alerts Pill */}
        <button
          onClick={() => onSelectTab('alerts')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-mono font-semibold transition-all ${
            activeAlertCount > 0
              ? 'bg-rose-950/50 border-rose-600/70 text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.3)] animate-pulse'
              : 'bg-slate-900 border-slate-800 text-slate-400'
          }`}
        >
          <BellRing className={`w-3.5 h-3.5 ${activeAlertCount > 0 ? 'text-rose-400 animate-bounce' : ''}`} />
          <span>ALERTS:</span>
          <span className={`font-bold ${activeAlertCount > 0 ? 'text-rose-200' : 'text-slate-500'}`}>
            {activeAlertCount}
          </span>
        </button>

        {/* WebSocket Indicator */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-[11px] font-mono ${
            isWsConnected
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-400'
              : 'bg-rose-950/40 border-rose-800 text-rose-400'
          }`}
          title={isWsConnected ? 'WebSocket live stream connected' : 'WebSocket disconnected (reconnecting...)'}
        >
          <Radio className={`w-3 h-3 ${isWsConnected ? 'text-emerald-400 animate-pulse' : 'text-rose-400'}`} />
          <span className="hidden sm:inline font-bold">
            {isWsConnected ? 'LIVE FEED' : 'OFFLINE'}
          </span>
        </div>

        {/* Digital Military Clock */}
        <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-1 rounded">
          <Clock className="w-3.5 h-3.5 text-cyan-400 hidden sm:block" />
          <div className="text-right">
            <div className="text-xs font-mono font-bold text-slate-100 tracking-wider">
              {currentTime || '--:--:--'}
            </div>
            <div className="text-[9px] font-mono text-slate-500 leading-none">
              {currentDate || 'IST / UTC+5:30'}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
