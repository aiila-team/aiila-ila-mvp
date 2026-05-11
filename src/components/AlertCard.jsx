import { RiskScoreBadge } from './RiskScore.jsx';
import { formatRelativeTime, getEntityColor, getStatusBadge } from '../utils.js';

const FLAG_LABELS = {
  velocity_anomaly: 'Velocity ⚡',
  pattern_match: 'Pattern ◆',
  negative_sentiment: 'Sentiment ↓',
  coordinated_behavior: 'Coordinated ⬡',
  sim_cluster: 'SIM Cluster',
  phishing: 'Phishing ⚠',
  domain_cluster: 'Domains',
  ocr_detected: 'OCR',
  hawala: 'Hawala',
  keyword_match: 'Keyword',
  crypto_layering: 'Crypto ↺',
  network_centrality: 'Network Hub',
  anomaly_detection: 'Anomaly',
  inauthentic_content: 'Inauthentic',
};

export default function AlertCard({ alert, onClick, selected }) {
  const entityColor = getEntityColor(alert.entity_type);
  const statusBadge = getStatusBadge(alert.status);

  return (
    <div
      onClick={() => onClick(alert)}
      className="animate-slide-right"
      style={{
        background: selected ? 'rgba(245,158,11,0.05)' : '#13161D',
        border: `1px solid ${selected ? 'rgba(245,158,11,0.3)' : 'rgba(255,255,255,0.06)'}`,
        borderRadius: '10px',
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'all 0.15s',
        marginBottom: '8px',
        borderLeft: `3px solid ${selected ? '#F59E0B' : 'rgba(255,255,255,0.06)'}`,
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => {
        if (!selected) {
          e.currentTarget.style.background = '#1A1E27';
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
        }
      }}
      onMouseLeave={e => {
        if (!selected) {
          e.currentTarget.style.background = '#13161D';
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
        }
      }}
    >
      {/* NEW pulse indicator */}
      {alert.status === 'new' && (
        <div style={{
          position: 'absolute',
          top: '14px',
          right: '14px',
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: '#EF4444',
          animation: 'blink 1.4s infinite',
        }} />
      )}

      {/* Top row: entity name + type + risk */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        {/* Entity type dot */}
        <div style={{
          width: '8px', height: '8px',
          borderRadius: '50%',
          background: entityColor,
          flexShrink: 0,
          boxShadow: `0 0 6px ${entityColor}60`,
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: 'Syne, sans-serif',
            fontWeight: '600',
            fontSize: '14px',
            color: '#F1F5F9',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>{alert.entity_name}</div>
        </div>
        <RiskScoreBadge score={alert.risk_score} size="sm" />
      </div>

      {/* Alert type */}
      <div style={{
        fontSize: '11px',
        fontFamily: 'JetBrains Mono, monospace',
        color: '#F59E0B',
        marginBottom: '6px',
        letterSpacing: '0.02em',
      }}>
        {alert.alert_type.toUpperCase()}
      </div>

      {/* Summary snippet */}
      <div style={{
        fontSize: '12px',
        color: '#6B7280',
        lineHeight: '1.5',
        marginBottom: '10px',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {alert.summary}
      </div>

      {/* Bottom row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        {/* Status */}
        <span style={{
          fontSize: '9px',
          fontFamily: 'JetBrains Mono, monospace',
          fontWeight: '600',
          color: statusBadge.color,
          background: statusBadge.bg,
          borderRadius: '3px',
          padding: '2px 5px',
          letterSpacing: '0.06em',
        }}>{statusBadge.label}</span>

        {/* Source */}
        <span style={{
          fontSize: '10px',
          color: '#4B5563',
          background: 'rgba(255,255,255,0.04)',
          borderRadius: '3px',
          padding: '2px 5px',
          fontFamily: 'Inter, sans-serif',
        }}>
          {alert.source}
        </span>

        {/* Flags */}
        {alert.flags.slice(0, 2).map(flag => (
          <span key={flag} style={{
            fontSize: '9px',
            color: '#374151',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '3px',
            padding: '2px 5px',
            fontFamily: 'JetBrains Mono, monospace',
          }}>{FLAG_LABELS[flag] || flag}</span>
        ))}

        {/* Time */}
        <span style={{
          marginLeft: 'auto',
          fontSize: '10px',
          color: '#374151',
          fontFamily: 'JetBrains Mono, monospace',
        }}>{formatRelativeTime(alert.timestamp)}</span>
      </div>
    </div>
  );
}
