import React from 'react';
import { CaseStatus } from '../types/case';

interface Props {
  status: CaseStatus | string;
  className?: string;
}

export const StatusBadge: React.FC<Props> = ({ status, className = '' }) => {
  const norm = (status || 'OPEN').toUpperCase();

  let colors = 'bg-slate-800 text-slate-300 border-slate-700';

  switch (norm) {
    case 'OPEN':
      colors = 'bg-blue-950/80 text-blue-300 border-blue-800/60 animate-pulse';
      break;
    case 'IN_REVIEW':
      colors = 'bg-amber-950/80 text-amber-300 border-amber-800/60';
      break;
    case 'ESCALATED':
      colors = 'bg-purple-950/80 text-purple-300 border-purple-800/60 ring-1 ring-purple-500/30';
      break;
    case 'RESOLVED':
      colors = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60';
      break;
    case 'CLOSED':
      colors = 'bg-slate-800 text-slate-400 border-slate-700';
      break;
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider border ${colors} ${className}`}
    >
      {norm.replace('_', ' ')}
    </span>
  );
};

