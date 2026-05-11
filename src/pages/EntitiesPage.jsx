import { useState, useMemo } from 'react';

// ─── Mock Entity Data (derived from existing MOCK_ALERTS + extras) ───────────
const MOCK_ENTITIES = [
  {
    id: 'ENT-001',
    name: 'Arjun Mehra',
    type: 'Person',
    riskScore: 92,
    lastSeen: new Date(Date.now() - 3 * 60000).toISOString(),
    aliases: ['@arjun_m99', 'arjun.mehra@protonmail.com'],
    flags: ['velocity_anomaly', 'pattern_match'],
    status: 'active',
  },
  {
    id: 'ENT-002',
    name: 'SIM Cluster #7 — Rajasthan',
    type: 'Organization',
    riskScore: 87,
    lastSeen: new Date(Date.now() - 18 * 60000).toISOString(),
    aliases: ['SIM_swap_cluster_RJ'],
    flags: ['sim_cluster', 'anomaly_detection'],
    status: 'active',
  },
  {
    id: 'ENT-003',
    name: 'Priya Shankar',
    type: 'Person',
    riskScore: 74,
    lastSeen: new Date(Date.now() - 45 * 60000).toISOString(),
    aliases: ['+91-8867543210', '@priya_sh88'],
    flags: ['coordinated_behavior'],
    status: 'active',
  },
  {
    id: 'ENT-004',
    name: 'hawala_network_UP',
    type: 'Threat Actor',
    riskScore: 68,
    lastSeen: new Date(Date.now() - 2.1 * 3600000).toISOString(),
    aliases: ['@hw_nets_up', 'hwala_nets_up@protonmail.com'],
    flags: ['keyword_match', 'hawala'],
    status: 'monitoring',
  },
  {
    id: 'ENT-005',
    name: 'Deepak Rao',
    type: 'Person',
    riskScore: 59,
    lastSeen: new Date(Date.now() - 5.4 * 3600000).toISOString(),
    aliases: ['deepak.rao@outlook.com', '@dr_finance_in'],
    flags: ['phishing', 'domain_cluster'],
    status: 'confirmed',
  },
  {
    id: 'ENT-006',
    name: 'Crypto-UPI Bridge Node #3',
    type: 'Crypto',
    riskScore: 81,
    lastSeen: new Date(Date.now() - 7 * 3600000).toISOString(),
    aliases: ['cryptonode3@upi', '@crypt0_bridge_IN'],
    flags: ['crypto_layering', 'velocity_anomaly'],
    status: 'active',
  },
  {
    id: 'ENT-007',
    name: 'Mumbai Phishing Ring',
    type: 'Organization',
    riskScore: 45,
    lastSeen: new Date(Date.now() - 12 * 3600000).toISOString(),
    aliases: ['mum_phi_ring', 'mpr_ops@protonmail.com'],
    flags: ['phishing'],
    status: 'monitoring',
  },
  {
    id: 'ENT-008',
    name: 'Suresh Patel',
    type: 'Person',
    riskScore: 28,
    lastSeen: new Date(Date.now() - 24 * 3600000).toISOString(),
    aliases: ['+91-9900112233'],
    flags: [],
    status: 'cleared',
  },
  {
    id: 'ENT-009',
    name: 'Delhi NCR Drop Zone',
    type: 'Location',
    riskScore: 76,
    lastSeen: new Date(Date.now() - 1.2 * 3600000).toISOString(),
    aliases: ['DL-Drop-7', 'Connaught Place cluster'],
    flags: ['network_centrality'],
    status: 'active',
  },
  {
    id: 'ENT-010',
    name: 'BTC Mixer Node #9',
    type: 'Crypto',
    riskScore: 95,
    lastSeen: new Date(Date.now() - 8 * 60000).toISOString(),
    aliases: ['bc1q9xmixer...', 'mix_node_9'],
    flags: ['crypto_layering', 'anomaly_detection'],
    status: 'active',
  },
];

// ─── Config ───────────────────────────────────────────────────────────────────
const ENTITY_TYPES = ['All', 'Person', 'Organization', 'Location', 'Threat Actor', 'Crypto'];

const TYPE_CONFIG = {
  Person:        { icon: '◉', color: '#60A5FA', bg: 'rgba(96,165,250,0.1)'  },
  Organization:  { icon: '⬡', color: '#A78BFA', bg: 'rgba(167,139,250,0.1)' },
  Location:      { icon: '⬨', color: '#34D399', bg: 'rgba(52,211,153,0.1)'  },
  'Threat Actor':{ icon: '⚠', color: '#F87171', bg: 'rgba(248,113,113,0.1)' },
  Crypto:        { icon: '◈', color: '#FBBF24', bg: 'rgba(251,191,36,0.1)'  },
};

const STATUS_CONFIG = {
  active:     { label: 'ACTIVE',     color: '#EF4444' },
  monitoring: { label: 'MONITORING', color: '#FBBF24' },
  confirmed:  { label: 'CONFIRMED',  color: '#F97316' },
  cleared:    { label: 'CLEARED',    color: '#10B981' },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getRiskConfig(score) {
  if (score >= 71) return { label: 'HIGH',   color: '#EF4444', glow: 'rgba(239,68,68,0.3)',   bar: '#EF4444' };
  if (score >= 31) return { label: 'MED',    color: '#FBBF24', glow: 'rgba(251,191,36,0.25)',  bar: '#FBBF24' };
  return              { label: 'LOW',    color: '#10B981', glow: 'rgba(16,185,129,0.25)',  bar: '#10B981' };
}

function formatLastSeen(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  const hrs  = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 60)  return `${mins}m ago`;
  if (hrs  < 24)  return `${hrs}h ago`;
  return `${days}d ago`;
}

// ─── EntityCard ───────────────────────────────────────────────────────────────
function EntityCard({ entity, onClick, selected }) {
  const risk   = getRiskConfig(entity.riskScore);
  const type   = TYPE_CONFIG[entity.type] || TYPE_CONFIG.Person;
  const status = STATUS_CONFIG[entity.status] || STATUS_CONFIG.monitoring;

  return (
    <div
      onClick={() => onClick(entity)}
      style={{
        background: selected ? 'rgba(245,158,11,0.06)' : '#0D0F14',
        border: `1px solid ${selected ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.07)'}`,
        borderRadius: '10px',
        padding: '18px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.border = `1px solid ${risk.glow.replace('0.3','0.6').replace('0.25','0.5')}`;
        e.currentTarget.style.boxShadow = `0 0 18px ${risk.glow}, 0 4px 24px rgba(0,0,0,0.4)`;
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.border = `1px solid ${selected ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.07)'}`;
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Scan line decoration */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '1px',
        background: `linear-gradient(90deg, transparent, ${risk.color}44, transparent)`,
      }} />

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        {/* Type badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '5px',
          background: type.bg, border: `1px solid ${type.color}33`,
          borderRadius: '5px', padding: '3px 8px',
        }}>
          <span style={{ fontSize: '11px', color: type.color }}>{type.icon}</span>
          <span style={{ fontSize: '10px', color: type.color, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em' }}>
            {entity.type.toUpperCase()}
          </span>
        </div>

        {/* Status pill */}
        <div style={{
          fontSize: '9px', fontFamily: 'JetBrains Mono, monospace',
          color: status.color, letterSpacing: '0.1em',
        }}>
          <span style={{ marginRight: '4px', fontSize: '7px' }}>●</span>{status.label}
        </div>
      </div>

      {/* Entity name */}
      <div style={{
        fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '14px',
        color: '#E2E8F0', marginBottom: '4px', letterSpacing: '0.01em',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {entity.name}
      </div>

      {/* ID */}
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: '10px',
        color: '#374151', marginBottom: '14px',
      }}>
        {entity.id}
      </div>

      {/* Risk score */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
          <span style={{ fontSize: '10px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em' }}>
            RISK SCORE
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '16px', fontFamily: 'JetBrains Mono, monospace', fontWeight: '700', color: risk.color }}>
              {entity.riskScore}
            </span>
            <span style={{
              fontSize: '9px', fontFamily: 'JetBrains Mono, monospace',
              color: risk.color, background: `${risk.color}18`,
              border: `1px solid ${risk.color}33`, borderRadius: '3px', padding: '1px 5px',
            }}>
              {risk.label}
            </span>
          </div>
        </div>
        {/* Risk bar */}
        <div style={{ height: '3px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${entity.riskScore}%`,
            background: `linear-gradient(90deg, ${risk.bar}88, ${risk.bar})`,
            borderRadius: '2px',
            boxShadow: `0 0 6px ${risk.glow}`,
            transition: 'width 0.6s ease',
          }} />
        </div>
      </div>

      {/* Flags */}
      {entity.flags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '12px' }}>
          {entity.flags.slice(0, 2).map(flag => (
            <span key={flag} style={{
              fontSize: '9px', fontFamily: 'JetBrains Mono, monospace',
              color: '#6B7280', background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '3px', padding: '2px 6px',
              letterSpacing: '0.04em',
            }}>
              {flag.replace(/_/g, ' ')}
            </span>
          ))}
          {entity.flags.length > 2 && (
            <span style={{
              fontSize: '9px', fontFamily: 'JetBrains Mono, monospace',
              color: '#4B5563', padding: '2px 4px',
            }}>
              +{entity.flags.length - 2}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.05)',
      }}>
        <span style={{ fontSize: '10px', color: '#374151', fontFamily: 'JetBrains Mono, monospace' }}>
          LAST SEEN
        </span>
        <span style={{ fontSize: '10px', color: '#6B7280', fontFamily: 'JetBrains Mono, monospace' }}>
          {formatLastSeen(entity.lastSeen)}
        </span>
      </div>
    </div>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────
function EntityDetail({ entity, onClose }) {
  const risk   = getRiskConfig(entity.riskScore);
  const type   = TYPE_CONFIG[entity.type] || TYPE_CONFIG.Person;
  const status = STATUS_CONFIG[entity.status] || STATUS_CONFIG.monitoring;

  return (
    <div style={{
      width: '300px', minWidth: '300px',
      background: '#0A0C10',
      borderLeft: '1px solid rgba(255,255,255,0.06)',
      display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em' }}>
          ENTITY DETAIL
        </span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: '#4B5563', cursor: 'pointer', fontSize: '16px', lineHeight: 1 }}
        >✕</button>
      </div>

      <div style={{ padding: '20px', flex: 1 }}>
        {/* Type + Status */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            background: type.bg, border: `1px solid ${type.color}33`,
            borderRadius: '5px', padding: '3px 8px',
          }}>
            <span style={{ fontSize: '11px', color: type.color }}>{type.icon}</span>
            <span style={{ fontSize: '10px', color: type.color, fontFamily: 'JetBrains Mono, monospace' }}>
              {entity.type.toUpperCase()}
            </span>
          </div>
          <div style={{
            fontSize: '9px', fontFamily: 'JetBrains Mono, monospace',
            color: status.color, alignSelf: 'center',
          }}>
            ● {status.label}
          </div>
        </div>

        {/* Name */}
        <div style={{
          fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '18px',
          color: '#F1F5F9', marginBottom: '4px', lineHeight: 1.2,
        }}>
          {entity.name}
        </div>
        <div style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: '11px',
          color: '#374151', marginBottom: '24px',
        }}>
          {entity.id}
        </div>

        {/* Risk gauge */}
        <div style={{
          background: '#0D0F14', border: `1px solid ${risk.color}22`,
          borderRadius: '8px', padding: '16px', marginBottom: '20px',
          boxShadow: `0 0 20px ${risk.glow}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace' }}>RISK SCORE</span>
            <span style={{ fontSize: '11px', color: risk.color, fontFamily: 'JetBrains Mono, monospace' }}>{risk.label}</span>
          </div>
          <div style={{ fontSize: '36px', fontFamily: 'JetBrains Mono, monospace', fontWeight: '700', color: risk.color, marginBottom: '10px' }}>
            {entity.riskScore}<span style={{ fontSize: '14px', color: '#4B5563' }}>/100</span>
          </div>
          <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px' }}>
            <div style={{
              height: '100%', width: `${entity.riskScore}%`,
              background: `linear-gradient(90deg, ${risk.bar}88, ${risk.bar})`,
              borderRadius: '2px', boxShadow: `0 0 8px ${risk.glow}`,
            }} />
          </div>
        </div>

        {/* Aliases */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em', marginBottom: '8px' }}>
            ALIASES / IDENTIFIERS
          </div>
          {entity.aliases.map((a, i) => (
            <div key={i} style={{
              fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color: '#6B7280',
              padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
              <span style={{ color: '#2E3340' }}>▸</span> {a}
            </div>
          ))}
        </div>

        {/* Flags */}
        {entity.flags.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '11px', color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em', marginBottom: '8px' }}>
              FLAGS
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {entity.flags.map(flag => (
                <span key={flag} style={{
                  fontSize: '10px', fontFamily: 'JetBrains Mono, monospace',
                  color: '#EF4444', background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  borderRadius: '4px', padding: '3px 8px',
                }}>
                  {flag.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div style={{ fontSize: '11px', color: '#374151', fontFamily: 'JetBrains Mono, monospace' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <span style={{ color: '#4B5563' }}>LAST SEEN</span>
            <span>{formatLastSeen(entity.lastSeen)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <span style={{ color: '#4B5563' }}>EXACT TIME</span>
            <span>{new Date(entity.lastSeen).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Entities Page ───────────────────────────────────────────────────────
export default function EntitiesPage() {
  const [search, setSearch]         = useState('');
  const [typeFilter, setTypeFilter] = useState('All');
  const [sortBy, setSortBy]         = useState('risk');
  const [selected, setSelected]     = useState(null);

  const filtered = useMemo(() => {
    let list = MOCK_ENTITIES.filter(e => {
      const matchSearch = e.name.toLowerCase().includes(search.toLowerCase())
        || e.id.toLowerCase().includes(search.toLowerCase())
        || e.aliases.some(a => a.toLowerCase().includes(search.toLowerCase()));
      const matchType = typeFilter === 'All' || e.type === typeFilter;
      return matchSearch && matchType;
    });

    if (sortBy === 'risk')     list = [...list].sort((a, b) => b.riskScore - a.riskScore);
    if (sortBy === 'recent')   list = [...list].sort((a, b) => new Date(b.lastSeen) - new Date(a.lastSeen));
    if (sortBy === 'name')     list = [...list].sort((a, b) => a.name.localeCompare(b.name));

    return list;
  }, [search, typeFilter, sortBy]);

  const stats = useMemo(() => ({
    total: MOCK_ENTITIES.length,
    high:  MOCK_ENTITIES.filter(e => e.riskScore >= 71).length,
    med:   MOCK_ENTITIES.filter(e => e.riskScore >= 31 && e.riskScore < 71).length,
    low:   MOCK_ENTITIES.filter(e => e.riskScore < 31).length,
  }), []);

  return (
    <div style={{
      display: 'flex', height: '100%', overflow: 'hidden',
      background: '#07080A', position: 'relative',
    }}>
      {/* Grid overlay */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
        zIndex: 0,
      }} />

      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative', zIndex: 1 }}>

        {/* Top bar */}
        <div style={{
          padding: '20px 24px 0',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}>
          {/* Title row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: '#F59E0B', fontSize: '16px' }}>◈</span>
                <span style={{ fontFamily: 'Syne, sans-serif', fontWeight: '700', fontSize: '18px', color: '#F1F5F9', letterSpacing: '0.03em' }}>
                  ENTITY REGISTRY
                </span>
                <span style={{
                  fontSize: '10px', fontFamily: 'JetBrains Mono, monospace',
                  color: '#4B5563', background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)', borderRadius: '4px',
                  padding: '2px 7px',
                }}>
                  {filtered.length} / {stats.total}
                </span>
              </div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#374151', marginTop: '2px', paddingLeft: '26px' }}>
                OSINT INTELLIGENCE LAYER — ENTITY MANAGEMENT
              </div>
            </div>

            {/* Stats strip */}
            <div style={{ display: 'flex', gap: '12px' }}>
              {[
                { label: 'HIGH', value: stats.high, color: '#EF4444' },
                { label: 'MED',  value: stats.med,  color: '#FBBF24' },
                { label: 'LOW',  value: stats.low,  color: '#10B981' },
              ].map(s => (
                <div key={s.label} style={{
                  background: `${s.color}10`, border: `1px solid ${s.color}25`,
                  borderRadius: '6px', padding: '6px 12px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: '16px', fontFamily: 'JetBrains Mono, monospace', fontWeight: '700', color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: '9px', fontFamily: 'JetBrains Mono, monospace', color: s.color, opacity: 0.7 }}>{s.label} RISK</div>
                </div>
              ))}
            </div>
          </div>

          {/* Controls row */}
          <div style={{ display: 'flex', gap: '10px', paddingBottom: '16px' }}>
            {/* Search */}
            <div style={{ flex: 1, position: 'relative' }}>
              <span style={{
                position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)',
                color: '#374151', fontSize: '13px', pointerEvents: 'none',
              }}>⌕</span>
              <input
                type="text"
                placeholder="Search by name, ID, alias..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  width: '100%', padding: '9px 12px 9px 32px',
                  background: '#0D0F14', border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '7px', color: '#D1D5DB',
                  fontFamily: 'JetBrains Mono, monospace', fontSize: '12px',
                  outline: 'none', boxSizing: 'border-box',
                }}
                onFocus={e => { e.target.style.border = '1px solid rgba(245,158,11,0.4)'; e.target.style.boxShadow = '0 0 10px rgba(245,158,11,0.1)'; }}
                onBlur={e =>  { e.target.style.border = '1px solid rgba(255,255,255,0.08)'; e.target.style.boxShadow = 'none'; }}
              />
            </div>

            {/* Type filter */}
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              style={{
                padding: '9px 12px', background: '#0D0F14',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '7px', color: '#9CA3AF',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '11px',
                outline: 'none', cursor: 'pointer', minWidth: '140px',
              }}
            >
              {ENTITY_TYPES.map(t => (
                <option key={t} value={t} style={{ background: '#0D0F14' }}>{t === 'All' ? 'ALL TYPES' : t.toUpperCase()}</option>
              ))}
            </select>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              style={{
                padding: '9px 12px', background: '#0D0F14',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '7px', color: '#9CA3AF',
                fontFamily: 'JetBrains Mono, monospace', fontSize: '11px',
                outline: 'none', cursor: 'pointer', minWidth: '120px',
              }}
            >
              <option value="risk"   style={{ background: '#0D0F14' }}>RISK ↓</option>
              <option value="recent" style={{ background: '#0D0F14' }}>RECENT ↓</option>
              <option value="name"   style={{ background: '#0D0F14' }}>NAME A–Z</option>
            </select>
          </div>
        </div>

        {/* Grid */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
          {filtered.length === 0 ? (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', height: '60%', gap: '10px',
            }}>
              <div style={{ fontSize: '28px', opacity: 0.15 }}>◈</div>
              <div style={{ fontFamily: 'Syne, sans-serif', fontWeight: '600', fontSize: '14px', color: '#374151' }}>
                NO ENTITIES FOUND
              </div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: '#2E3340' }}>
                ADJUST SEARCH OR FILTER
              </div>
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: '14px',
            }}>
              {filtered.map(entity => (
                <EntityCard
                  key={entity.id}
                  entity={entity}
                  selected={selected?.id === entity.id}
                  onClick={e => setSelected(selected?.id === e.id ? null : e)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <EntityDetail entity={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}