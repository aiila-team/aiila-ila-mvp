import React from 'react';
import { Entity, EntityType } from '../types';
import RiskScoreBadge from './RiskScoreBadge';
import RiskGauge from './RiskGauge';

interface EntityCardProps {
  entity: Entity;
  onClick?: (entity: Entity) => void;
  compact?: boolean;
}

const typeIcons: Record<EntityType, string> = {
  person: '👤',
  organization: '🏢',
  domain: '🌐',
  ip: '🖥️',
  url: '🔗',
  hash: '#️⃣',
};

const typeColors: Record<EntityType, string> = {
  person: 'text-purple-400 bg-purple-900/30',
  organization: 'text-blue-400 bg-blue-900/30',
  domain: 'text-cyan-400 bg-cyan-900/30',
  ip: 'text-green-400 bg-green-900/30',
  url: 'text-yellow-400 bg-yellow-900/30',
  hash: 'text-gray-400 bg-gray-800/40',
};

const EntityCard: React.FC<EntityCardProps> = ({ entity, onClick, compact = false }) => {
  return (
    <div
      onClick={() => onClick?.(entity)}
      className={`
        bg-slate-800/60 border border-slate-700 rounded-xl p-4 cursor-pointer
        transition-all duration-150 hover:border-slate-500 hover:bg-slate-800/80
        hover:shadow-lg hover:shadow-slate-900/50
        ${compact ? 'p-3' : 'p-4'}
      `}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`text-xs px-2 py-1 rounded-full font-medium ${typeColors[entity.type]}`}
          >
            {typeIcons[entity.type]} {entity.type}
          </span>
        </div>
        <RiskGauge score={entity.risk_score} size={52} />
      </div>

      <div className="mt-2">
        <h3 className="text-white font-semibold text-sm truncate">{entity.name}</h3>
        {entity.description && !compact && (
          <p className="text-gray-400 text-xs mt-1 line-clamp-2">{entity.description}</p>
        )}
      </div>

      {!compact && entity.aliases && entity.aliases.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {entity.aliases.slice(0, 3).map((alias) => (
            <span
              key={alias}
              className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded"
            >
              {alias}
            </span>
          ))}
          {entity.aliases.length > 3 && (
            <span className="text-xs text-gray-500">+{entity.aliases.length - 3}</span>
          )}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
        <span>Last seen {new Date(entity.last_seen).toLocaleDateString()}</span>
        <RiskScoreBadge score={entity.risk_score} size="sm" />
      </div>
    </div>
  );
};

export default EntityCard;
