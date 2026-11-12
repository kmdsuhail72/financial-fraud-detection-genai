import React from 'react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: string;
  trendPositive?: boolean;
  icon: React.ReactNode;
  variant?: 'default' | 'critical' | 'warning' | 'success';
}

export const KpiCard: React.FC<Props> = ({
  title,
  value,
  subtitle,
  trend,
  trendPositive = true,
  icon,
  variant = 'default',
}) => {
  let borderColors = 'border-slate-800 hover:border-slate-700';
  let iconBg = 'bg-slate-800 text-sky-400';

  if (variant === 'critical') {
    borderColors = 'border-red-900/40 hover:border-red-800/70';
    iconBg = 'bg-red-950/60 text-red-400';
  } else if (variant === 'warning') {
    borderColors = 'border-amber-900/40 hover:border-amber-800/70';
    iconBg = 'bg-amber-950/60 text-amber-400';
  } else if (variant === 'success') {
    borderColors = 'border-emerald-900/40 hover:border-emerald-800/70';
    iconBg = 'bg-emerald-950/60 text-emerald-400';
  }

  return (
    <div
      className={`bg-slate-900/90 rounded-xl p-5 border ${borderColors} transition-all duration-200 shadow-lg`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`p-2.5 rounded-lg ${iconBg}`}>{icon}</div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-slate-100">{value}</span>
        {trend && (
          <span
            className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
              trendPositive ? 'bg-emerald-950/70 text-emerald-400' : 'bg-red-950/70 text-red-400'
            }`}
          >
            {trend}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
};

