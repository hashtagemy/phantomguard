import React from 'react';
import { QualityLevel } from '../types';

interface StatusBadgeProps {
  status: QualityLevel | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  let colorClass = 'bg-gray-800 text-gray-400 border-gray-700';
  
  switch (status) {
    case QualityLevel.EXCELLENT:
    case 'completed':
      colorClass = 'bg-emerald-950/50 text-emerald-400 border-emerald-900/50 shadow-[0_0_10px_rgba(16,185,129,0.2)]';
      break;
    case QualityLevel.GOOD:
      colorClass = 'bg-blue-950/50 text-blue-400 border-blue-900/50';
      break;
    case QualityLevel.POOR:
      colorClass = 'bg-orange-950/50 text-orange-400 border-orange-900/50';
      break;
    case QualityLevel.FAILED:
    case 'terminated':
      colorClass = 'bg-red-950/50 text-red-400 border-red-900/50 shadow-[0_0_10px_rgba(239,68,68,0.2)]';
      break;
    case QualityLevel.STUCK:
      colorClass = 'bg-yellow-950/50 text-yellow-400 border-yellow-900/50 animate-pulse';
      break;
    case 'active':
      colorClass = 'bg-phantom-950/50 text-phantom-400 border-phantom-900/50 animate-pulse';
      break;
  }

  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs';

  return (
    <span className={`inline-flex items-center justify-center rounded-full border font-medium tracking-wide ${colorClass} ${sizeClass}`}>
      {status}
    </span>
  );
};
