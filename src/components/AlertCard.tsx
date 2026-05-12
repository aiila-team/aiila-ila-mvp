import React from 'react';
import { Alert, AlertSeverity } from '../types';
import RiskScoreBadge from './RiskScoreBadge';

interface AlertCardProps {
  alert: Alert;
  onClick?: (alert: Alert) => void;
  compact?: boolean;
}

const severityStyles: Record<AlertSeverity, string> = {
  critical: 'border-l-red-600 bg-red-950/20',
  high: 'border-l-orange-500 bg-orange-950/20',
  medium: 'border-l-yellow-500 bg-yellow-950/10',
  low: 'border-l-blue-500 bg-blue-950/10',
  info: 'border-l-gray-500 bg-gray-900/20',
};

const severityDot: Record<AlertSeverity, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500',
  info: 'bg-gray-400',
};

const AlertCard: React.FC<AlertCardProps> = ({ alert, onClick, compact = false }) => {
  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  };

  return (
    <div
      onClick={() => onClick?.(alert)}
      className={`
        border-l-4 rounded-r-lg p-3 cursor-pointer transition-all duration-150
        hover:brightness-110 hover:scale-[1.01]
        ${severityStyles[alert.severity]}
        ${compact ? 'py-2' : 'py-3'}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 mt-0.5 ${severityDot[alert.severity]}`} />
          <p className="text-sm font-semibold text-white truncate">{alert.title}</p>
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">
          {timeAgo(alert.timestamp)}
        </span>
      </div>

      {!compact && (
        <p className="text-xs text-gray-400 mt-1 ml-4 line-clamp-2">{alert.description}</p>
      )}

      <div className="flex items-center gap-2 mt-2 ml-4 flex-wrap">
        <span className="text-xs text-gray-500">{alert.source}</span>
        {alert.entity_name && (
          <span className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded">
            {alert.entity_name}
          </span>
        )}
        {alert.tags?.slice(0, 2).map((tag) => (
          <span key={tag} className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
            #{tag}
          </span>
        ))}
      </div>
    </div>
  );
};

export default AlertCard;
