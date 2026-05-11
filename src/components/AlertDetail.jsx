import { RiskGauge } from './RiskScore.jsx';
import { getEntityColor, getStatusBadge, formatRelativeTime, getSourceTierLabel } from '../utils.js';

export default function AlertDetail({ alert, onClose, onStatusChange }) {
  if (!alert) return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#374151',
      gap: '12px',
    }}>
      <div style={{ fontSize: '32px', opacity: 0.3 }}>◎</div>
      <div style={{ fontSize: '13px', fontFamily: 'Inter, sans-serif', color: '#374151' }}>Select an alert to view details</div>
      <div style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color: '#2E3340' }}>AWAITING SELECTION</div>
    </div>
  );

  const entityColor = getEntityColor(alert.entity_type);
  const status = getStatusBadge(alert.status);
  const STATUS_ACTIONS = {
    new: [{ label: 'Start Review', next: 'under_review', color: '#F59E0B' }],
    under_review: [
      { label: 'Confirm Threat', next: 'confirmed', color: '#EF4444' },
      { label: 'Dismiss', next: 'dismissed', color: '#6B7280' },
    ],
    confirmed: [{ label: 'Reopen', next: 'under_review', color: '#F59E0B' }],
    dismissed: [{ label: 'Reopen', next: 'new', color: '#F59E0B' }],
  };

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '20px',
    }} className="animate-slide-right">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: '20px', gap: '12px' }}>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: 'Syne, sans-serif',
            fontWeight: '700',
            fontSize: '18px',
            color: '#F1F5F9',
            marginBottom: '4px',
          }}>{alert.entity_name}</div>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '10px',
            color: entityColor,
            letterSpacing: '0.05em',
          }}>
            <span style={{
              width: '6px', height: '6px',
              borderRadius: '50%',
              background: entityColor,
              display: 'inline-block',
              marginRight: '5px',
              boxShadow: `0 0 4px ${entityColor}`,
            }} />
            {alert.entity_type.replace('_', ' ').toUpperCase()}
          </div>
        </div>
        <RiskGauge score={alert.risk_score} size={80} />
      </div>

      {/* Alert ID + time */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '16px',
        padding: '8px 12px',
        background: 'rgba(255,255,255,0.02)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.05)',
      }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#F59E0B' }}>{alert.id}</span>
        <span style={{ color: '#2E3340' }}>·</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#4B5563' }}>{alert.source}</span>
        <span style={{ color: '#2E3340' }}>·</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#374151' }}>{formatRelativeTime(alert.timestamp)}</span>
        <span style={{ marginLeft: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: '9px', color: '#4B5563' }}>
          {getSourceTierLabel(alert.source_tier)}
        </span>
      </div>

      {/* Alert type */}
      <div style={{
        padding: '10px 14px',
        background: 'rgba(239,68,68,0.06)',
        border: '1px solid rgba(239,68,68,0.15)',
        borderRadius: '8px',
        marginBottom: '16px',
      }}>
        <div style={{ fontSize: '10px', color: '#6B7280', fontFamily: 'JetBrains Mono, monospace', marginBottom: '4px' }}>ALERT TYPE</div>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '13px', color: '#F87171' }}>
          {alert.alert_type}
        </div>
      </div>

      {/* Summary */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '6px' }}>SUMMARY</div>
        <p style={{ fontSize: '13px', color: '#9CA3AF', lineHeight: '1.6' }}>{alert.summary}</p>
      </div>

      {/* Primary ID + Aliases */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>IDENTIFIERS</div>
        <div style={{
          background: '#0D0F14',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 12px',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>PRIMARY</span>
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: entityColor }}>{alert.primary_id}</span>
          </div>
          {alert.aliases.map((alias, i) => (
            <div key={i} style={{
              padding: '7px 12px',
              borderBottom: i < alert.aliases.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}>
              <span style={{ fontSize: '10px', color: '#2E3340', fontFamily: 'JetBrains Mono, monospace' }}>ALIAS</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#6B7280' }}>{alias}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Factors */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
          RISK FACTORS (TOP {alert.risk_factors.length})
        </div>
        {alert.risk_factors.map((f, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            padding: '8px 12px',
            background: '#0D0F14',
            borderRadius: '6px',
            marginBottom: '4px',
            border: '1px solid rgba(255,255,255,0.05)',
          }}>
            <span style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              color: '#F59E0B',
              width: '16px',
              flexShrink: 0,
            }}>#{i + 1}</span>
            <span style={{ fontSize: '12px', color: '#9CA3AF', lineHeight: '1.4' }}>{f}</span>
          </div>
        ))}
      </div>

      {/* Status Actions */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: '8px' }}>
          STATUS — <span style={{ color: status.color }}>{status.label}</span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(STATUS_ACTIONS[alert.status] || []).map(action => (
            <button
              key={action.next}
              onClick={() => onStatusChange(alert.id, action.next)}
              style={{
                padding: '7px 14px',
                background: 'transparent',
                border: `1px solid ${action.color}40`,
                borderRadius: '6px',
                color: action.color,
                fontSize: '11px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = `${action.color}15`; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >{action.label}</button>
          ))}
          <button
            style={{
              padding: '7px 14px',
              background: 'transparent',
              border: '1px solid rgba(59,130,246,0.3)',
              borderRadius: '6px',
              color: '#3B82F6',
              fontSize: '11px',
              fontFamily: 'Inter, sans-serif',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(59,130,246,0.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >⬡ View Graph</button>
          <button
            style={{
              padding: '7px 14px',
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px',
              color: '#6B7280',
              fontSize: '11px',
              fontFamily: 'Inter, sans-serif',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.15s',
              marginLeft: 'auto',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >↓ Export PDF</button>
        </div>
      </div>
    </div>
  );
}
