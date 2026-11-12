import React from 'react';
import {
  ShieldAlert,
  LayoutDashboard,
  Layers,
  FileSearch,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Activity,
  Cpu
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  activeCaseId: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  collapsed,
  onToggleCollapse,
  activeCaseId
}) => {
  const navItems = [
    {
      id: 'dashboard',
      label: 'Overview',
      icon: LayoutDashboard,
      badge: null
    },
    {
      id: 'queue',
      label: 'Investigation Queue',
      icon: Layers,
      badge: 'Live'
    },
    {
      id: 'detail',
      label: 'Case Investigation',
      icon: FileSearch,
      badge: activeCaseId ? activeCaseId.replace('CASE-', '#') : null,
      disabled: !activeCaseId
    },
    {
      id: 'settings',
      label: 'Platform Settings',
      icon: Settings,
      badge: null
    }
  ];

  return (
    <aside
      className={`h-screen sticky top-0 bg-slate-900/95 border-r border-slate-800 flex flex-col justify-between transition-all duration-300 z-30 select-none ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
          <div
            className="flex items-center space-x-3 cursor-pointer overflow-hidden"
            onClick={() => onSelectTab('dashboard')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 shrink-0">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            {!collapsed && (
              <div className="truncate">
                <div className="font-bold text-white text-base tracking-tight leading-none flex items-center gap-1.5">
                  FinGuard <span className="text-sky-400 font-extrabold">AI</span>
                </div>
                <div className="text-[10px] uppercase font-mono text-slate-400 mt-1 tracking-wider">
                  Fraud Ops Center
                </div>
              </div>
            )}
          </div>
          <button
            onClick={onToggleCollapse}
            aria-label="Toggle Sidebar"
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            const isDisabled = item.disabled;

            return (
              <button
                key={item.id}
                disabled={isDisabled}
                onClick={() => !isDisabled && onSelectTab(item.id)}
                title={collapsed ? item.label : undefined}
                className={`w-full flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all group ${
                  isActive
                    ? 'bg-sky-600 text-white shadow-md shadow-sky-600/20'
                    : isDisabled
                    ? 'text-slate-600 cursor-not-allowed opacity-50'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                } ${collapsed ? 'justify-center' : 'justify-between'}`}
              >
                <div className="flex items-center space-x-3 truncate">
                  <Icon
                    className={`w-5 h-5 shrink-0 ${
                      isActive ? 'text-white' : 'text-slate-400 group-hover:text-sky-400'
                    }`}
                  />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </div>
                {!collapsed && item.badge && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider font-semibold ${
                      isActive
                        ? 'bg-sky-500/40 text-sky-100'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Cloud & Model Status Footer */}
      <div className="p-3 border-t border-slate-800">
        {!collapsed ? (
          <div className="p-3 rounded-lg bg-slate-800/50 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Inference Stream
              </span>
              <span className="font-mono text-emerald-400 font-semibold">99.98%</span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center justify-between font-mono">
              <span>Bedrock: Claude 3.5</span>
              <span className="text-slate-300">ap-south-1</span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center py-2 space-y-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" title="System Operational" />
            <span title="Bedrock & SageMaker Connected">
              <Cpu className="w-4 h-4 text-slate-500" />
            </span>
          </div>
        )}
      </div>
    </aside>
  );
};

