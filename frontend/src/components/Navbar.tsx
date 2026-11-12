import React, { useState } from 'react';
import {
  Search,
  Bell,
  RefreshCw,
  Server,
  CloudOff,
  UserCheck,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  isDemoMode: boolean;
  onToggleDemoMode: () => void;
  onRefresh: () => void;
  isLoading: boolean;
  backendHealthy: boolean | null;
  onSearch: (query: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  isDemoMode,
  onToggleDemoMode,
  onRefresh,
  isLoading,
  backendHealthy,
  onSearch
}) => {
  const [searchVal, setSearchVal] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      onSearch(searchVal.trim());
    }
  };

  const getTabTitle = (tab: string) => {
    switch (tab) {
      case 'dashboard':
        return 'Executive Fraud Overview & Risk Telemetry';
      case 'queue':
        return 'Live Fraud Case Investigation Queue';
      case 'detail':
        return 'Multi-Modal Fraud Case Dossier';
      case 'settings':
        return 'Platform Governance & API Configuration';
      default:
        return 'Investigation Portal';
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Breadcrumb / Title */}
      <div className="flex items-center space-x-3">
        <h1 className="text-base font-semibold text-white tracking-tight">
          {getTabTitle(currentTab)}
        </h1>
      </div>

      {/* Center Search Bar */}
      <div className="max-w-md w-full mx-6 hidden md:block">
        <form onSubmit={handleSearchSubmit} className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            placeholder="Search Case ID, Customer, Card PAN, or TXN..."
            className="w-full bg-slate-950/60 border border-slate-700/80 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500 focus:border-sky-500 transition-all font-mono"
          />
        </form>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        {/* Backend / Demo Indicator */}
        <div className="flex items-center space-x-2 bg-slate-950/70 border border-slate-800 rounded-lg px-2.5 py-1">
          {isDemoMode ? (
            <span className="flex items-center text-amber-400 text-xs font-medium space-x-1.5" title="Operating with synthetic demo datasets">
              <CloudOff className="w-3.5 h-3.5 text-amber-400" />
              <span>Demo Sandbox</span>
            </span>
          ) : (
            <span className="flex items-center text-xs font-medium space-x-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300">Live API</span>
              {backendHealthy === true && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="Connected" />}
              {backendHealthy === false && <span className="w-2 h-2 rounded-full bg-rose-500" title="API Disconnected" />}
            </span>
          )}

          <button
            onClick={onToggleDemoMode}
            className="text-[11px] underline text-sky-400 hover:text-sky-300 ml-1 font-mono transition-colors"
          >
            {isDemoMode ? 'Go Live' : 'Demo Mode'}
          </button>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh Case Stream"
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors border border-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-sky-400' : ''}`} />
        </button>

        {/* Analyst Profile Badge */}
        <div className="flex items-center space-x-2.5 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-xs text-white shadow-sm ring-1 ring-sky-400/30">
            AM
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-semibold text-slate-200 leading-tight">Alex Mercer</div>
            <div className="text-[10px] text-slate-400 font-mono">Fraud Analyst L3</div>
          </div>
        </div>
      </div>
    </header>
  );
};

