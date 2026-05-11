import { useState, useEffect, useRef } from 'react';

/* ─────────────────────────────────────────
   MOCK DATA
───────────────────────────────────────── */
const MOCK_ALERTS = [
  {
    id: 'ALT-7821', entity_name: 'aadhaar-update-portal.in', entity_type: 'domain',
    alert_type: 'Phishing Domain Detected', risk_score: 94,
    status: 'new', source: 'OSINT-Feed', source_tier: 1,
    summary: 'New phishing domain detected: aadhaar-update-portal.in (lookalike score: 0.92). Domain registered 6 hours ago with privacy-protected WHOIS.',
    primary_id: 'DOM-9921-IN', aliases: ['update-aadhaar.in', 'aadhar-portal.net'],
    flags: ['phishing', 'domain_cluster', 'velocity_anomaly'],
    timestamp: Date.now() - 1000 * 60 * 8,
    severity: 'critical', type: 'Entity',
  },
  {
    id: 'ALT-7820', entity_name: 'UPI transfer.fast@paytm', entity_type: 'account',
    alert_type: 'Financial Fraud Pattern', risk_score: 88,
    status: 'new', source: 'FinInt-API', source_tier: 2,
    summary: 'Financial fraud pattern: UPI transfer.fast@paytm linked to 28 mule accounts across 4 banks. Transaction velocity 340% above baseline.',
    primary_id: 'ACC-4471-FIN', aliases: ['@paytm_fast', 'upi.transfer22'],
    flags: ['hawala', 'velocity_anomaly', 'network_centrality'],
    timestamp: Date.now() - 1000 * 60 * 33,
    severity: 'critical', type: 'Fraud',
  },
  {
    id: 'ALT-7819', entity_name: 'Bomb Threat — Kolkata Metro', entity_type: 'event',
    alert_type: 'Threat Escalation', risk_score: 97,
    status: 'under_review', source: 'SocMed-Monitor', source_tier: 1,
    summary: 'Threat escalation: bomb threat mentions in Kolkata exceed alert threshold. 47 coordinated posts across 3 platforms within 12 minutes.',
    primary_id: 'EVT-0033-KOL', aliases: [],
    flags: ['coordinated_behavior', 'keyword_match', 'velocity_anomaly'],
    timestamp: Date.now() - 1000 * 60 * 55,
    severity: 'critical', type: 'Terrorism',
  },
  {
    id: 'ALT-7818', entity_name: '@NarendraModi_Fan99', entity_type: 'account',
    alert_type: 'Inauthentic Coordinated Behaviour', risk_score: 71,
    status: 'new', source: 'Twitter-API', source_tier: 2,
    summary: 'Account shows signs of coordinated inauthentic behaviour. Part of a 214-node botnet amplifying political disinformation.',
    primary_id: 'TW-8812-IN', aliases: ['@NaMo_fan99', '@Supporter_Modi9'],
    flags: ['coordinated_behavior', 'inauthentic_content', 'sim_cluster'],
    timestamp: Date.now() - 1000 * 60 * 90,
    severity: 'high', type: 'Threat',
  },
  {
    id: 'ALT-7817', entity_name: 'Investment Scheme — Srinagar', entity_type: 'event',
    alert_type: 'Threat Escalation', risk_score: 82,
    status: 'new', source: 'SocMed-Monitor', source_tier: 1,
    summary: 'Threat escalation: investment scheme mentions in Srinagar exceed alert threshold. Likely Ponzi structure with 1,200+ victims identified.',
    primary_id: 'EVT-0034-SRN', aliases: [],
    flags: ['keyword_match', 'network_centrality', 'pattern_match'],
    timestamp: Date.now() - 1000 * 60 * 108,
    severity: 'critical', type: 'Fraud',
  },
  {
    id: 'ALT-7816', entity_name: 'RBI Digital Fraud Narrative', entity_type: 'narrative',
    alert_type: 'Coordinated Narrative Spread', risk_score: 65,
    status: 'confirmed', source: 'OSINT-Feed', source_tier: 1,
    summary: 'RBI is mulling measures to tackle rising cases of digital fraud in India. Coordinated amplification detected across Telegram channels.',
    primary_id: 'NAR-2201-FIN', aliases: [],
    flags: ['coordinated_behavior', 'negative_sentiment', 'pattern_match'],
    timestamp: Date.now() - 1000 * 60 * 142,
    severity: 'high', type: 'Fraud',
  },
  {
    id: 'ALT-7815', entity_name: 'Operation Sindoor — Anniversary', entity_type: 'event',
    alert_type: 'Narrative Amplification', risk_score: 58,
    status: 'dismissed', source: 'NewsAPI', source_tier: 3,
    summary: 'India marked the first anniversary of Operation Sindoor. Spike in cross-border messaging with glorification patterns detected.',
    primary_id: 'EVT-0031-DEL', aliases: [],
    flags: ['keyword_match', 'coordinated_behavior'],
    timestamp: Date.now() - 1000 * 60 * 180,
    severity: 'medium', type: 'Terrorism',
  },
  {
    id: 'ALT-7814', entity_name: 'Air India Multi-Modal Hub', entity_type: 'narrative',
    alert_type: 'Sensitive Infrastructure Mention', risk_score: 44,
    status: 'new', source: 'NewsAPI', source_tier: 3,
    summary: 'High threat detected: The airport has been developed with the vision of an integrated multi-modal connectivity hub, drawing attention from adversarial actors.',
    primary_id: 'NAR-2199-INF', aliases: [],
    flags: ['keyword_match', 'negative_sentiment'],
    timestamp: Date.now() - 1000 * 60 * 210,
    severity: 'info', type: 'Threat',
  },
];

/* ─────────────────────────────────────────
   HELPERS
───────────────────────────────────────── */
const SEVERITY_CFG = {
  critical: { color: '#EF4444', bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.25)', label: 'CRITICAL' },
  high:     { color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', label: 'HIGH' },
  medium:   { color: '#3B82F6', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.25)', label: 'MEDIUM' },
  info:     { color: '#6B7280', bg: 'rgba(107,114,128,0.12)', border: 'rgba(107,114,128,0.2)', label: 'INFO' },
};
const STATUS_CFG = {
  new:          { color: '#EF4444', bg: 'rgba(239,68,68,0.1)', label: 'NEW' },
  under_review: { color: '#F59E0B', bg: 'rgba(245,158,11,0.1)', label: 'REVIEWING' },
  confirmed:    { color: '#10B981', bg: 'rgba(16,185,129,0.1)', label: 'CONFIRMED' },
  dismissed:    { color: '#4B5563', bg: 'rgba(75,85,99,0.1)', label: 'DISMISSED' },
};
const ENTITY_COLOR = {
  domain: '#A78BFA', account: '#34D399', event: '#F87171', narrative: '#60A5FA',
};
const FLAG_LABELS = {
  velocity_anomaly: 'Velocity ⚡', pattern_match: 'Pattern ◆', negative_sentiment: 'Sentiment ↓',
  coordinated_behavior: 'Coordinated ⬡', sim_cluster: 'SIM Cluster', phishing: 'Phishing ⚠',
  domain_cluster: 'Domains', ocr_detected: 'OCR', hawala: 'Hawala', keyword_match: 'Keyword',
  crypto_layering: 'Crypto ↺', network_centrality: 'Network Hub', anomaly_detection: 'Anomaly',
  inauthentic_content: 'Inauthentic',
};
const TYPE_OPTIONS = ['All Types', 'Threat', 'Fraud', 'Terrorism', 'Entity'];
const SEVERITY_OPTIONS = ['all', 'critical', 'high', 'medium', 'info'];

function formatTime(ts) {
  const diff = Date.now() - ts;
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function RiskBadge({ score }) {
  const color = score >= 85 ? '#EF4444' : score >= 65 ? '#F59E0B' : '#3B82F6';
  return (
    <div style={{
      width: 34, height: 34, borderRadius: '50%',
      border: `2px solid ${color}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 10, fontWeight: 700, color,
      fontFamily: 'JetBrains Mono, monospace',
      background: `${color}10`, flexShrink: 0,
      boxShadow: `0 0 8px ${color}30`,
    }}>{score}</div>
  );
}

/* ─────────────────────────────────────────
   ALERT ROW (table row style like screenshot)
───────────────────────────────────────── */
function AlertRow({ alert, selected, onClick }) {
  const [hovered, setHovered] = useState(false);
  const sev = SEVERITY_CFG[alert.severity] || SEVERITY_CFG.info;

  return (
    <div
      onClick={() => onClick(alert)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'grid',
        gridTemplateColumns: '100px 1fr 110px 140px 64px',
        alignItems: 'center',
        gap: 12,
        padding: '11px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        borderLeft: `3px solid ${selected ? sev.color : 'transparent'}`,
        background: selected
          ? `${sev.color}08`
          : hovered ? 'rgba(255,255,255,0.025)' : 'transparent',
        cursor: 'pointer',
        transition: 'all 0.12s',
      }}
    >
      {/* Severity badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {alert.status === 'new' && (
          <div style={{
            width: 5, height: 5, borderRadius: '50%',
            background: sev.color, flexShrink: 0,
            boxShadow: `0 0 6px ${sev.color}`,
            animation: 'blink 1.5s infinite',
          }} />
        )}
        <span style={{
          fontSize: 9, fontWeight: 700, letterSpacing: '0.06em',
          fontFamily: 'JetBrains Mono, monospace',
          color: sev.color, background: sev.bg,
          border: `1px solid ${sev.border}`,
          padding: '2px 7px', borderRadius: 3,
        }}>{sev.label}</span>
      </div>

      {/* Title */}
      <div>
        <div style={{
          fontSize: 12.5, color: '#D1D5DB',
          fontFamily: 'Inter, sans-serif',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          maxWidth: 480,
        }}>{alert.summary}</div>
        <div style={{
          fontSize: 10, color: '#4B5563',
          fontFamily: 'JetBrains Mono, monospace',
          marginTop: 2,
        }}>{alert.id} · {alert.entity_name}</div>
      </div>

      {/* Type */}
      <div style={{
        fontSize: 10, color: '#6B7280',
        fontFamily: 'JetBrains Mono, monospace',
        letterSpacing: '0.04em',
      }}>{alert.type}</div>

      {/* Time */}
      <div style={{
        fontSize: 10, color: '#4B5563',
        fontFamily: 'JetBrains Mono, monospace',
      }}>{new Date(alert.timestamp).toLocaleString('en-IN', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', hour12: false,
      })}</div>

      {/* ACK button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={e => { e.stopPropagation(); }}
          style={{
            padding: '4px 10px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 4, color: '#6B7280',
            fontSize: 10, fontFamily: 'JetBrains Mono, monospace',
            cursor: 'pointer', letterSpacing: '0.04em',
            transition: 'all 0.12s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#F59E0B'; e.currentTarget.style.borderColor = 'rgba(245,158,11,0.4)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = '#6B7280'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
        >ACK</button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   ALERT DETAIL PANEL
───────────────────────────────────────── */
function AlertDetail({ alert, onStatusChange, onClose }) {
  if (!alert) return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 12,
    }}>
      <div style={{ fontSize: 32, opacity: 0.15, color: '#00C2FF' }}>◎</div>
      <div style={{ fontSize: 12, fontFamily: 'Inter, sans-serif', color: '#374151' }}>Select an alert to inspect</div>
      <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#2A3140', letterSpacing: '0.1em' }}>AWAITING SELECTION</div>
    </div>
  );

  const entityColor = ENTITY_COLOR[alert.entity_type] || '#9CA3AF';
  const status = STATUS_CFG[alert.status];
  const sev = SEVERITY_CFG[alert.severity] || SEVERITY_CFG.info;
  const scoreColor = alert.risk_score >= 85 ? '#EF4444' : alert.risk_score >= 65 ? '#F59E0B' : '#3B82F6';

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
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 18px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 18 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: 'Syne, sans-serif', fontWeight: 700,
            fontSize: 16, color: '#F1F5F9', marginBottom: 5,
            lineHeight: 1.3,
          }}>{alert.entity_name}</div>
          <div style={{
            fontSize: 10, fontFamily: 'JetBrains Mono, monospace',
            color: entityColor, letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: entityColor,
              display: 'inline-block', boxShadow: `0 0 4px ${entityColor}`,
            }} />
            {alert.entity_type.replace('_', ' ').toUpperCase()}
          </div>
        </div>
        {/* Risk ring */}
        <div style={{ position: 'relative', width: 56, height: 56, flexShrink: 0 }}>
          <svg width="56" height="56" viewBox="0 0 56 56">
            <circle cx="28" cy="28" r="24" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
            <circle cx="28" cy="28" r="24" fill="none" stroke={scoreColor} strokeWidth="3"
              strokeDasharray={`${2 * Math.PI * 24 * alert.risk_score / 100} ${2 * Math.PI * 24}`}
              strokeLinecap="round" transform="rotate(-90 28 28)"
              style={{ filter: `drop-shadow(0 0 4px ${scoreColor})` }}
            />
          </svg>
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: scoreColor, fontFamily: 'JetBrains Mono, monospace', lineHeight: 1 }}>{alert.risk_score}</div>
            <div style={{ fontSize: 7, color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>RISK</div>
          </div>
        </div>
      </div>

      {/* Meta row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 12px', background: 'rgba(255,255,255,0.02)',
        borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)',
        marginBottom: 14, flexWrap: 'wrap',
      }}>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#F59E0B' }}>{alert.id}</span>
        <span style={{ color: '#2A3140' }}>·</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#4B5563' }}>{alert.source}</span>
        <span style={{ color: '#2A3140' }}>·</span>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#374151' }}>{formatTime(alert.timestamp)}</span>
        <span style={{
          marginLeft: 'auto', fontSize: 9, fontFamily: 'JetBrains Mono, monospace',
          color: sev.color, background: sev.bg, padding: '2px 6px',
          borderRadius: 3, border: `1px solid ${sev.border}`,
        }}>{sev.label}</span>
      </div>

      {/* Alert type */}
      <div style={{
        padding: '10px 14px', background: 'rgba(239,68,68,0.05)',
        border: '1px solid rgba(239,68,68,0.12)', borderRadius: 7, marginBottom: 14,
      }}>
        <div style={{ fontSize: 9, color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4, letterSpacing: '0.1em' }}>ALERT TYPE</div>
        <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: 600, fontSize: 13, color: '#F87171' }}>{alert.alert_type}</div>
      </div>

      {/* Summary */}
      <Section label="SUMMARY">
        <p style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.6, margin: 0 }}>{alert.summary}</p>
      </Section>

      {/* Identifiers */}
      <Section label="IDENTIFIERS">
        <div style={{ background: '#0A0D12', borderRadius: 7, border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}>
          <IDRow label="PRIMARY" value={alert.primary_id} color={entityColor} />
          {alert.aliases.map((a, i) => <IDRow key={i} label="ALIAS" value={a} color="#4B5563" />)}
        </div>
      </Section>

      {/* Flags */}
      <Section label="INTELLIGENCE FLAGS">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {alert.flags.map(f => (
            <span key={f} style={{
              fontSize: 9, fontFamily: 'JetBrains Mono, monospace',
              color: '#F59E0B', background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.2)',
              padding: '3px 8px', borderRadius: 3,
            }}>{FLAG_LABELS[f] || f}</span>
          ))}
        </div>
      </Section>

      {/* Status actions */}
      <Section label={`STATUS — ${status.label}`} labelColor={status.color}>
        <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
          {(STATUS_ACTIONS[alert.status] || []).map(action => (
            <ActionBtn key={action.next} color={action.color} onClick={() => onStatusChange(alert.id, action.next)}>
              {action.label}
            </ActionBtn>
          ))}
          <ActionBtn color="#3B82F6">⬡ View Graph</ActionBtn>
          <ActionBtn color="#4B5563" style={{ marginLeft: 'auto' }}>↓ Export PDF</ActionBtn>
        </div>
      </Section>
    </div>
  );
}

function Section({ label, labelColor, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{
        fontSize: 9, color: labelColor || '#4B5563',
        fontFamily: 'JetBrains Mono, monospace',
        letterSpacing: '0.12em', marginBottom: 7,
      }}>{label}</div>
      {children}
    </div>
  );
}

function IDRow({ label, value, color }) {
  return (
    <div style={{
      padding: '7px 12px', borderBottom: '1px solid rgba(255,255,255,0.04)',
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <span style={{ fontSize: 9, color: '#2E3340', fontFamily: 'JetBrains Mono, monospace', width: 44, flexShrink: 0 }}>{label}</span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color }}>{value}</span>
    </div>
  );
}

function ActionBtn({ color, children, onClick, style: extraStyle }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '6px 13px',
        background: hov ? `${color}18` : 'transparent',
        border: `1px solid ${color}40`,
        borderRadius: 6, color,
        fontSize: 11, fontFamily: 'Inter, sans-serif', fontWeight: 500,
        cursor: 'pointer', transition: 'all 0.15s',
        ...extraStyle,
      }}
    >{children}</button>
  );
}

/* ─────────────────────────────────────────
   STATS BAR
───────────────────────────────────────── */
function StatChip({ label, value, color }) {
  return (
    <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>
      <span style={{ color: '#4B5563' }}>{label}: </span>
      <span style={{ color, fontWeight: 700 }}>{value}</span>
    </span>
  );
}

/* ─────────────────────────────────────────
   MAIN PAGE
───────────────────────────────────────── */
export default function AlertsPage() {
 const [alerts, setAlerts] = useState(MOCK_ALERTS);
  const [selected, setSelected] = useState(MOCK_ALERTS[0]);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('All Types');
  const [search, setSearch] = useState('');
  const [liveCount, setLiveCount] = useState(289);

  // Simulate live count ticking
  useEffect(() => {
    const t = setInterval(() => setLiveCount(c => c + Math.floor(Math.random() * 2)), 8000);
    return () => clearInterval(t);
  }, []);

  const filtered = alerts.filter(a => {
    if (severityFilter !== 'all' && a.severity !== severityFilter) return false;
    if (typeFilter !== 'All Types' && a.type !== typeFilter) return false;
    if (search && !a.summary.toLowerCase().includes(search.toLowerCase()) &&
        !a.entity_name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    total: liveCount,
    unread: alerts.filter(a => a.status === 'new').length,
    critical: alerts.filter(a => a.severity === 'critical').length,
    high: alerts.filter(a => a.severity === 'high').length,
    medium: alerts.filter(a => a.severity === 'medium').length,
    info: alerts.filter(a => a.severity === 'info').length,
  };

  function handleStatusChange(id, nextStatus) {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: nextStatus } : a));
    setSelected(prev => prev?.id === id ? { ...prev, status: nextStatus } : prev);
  }

  const SelectStyle = {
    background: '#0D1017',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: 6,
    color: '#9CA3AF',
    fontSize: 12,
    fontFamily: 'JetBrains Mono, monospace',
    padding: '6px 10px',
    cursor: 'pointer',
    outline: 'none',
    appearance: 'none',
    paddingRight: 28,
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', background: '#080C14', overflow: 'hidden',
      fontFamily: 'Inter, sans-serif',
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:translateY(0)} }
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:rgba(0,194,255,0.15);border-radius:2px}
        select option { background: #0D1017; }
      `}</style>

      {/* Top Header */}
      <div style={{
        padding: '14px 24px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 16,
        flexShrink: 0, background: '#080C14',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <h1 style={{
              fontFamily: 'Syne, sans-serif', fontSize: 22, fontWeight: 700,
              color: '#F1F5F9', letterSpacing: '-0.01em', margin: 0,
            }}>
              <span style={{ color: '#EF4444' }}>ALERT</span>
              <span style={{ color: '#E5E7EB' }}> MANAGEMENT</span>
            </h1>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)',
              borderRadius: 20, padding: '3px 10px',
            }}>
              <div style={{
                width: 5, height: 5, borderRadius: '50%',
                background: '#10B981', animation: 'blink 1.5s infinite',
                boxShadow: '0 0 5px #10B981',
              }} />
              <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace', color: '#10B981', letterSpacing: '0.08em' }}>LIVE</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <StatChip label="TOTAL" value={counts.total} color="#E5E7EB" />
            <StatChip label="UNREAD" value={counts.unread} color="#EF4444" />
            <StatChip label="Critical" value={counts.critical} color="#EF4444" />
            <StatChip label="High" value={counts.high} color="#F59E0B" />
            <StatChip label="Info" value={counts.info} color="#6B7280" />
            <StatChip label="Medium" value={counts.medium} color="#3B82F6" />
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{
        padding: '10px 24px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        display: 'flex', alignItems: 'center', gap: 10,
        background: '#060A11', flexShrink: 0,
      }}>
        {/* Severity pills */}
        <div style={{ display: 'flex', gap: 4 }}>
          {SEVERITY_OPTIONS.map(s => {
            const cfg = s === 'all' ? { color: '#9CA3AF', bg: 'rgba(156,163,175,0.1)', border: 'rgba(156,163,175,0.2)', label: 'ALL' } : SEVERITY_CFG[s];
            const active = severityFilter === s;
            return (
              <button key={s} onClick={() => setSeverityFilter(s)} style={{
                padding: '5px 11px', borderRadius: 5,
                border: `1px solid ${active ? cfg.border || cfg.color+'40' : 'rgba(255,255,255,0.07)'}`,
                background: active ? cfg.bg : 'transparent',
                color: active ? cfg.color : '#4B5563',
                fontSize: 9, fontFamily: 'JetBrains Mono, monospace',
                fontWeight: 700, letterSpacing: '0.06em', cursor: 'pointer',
                transition: 'all 0.12s',
              }}>{(cfg.label || s.toUpperCase())}</button>
            );
          })}
        </div>

        <div style={{ width: 1, height: 20, background: 'rgba(255,255,255,0.07)' }} />

        {/* Type dropdown */}
        <div style={{ position: 'relative' }}>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={SelectStyle}>
            {TYPE_OPTIONS.map(t => <option key={t}>{t}</option>)}
          </select>
          <span style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: '#4B5563', pointerEvents: 'none', fontSize: 10 }}>▾</span>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <span style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', fontSize: 11, color: '#4B5563' }}>⌕</span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search alerts..."
            style={{
              background: '#0D1017', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 6, color: '#9CA3AF', fontSize: 12,
              fontFamily: 'JetBrains Mono, monospace',
              padding: '6px 10px 6px 26px', width: 200, outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Body: table + detail */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Left: table */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          overflow: 'hidden', minWidth: 0,
        }}>
          {/* Table header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '100px 1fr 110px 140px 64px',
            gap: 12, padding: '8px 16px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            background: '#060A11',
          }}>
            {['SEVERITY', 'TITLE', 'TYPE', 'TIME', 'ACTION'].map(h => (
              <div key={h} style={{
                fontSize: 9, fontFamily: 'JetBrains Mono, monospace',
                color: '#2E3340', letterSpacing: '0.12em',
                textAlign: h === 'ACTION' ? 'right' : 'left',
              }}>{h}</div>
            ))}
          </div>

          {/* Rows */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {filtered.length === 0 ? (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: 120, color: '#2E3340',
                fontSize: 12, fontFamily: 'JetBrains Mono, monospace',
              }}>NO ALERTS MATCH FILTER</div>
            ) : filtered.map(alert => (
              <AlertRow
                key={alert.id}
                alert={alert}
                selected={selected?.id === alert.id}
                onClick={setSelected}
              />
            ))}
          </div>

          {/* Table footer */}
          <div style={{
            padding: '8px 16px', borderTop: '1px solid rgba(255,255,255,0.05)',
            display: 'flex', alignItems: 'center', gap: 10,
            background: '#060A11',
          }}>
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#2E3340' }}>
              SHOWING {filtered.length} OF {alerts.length} ALERTS
            </span>
            <span style={{ marginLeft: 'auto', fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#2A3140' }}>
              LAST SYNC: {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </span>
          </div>
        </div>

        {/* Right: detail */}
        <div style={{
          width: 340, minWidth: 340,
          display: 'flex', flexDirection: 'column',
          background: '#060A11',
          overflow: 'hidden',
        }}>
          {/* Detail header */}
          <div style={{
            padding: '10px 18px',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono, monospace', color: '#2E3340', letterSpacing: '0.12em' }}>ALERT DETAIL</span>
            {selected && (
              <span style={{
                fontSize: 9, fontFamily: 'JetBrains Mono, monospace', color: '#F59E0B',
                background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
                padding: '1px 6px', borderRadius: 3, marginLeft: 4,
              }}>{selected.id}</span>
            )}
          </div>
          <AlertDetail
            alert={selected}
            onStatusChange={handleStatusChange}
          />
        </div>
      </div>
    </div>
  );
}