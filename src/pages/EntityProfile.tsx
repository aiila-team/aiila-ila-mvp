import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

// ─── Types ────────────────────────────────────────────────────────────────────

type EntityType = 'person' | 'organization' | 'device' | 'account' | 'unknown';

interface Alias {
  id: string;
  type: 'phone' | 'email' | 'username' | 'upi' | 'pan' | 'aadhaar' | 'ip' | 'other';
  value: string;
  verified?: boolean;
}

interface TimelineEvent {
  id: string;
  timestamp: string;           // ISO string
  source: string;              // e.g. "CIBIL", "FIU-IND", "ED Portal"
  event_type: string;          // e.g. "flagged", "transaction", "login"
  description: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
}

interface Entity {
  id: string;
  name: string;
  type: EntityType;
  risk_score: number;          // 0–100
  description?: string;
  tags?: string[];
  aliases?: Alias[];
  first_seen: string;
  last_seen: string;
  linked_entities?: string[];
  timeline?: TimelineEvent[];
}

// ─── Mock data (replace with real API calls) ──────────────────────────────────

const MOCK_ENTITY: Entity = {
  id: 'ENT-20481',
  name: 'Rajesh Kumar Verma',
  type: 'person',
  risk_score: 76,
  description: 'Subject flagged across multiple FIU-IND reports for layered cash transactions. Associated with shell entities in Hyderabad and Dubai.',
  tags: ['shell-company', 'hawala', 'cross-border'],
  first_seen: '2021-03-14T10:22:00Z',
  last_seen:  '2024-11-08T18:44:00Z',
  linked_entities: ['ENT-10023', 'ENT-10091', 'ENT-20102', 'ENT-30084'],
  aliases: [
    { id: 'a1', type: 'phone',    value: '+91 98765 43210', verified: true },
    { id: 'a2', type: 'phone',    value: '+971 50 123 4567' },
    { id: 'a3', type: 'email',    value: 'r.verma@fintrade.co', verified: true },
    { id: 'a4', type: 'email',    value: 'rajesh.k1981@proton.me' },
    { id: 'a5', type: 'username', value: 'r_verma_81' },
    { id: 'a6', type: 'username', value: 'trade_king_hyd' },
    { id: 'a7', type: 'upi',      value: 'r.verma@ybl', verified: true },
    { id: 'a8', type: 'upi',      value: 'rverma81@okicici' },
    { id: 'a9', type: 'pan',      value: 'ABCPK1234F', verified: true },
    { id: 'a10', type: 'ip',      value: '103.24.77.211' },
  ],
  timeline: [
    { id: 't1', timestamp: '2021-03-14T10:22:00Z', source: 'FIU-IND',    event_type: 'initial_flag',   description: 'First STR filed by HDFC Bank for ₹48L cash deposit in 3 transactions.', severity: 'high' },
    { id: 't2', timestamp: '2021-09-02T08:11:00Z', source: 'ED Portal',  event_type: 'enquiry_open',   description: 'Enforcement Directorate opened FEMA enquiry case EDF/21/0837.', severity: 'high' },
    { id: 't3', timestamp: '2022-02-17T14:55:00Z', source: 'CIBIL',      event_type: 'credit_check',   description: 'Hard inquiry from private lender; loan application for ₹1.2Cr.', severity: 'low' },
    { id: 't4', timestamp: '2022-07-29T09:30:00Z', source: 'NPCI',       event_type: 'upi_volume',     description: 'UPI transaction volume exceeded ₹10L in a single day — threshold alert.', severity: 'medium' },
    { id: 't5', timestamp: '2022-12-05T19:02:00Z', source: 'FIU-IND',    event_type: 'second_str',     description: 'Second STR from Axis Bank; cross-border wire to Dubai account.', severity: 'critical' },
    { id: 't6', timestamp: '2023-04-13T11:18:00Z', source: 'CBI',        event_type: 'notice_issued',  description: 'Look-out circular issued; passport flagged for overseas travel restriction.', severity: 'critical' },
    { id: 't7', timestamp: '2023-08-22T16:45:00Z', source: 'GSTN',       event_type: 'gst_mismatch',   description: 'GST return mismatch detected; ₹3.4Cr under-reported turnover (FY23).', severity: 'high' },
    { id: 't8', timestamp: '2024-01-10T12:00:00Z', source: 'ED Portal',  event_type: 'asset_attached', description: 'Provisional attachment order on residential property — ₹2.1Cr.', severity: 'critical' },
    { id: 't9', timestamp: '2024-06-30T08:55:00Z', source: 'NPCI',       event_type: 'account_freeze', description: 'Two linked bank accounts frozen on court order.', severity: 'high' },
    { id: 't10', timestamp: '2024-11-08T18:44:00Z', source: 'FIU-IND',   event_type: 'update',         description: 'Case status updated: active investigation; 3 new associate entities added.', severity: 'medium' },
  ],
};

// ─── Constants ────────────────────────────────────────────────────────────────

const SEVERITY_META = {
  low:      { label: 'LOW',      color: '#42be65', bg: 'rgba(66,190,101,0.12)'  },
  medium:   { label: 'MED',      color: '#f1c21b', bg: 'rgba(241,194,27,0.12)'  },
  high:     { label: 'HIGH',     color: '#ff832b', bg: 'rgba(255,131,43,0.12)'  },
  critical: { label: 'CRIT',     color: '#fa4d56', bg: 'rgba(250,77,86,0.12)'   },
};

const ALIAS_TYPE_META: Record<Alias['type'], { label: string; icon: string }> = {
  phone:    { label: 'PHONE',    icon: '📞' },
  email:    { label: 'EMAIL',    icon: '✉' },
  username: { label: 'USERNAME', icon: '👤' },
  upi:      { label: 'UPI ID',   icon: '₹' },
  pan:      { label: 'PAN',      icon: '🪪' },
  aadhaar:  { label: 'AADHAAR',  icon: '🔢' },
  ip:       { label: 'IP ADDR',  icon: '🌐' },
  other:    { label: 'OTHER',    icon: '🔗' },
};

const ENTITY_TYPE_ICON: Record<EntityType, string> = {
  person:       '◈',
  organization: '⬡',
  device:       '▣',
  account:      '◇',
  unknown:      '◌',
};

function riskColor(score: number): string {
  if (score >= 75) return '#fa4d56';
  if (score >= 50) return '#ff832b';
  if (score >= 25) return '#f1c21b';
  return '#42be65';
}

function riskLabel(score: number): string {
  if (score >= 75) return 'CRITICAL';
  if (score >= 50) return 'HIGH';
  if (score >= 25) return 'MEDIUM';
  return 'LOW';
}

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtFull(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Animated arc gauge */
const RiskGauge: React.FC<{ score: number }> = ({ score }) => {
  const [animated, setAnimated] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 80);
    return () => clearTimeout(t);
  }, [score]);

  const r = 44, cx = 56, cy = 56;
  const total = 2 * Math.PI * r;
  const arc = (animated / 100) * (total * 0.75);
  const color = riskColor(score);

  return (
    <svg width="112" height="112" viewBox="0 0 112 112" style={{ flexShrink: 0 }}>
      {/* track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#393939" strokeWidth="6"
        strokeDasharray={`${total * 0.75} ${total * 0.25}`}
        strokeLinecap="round"
        style={{ transform: 'rotate(135deg)', transformOrigin: `${cx}px ${cy}px` }} />
      {/* fill */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={`${arc} ${total - arc}`}
        strokeLinecap="round"
        style={{
          transform: 'rotate(135deg)',
          transformOrigin: `${cx}px ${cy}px`,
          transition: 'stroke-dasharray 0.9s cubic-bezier(.4,0,.2,1), stroke 0.4s',
          filter: `drop-shadow(0 0 6px ${color}88)`,
        }} />
      <text x={cx} y={cy - 4} textAnchor="middle" fill={color}
        style={{ fontSize: 20, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>
        {score}
      </text>
      <text x={cx} y={cy + 13} textAnchor="middle" fill="#6f6f6f"
        style={{ fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
        {riskLabel(score)}
      </text>
    </svg>
  );
};

/** One alias row */
const AliasRow: React.FC<{ alias: Alias }> = ({ alias }) => {
  const meta = ALIAS_TYPE_META[alias.type];
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '8px 12px',
      borderBottom: '1px solid #262626',
    }}>
      <span style={{ width: 80, fontSize: 10, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1 }}>
        {meta.icon} {meta.label}
      </span>
      <span style={{ flex: 1, fontSize: 13, color: '#f4f4f4', fontFamily: "'IBM Plex Mono', monospace" }}>
        {alias.value}
      </span>
      {alias.verified && (
        <span style={{
          fontSize: 10, padding: '1px 6px',
          background: 'rgba(66,190,101,0.15)', color: '#42be65',
          border: '1px solid rgba(66,190,101,0.3)',
          fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.5,
        }}>
          VERIFIED
        </span>
      )}
    </div>
  );
};

/** Timeline event row */
const TimelineRow: React.FC<{ event: TimelineEvent; last: boolean }> = ({ event, last }) => {
  const sev = SEVERITY_META[event.severity ?? 'low'];
  return (
    <div style={{ display: 'flex', gap: 0, position: 'relative' }}>
      {/* spine */}
      <div style={{ width: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, borderRadius: 0, background: sev.color,
          border: `2px solid ${sev.color}`,
          flexShrink: 0, zIndex: 1,
          boxShadow: `0 0 8px ${sev.color}88`,
        }} />
        {!last && <div style={{ width: 1, flex: 1, background: '#262626', minHeight: 32 }} />}
      </div>

      {/* content */}
      <div style={{ flex: 1, paddingBottom: last ? 0 : 24, paddingLeft: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{
            fontSize: 9, padding: '1px 6px',
            background: sev.bg, color: sev.color,
            border: `1px solid ${sev.color}44`,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1,
          }}>
            {sev.label}
          </span>
          <span style={{ fontSize: 10, color: '#a8a8a8', fontFamily: "'IBM Plex Mono', monospace" }}>
            {fmtFull(event.timestamp)}
          </span>
          <span style={{
            fontSize: 10, color: '#78a9ff',
            fontFamily: "'IBM Plex Mono', monospace",
          }}>
            {event.source}
          </span>
          <span style={{ fontSize: 10, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.5 }}>
            {event.event_type.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#c6c6c6', lineHeight: 1.5 }}>
          {event.description}
        </p>
      </div>
    </div>
  );
};

/** Graph placeholder */
const GraphPlaceholder: React.FC = () => (
  <div style={{
    height: 280,
    background: '#161616',
    border: '1px solid #393939',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    position: 'relative',
    overflow: 'hidden',
  }}>
    {/* decorative grid */}
    <svg style={{ position: 'absolute', inset: 0, opacity: 0.06 }} width="100%" height="100%">
      <defs>
        <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
          <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#78a9ff" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>

    {/* fake node-link sketch */}
    <svg width="260" height="140" style={{ opacity: 0.18 }}>
      <line x1="130" y1="70" x2="60"  y2="30"  stroke="#78a9ff" strokeWidth="1" strokeDasharray="4 2" />
      <line x1="130" y1="70" x2="200" y2="30"  stroke="#78a9ff" strokeWidth="1" strokeDasharray="4 2" />
      <line x1="130" y1="70" x2="50"  y2="110" stroke="#78a9ff" strokeWidth="1" strokeDasharray="4 2" />
      <line x1="130" y1="70" x2="210" y2="110" stroke="#78a9ff" strokeWidth="1" strokeDasharray="4 2" />
      <line x1="130" y1="70" x2="130" y2="20"  stroke="#78a9ff" strokeWidth="1" strokeDasharray="4 2" />
      <circle cx="130" cy="70"  r="14" fill="#262626" stroke="#fa4d56" strokeWidth="2" />
      <circle cx="60"  cy="30"  r="8"  fill="#262626" stroke="#78a9ff" strokeWidth="1.5" />
      <circle cx="200" cy="30"  r="8"  fill="#262626" stroke="#78a9ff" strokeWidth="1.5" />
      <circle cx="50"  cy="110" r="8"  fill="#262626" stroke="#78a9ff" strokeWidth="1.5" />
      <circle cx="210" cy="110" r="8"  fill="#262626" stroke="#78a9ff" strokeWidth="1.5" />
      <circle cx="130" cy="20"  r="6"  fill="#262626" stroke="#78a9ff" strokeWidth="1.5" />
    </svg>

    <div style={{ textAlign: 'center', zIndex: 1 }}>
      <p style={{ margin: 0, fontSize: 12, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1 }}>
        D3 GRAPH VISUALIZATION
      </p>
      <p style={{ margin: '4px 0 0', fontSize: 11, color: '#393939', fontFamily: "'IBM Plex Mono', monospace" }}>
        SCHEDULED — DAY 4
      </p>
    </div>
  </div>
);

// ─── Section wrapper ──────────────────────────────────────────────────────────

const Section: React.FC<{ title: string; badge?: string | number; children: React.ReactNode }> = ({ title, badge, children }) => (
  <div style={{ border: '1px solid #262626' }}>
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '8px 16px',
      borderBottom: '1px solid #262626',
      background: '#161616',
    }}>
      <span style={{ fontSize: 11, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
        {title}
      </span>
      {badge !== undefined && (
        <span style={{
          marginLeft: 'auto',
          fontSize: 10, color: '#525252',
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {badge}
        </span>
      )}
    </div>
    <div style={{ background: '#1c1c1c' }}>
      {children}
    </div>
  </div>
);

// ─── Main Page ────────────────────────────────────────────────────────────────

const EntityProfilePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [entity, setEntity] = useState<Entity | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aliasFilter, setAliasFilter] = useState<string>('all');

  useEffect(() => {
    setIsLoading(true);
    // Replace with: client.get<Entity>(`/entities/${id}`)
    setTimeout(() => {
      setEntity(MOCK_ENTITY);
      setIsLoading(false);
    }, 600);
  }, [id]);

  if (isLoading) return (
    <div style={{ padding: 48, fontFamily: "'IBM Plex Mono', monospace", color: '#525252', fontSize: 12, letterSpacing: 1 }}>
      LOADING ENTITY…
    </div>
  );
  if (error) return (
    <div style={{ padding: 48, fontFamily: "'IBM Plex Mono', monospace", color: '#fa4d56', fontSize: 12 }}>
      {error}
    </div>
  );
  if (!entity) return null;

  const scoreColor = riskColor(entity.risk_score);
  const uniqueAliasTypes = ['all', ...Array.from(new Set(entity.aliases?.map(a => a.type) ?? []))];
  const filteredAliases = aliasFilter === 'all'
    ? (entity.aliases ?? [])
    : (entity.aliases ?? []).filter(a => a.type === aliasFilter);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #161616; }
        ::-webkit-scrollbar-thumb { background: #393939; }
        .carbon-tag-btn:hover { background: #393939 !important; }
        .meta-card:hover { border-color: #525252 !important; }
      `}</style>

      <div style={{
        background: '#161616',
        minHeight: '100vh',
        color: '#f4f4f4',
        fontFamily: "'IBM Plex Sans', sans-serif",
        padding: '24px 32px',
        maxWidth: 960,
      }}>

        {/* ── Breadcrumb ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          marginBottom: 20,
          fontSize: 11, color: '#525252',
          fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.8,
        }}>
          <span style={{ color: '#78a9ff', cursor: 'pointer' }}>ENTITIES</span>
          <span>/</span>
          <span>{entity.id}</span>
        </div>

        {/* ────────────────────────────────────────────────────────────────── */}
        {/* PANEL 1 · ENTITY HEADER                                           */}
        {/* ────────────────────────────────────────────────────────────────── */}
        <Section title="ENTITY PROFILE">
          <div style={{ padding: '20px 20px 24px' }}>
            <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' }}>

              {/* Gauge */}
              <RiskGauge score={entity.risk_score} />

              {/* Core identity */}
              <div style={{ flex: 1, minWidth: 220 }}>
                {/* Type chip */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: 18, color: scoreColor,
                    lineHeight: 1,
                  }}>
                    {ENTITY_TYPE_ICON[entity.type]}
                  </span>
                  <span style={{
                    fontSize: 10, letterSpacing: 1.5,
                    fontFamily: "'IBM Plex Mono', monospace",
                    color: '#6f6f6f',
                    textTransform: 'uppercase',
                  }}>
                    {entity.type}
                  </span>
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: 10, letterSpacing: 1,
                    fontFamily: "'IBM Plex Mono', monospace",
                    color: '#525252',
                  }}>
                    ID: {entity.id}
                  </span>
                </div>

                {/* Name */}
                <h1 style={{
                  margin: '0 0 4px',
                  fontSize: 22, fontWeight: 600,
                  color: '#f4f4f4',
                  fontFamily: "'IBM Plex Sans', sans-serif",
                  letterSpacing: -0.3,
                }}>
                  {entity.name}
                </h1>

                {/* Risk badge */}
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <span style={{
                    fontSize: 11, padding: '2px 8px',
                    background: `${scoreColor}1a`,
                    color: scoreColor,
                    border: `1px solid ${scoreColor}44`,
                    fontFamily: "'IBM Plex Mono', monospace",
                    letterSpacing: 1,
                  }}>
                    RISK · {riskLabel(entity.risk_score)}
                  </span>
                  <span style={{ fontSize: 11, color: '#6f6f6f', fontFamily: "'IBM Plex Mono', monospace" }}>
                    {entity.risk_score} / 100
                  </span>
                </div>

                {entity.description && (
                  <p style={{ margin: '0 0 12px', fontSize: 13, color: '#a8a8a8', lineHeight: 1.6, maxWidth: 520 }}>
                    {entity.description}
                  </p>
                )}

                {/* Tags */}
                {entity.tags && entity.tags.length > 0 && (
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {entity.tags.map(tag => (
                      <span key={tag} style={{
                        fontSize: 10, padding: '2px 8px',
                        background: '#262626', color: '#a8a8a8',
                        border: '1px solid #393939',
                        fontFamily: "'IBM Plex Mono', monospace",
                        letterSpacing: 0.5,
                      }}>
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Meta stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, marginTop: 20, border: '1px solid #262626' }}>
              {[
                { label: 'FIRST SEEN',       value: fmt(entity.first_seen) },
                { label: 'LAST SEEN',         value: fmt(entity.last_seen) },
                { label: 'ALIASES',           value: entity.aliases?.length ?? 0 },
                { label: 'LINKED ENTITIES',   value: entity.linked_entities?.length ?? 0 },
              ].map(({ label, value }, i) => (
                <div key={label} className="meta-card" style={{
                  padding: '12px 16px',
                  background: '#1c1c1c',
                  borderRight: i < 3 ? '1px solid #262626' : 'none',
                  transition: 'border-color 0.15s',
                }}>
                  <p style={{ margin: '0 0 4px', fontSize: 9, color: '#525252', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1.5 }}>
                    {label}
                  </p>
                  <p style={{ margin: 0, fontSize: 16, color: '#f4f4f4', fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Section>

        <div style={{ height: 16 }} />

        {/* ────────────────────────────────────────────────────────────────── */}
        {/* PANEL 2 · ALIASES                                                 */}
        {/* ────────────────────────────────────────────────────────────────── */}
        <Section title="ALIASES & LINKED IDENTIFIERS" badge={`${entity.aliases?.length ?? 0} RECORDS`}>
          {/* filter strip */}
          <div style={{
            display: 'flex', gap: 0,
            borderBottom: '1px solid #262626',
            overflowX: 'auto',
          }}>
            {uniqueAliasTypes.map(t => (
              <button
                key={t}
                className="carbon-tag-btn"
                onClick={() => setAliasFilter(t)}
                style={{
                  padding: '7px 14px',
                  fontSize: 10, letterSpacing: 1,
                  fontFamily: "'IBM Plex Mono', monospace",
                  border: 'none',
                  borderRight: '1px solid #262626',
                  background: aliasFilter === t ? '#393939' : 'transparent',
                  color: aliasFilter === t ? '#f4f4f4' : '#6f6f6f',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'background 0.15s',
                  textTransform: 'uppercase',
                }}
              >
                {t === 'all' ? 'ALL' : ALIAS_TYPE_META[t as Alias['type']]?.label ?? t}
              </button>
            ))}
          </div>
          {/* rows */}
          <div>
            {filteredAliases.length ? (
              filteredAliases.map(a => <AliasRow key={a.id} alias={a} />)
            ) : (
              <p style={{ margin: 0, padding: '16px', fontSize: 12, color: '#525252', fontFamily: "'IBM Plex Mono', monospace" }}>
                NO ALIASES FOUND
              </p>
            )}
          </div>
        </Section>

        <div style={{ height: 16 }} />

        {/* ────────────────────────────────────────────────────────────────── */}
        {/* PANEL 3 · GRAPH PLACEHOLDER                                       */}
        {/* ────────────────────────────────────────────────────────────────── */}
        <Section title="RELATIONSHIP GRAPH">
          <GraphPlaceholder />
        </Section>

        <div style={{ height: 16 }} />

        {/* ────────────────────────────────────────────────────────────────── */}
        {/* PANEL 4 · SOURCE TIMELINE                                         */}
        {/* ────────────────────────────────────────────────────────────────── */}
        <Section title="SOURCE TIMELINE" badge={`${entity.timeline?.length ?? 0} EVENTS`}>
          <div style={{ padding: '20px 16px 8px' }}>
            {entity.timeline && entity.timeline.length > 0 ? (
              [...entity.timeline]
                .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
                .map((ev, idx, arr) => (
                  <TimelineRow key={ev.id} event={ev} last={idx === arr.length - 1} />
                ))
            ) : (
              <p style={{ margin: 0, fontSize: 12, color: '#525252', fontFamily: "'IBM Plex Mono', monospace" }}>
                NO TIMELINE EVENTS
              </p>
            )}
          </div>
        </Section>

        <div style={{ height: 40 }} />
      </div>
    </>
  );
};

export default EntityProfilePage;