import React from 'react';
import { RiskLevel } from '../types/case';
import { ShieldAlert, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';

interface Props {
  level: RiskLevel | string;
  score?: number;
  showIcon?: boolean;
  className?: string;
}

export const RiskBadge: React.FC<Props> = ({ level, score, showIcon = true, className = '' }) => {
  const norm = (level || 'LOW').toUpperCase();

  let colors = 'bg-slate-800 text-slate-300 border-slate-700';
  let icon = <CheckCircle className="w-3.5 h-3.5" />;

  if (norm === 'CRITICAL') {
    colors = 'bg-red-950/80 text-red-300 border-red-800/60 ring-1 ring-red-500/20';
    icon = <ShieldAlert className="w-3.5 h-3.5 text-red-400" />;
  } else if (norm === 'HIGH') {
    colors = 'bg-amber-950/80 text-amber-300 border-amber-800/60 ring-1 ring-amber-500/20';
    icon = <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
  } else if (norm === 'REVIEW' || norm === 'MEDIUM') {
    colors = 'bg-sky-950/80 text-sky-300 border-sky-800/60';
    icon = <AlertCircle className="w-3.5 h-3.5 text-sky-400" />;
  } else if (norm === 'LOW') {
    colors = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60';
    icon = <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colors} ${className}`}
    >
      {showIcon && icon}
      <span>{norm}</span>
      {score !== undefined && (
        <span className="font-mono opacity-80 pl-0.5">({(score * 100).toFixed(1)}%)</span>
      )}
    </span>
  );
};

