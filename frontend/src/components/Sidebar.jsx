import { useState, useEffect } from 'react';

/* ── Nav Groups (updated as per requirement) ── */
const NAV_GROUPS = [
  {
    items: [
      { id: 'geo',       label: 'Geo Intel',   icon: GlobeIcon },
      { id: 'dashboard', label: 'Dashboard',   icon: DashIcon },
    ],
  },
  {
    label: 'BEL Capability Modules',
    items: [
      { id: 'ephemeral',  label: 'Ephemeral Capture',   icon: CaptureIcon },
      { id: 'narr',       label: 'Coordinated Narr',    icon: NetworkIcon },
      { id: 'investigation', label: 'Investigation',    icon: SearchIcon },
      { id: 'nlp',        label: 'Multilingual NLP',    icon: NLPIcon },
      { id: 'idscan',     label: 'ID Scan',             icon: IDScanIcon },
      { id: 'credibility',label: 'Credibility',         icon: ShieldIcon },
      { id: 'resilience', label: 'Resilience',          icon: ResilienceIcon },
    ],
  },
  {
    label: 'Platform',
    items: [
      { id: 'search',   label: 'Search',      icon: SearchSmIcon },
      { id: 'sources',  label: 'Sources',     icon: SourceIcon },
      { id: 'keywords', label: 'Keywords',    icon: TagIcon,   badge: 6,  badgeType: 'info' },
      { id: 'entities', label: 'Entity Graph',icon: GraphIcon },
      { id: 'alerts',   label: 'Alerts',      icon: BellIcon,  badge: 43, badgeType: 'danger'},
      { id: 'reports',  label: 'Reports',     icon: ReportIcon },
      { id: 'settings', label: 'Settings',    icon: SettingsIcon },
    ],
  },
];

export default function Sidebar({ activePage = 'alerts', onNavigate }) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  });

  const handleNav = (id) => onNavigate?.(id);

  return (
    <aside style={css.sidebar}>
      {/* Ambient glow */}
      <div style={css.ambientGlow} />

      {/* Brand */}
      <div style={css.brand}>
        <div style={css.brandHex}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <polygon
              points="10,1.5 18,6 18,14 10,18.5 2,14 2,6"
              stroke="#00C2FF" strokeWidth="1.1"
              fill="rgba(0,194,255,0.07)"
            />
            <text x="10" y="12.5" textAnchor="middle"
              fontFamily="Syne,sans-serif" fontSize="5" fontWeight="700" fill="#00C2FF">
              ILA
            </text>
          </svg>
        </div>
        <div>
          <div style={css.brandName}>ILA</div>
          <div style={css.brandVer}>OSINT PLATFORM · v1.0</div>
        </div>
      </div>

      {/* Status row */}
      <div style={css.statusRow}>
        <span style={css.liveDot} />
        <span>SYSTEM LIVE</span>
        <span style={{ marginLeft: 'auto', color: 'rgba(0,194,255,0.4)' }}>{timeStr}</span>
      </div>

      {/* Nav */}
      <nav style={css.nav}>
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi} style={{ marginBottom: 2 }}>
            {group.label && (
              <div style={css.groupLabel}>{group.label}</div>
            )}
            {group.items.map(item => (
              <NavItem
                key={item.id}
                item={item}
                active={activePage === item.id}
                onClick={() => handleNav(item.id)}
              />
            ))}
            {gi < NAV_GROUPS.length - 1 && <div style={css.sep} />}
          </div>
        ))}
      </nav>

      {/* Footer / user */}
      <div style={css.footer}>
        <div style={css.avatar}>AD</div>
        <div>
          <div style={css.userName}>Administrator</div>
          <div style={css.userRole}>ADMIN</div>
        </div>
        <button
          style={css.logoutBtn}
          title="Logout"
          onClick={() => handleNav('__logout__')}
        >
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none"
            stroke="currentColor" strokeWidth="1.4">
            <path d="M9 7H2M5 4.5 2 7l3 2.5" />
            <path d="M7 2h3a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H7" />
          </svg>
        </button>
      </div>
    </aside>
  );
}

/* ── NavItem ── */
function NavItem({ item, active, onClick }) {
  const [hovered, setHovered] = useState(false);
  const Icon = item.icon;

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: '100%',
        display: 'flex', alignItems: 'center', gap: 9,
        padding: '7px 10px',
        borderRadius: 6,
        border: 'none',
        borderLeft: `2px solid ${active ? '#00C2FF' : 'transparent'}`,
        background: active
          ? 'rgba(0,194,255,0.1)'
          : hovered
            ? 'rgba(0,194,255,0.05)'
            : 'transparent',
        cursor: 'pointer', textAlign: 'left',
        transition: 'all 0.15s',
        marginBottom: 1,
        boxShadow: active ? 'inset 0 0 12px rgba(0,194,255,0.05)' : 'none',
      }}
    >
      <span style={{
        width: 16, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: active ? '#00C2FF' : hovered ? '#B8C7D9' : '#4A5E72',
        flexShrink: 0, transition: 'color 0.15s',
      }}>
        <Icon />
      </span>
      <span style={{
        fontSize: 12, fontWeight: active ? 500 : 400,
        fontFamily: 'Inter, sans-serif',
        color: active ? '#00E5FF' : hovered ? '#B8C7D9' : '#7F8FA4',
        flex: 1, letterSpacing: '0.02em',
        transition: 'color 0.15s',
      }}>
        {item.label}
      </span>
      {item.badge != null && (
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9, padding: '1px 5px', borderRadius: 3, fontWeight: 600,
          background: item.badgeType === 'danger'
            ? 'rgba(255,82,82,0.15)' : 'rgba(0,194,255,0.1)',
          color: item.badgeType === 'danger' ? '#FF5252' : '#00C2FF',
          border: `1px solid ${item.badgeType === 'danger'
            ? 'rgba(255,82,82,0.25)' : 'rgba(0,194,255,0.2)'}`,
        }}>
          {item.badge}
        </span>
      )}
    </button>
  );
}

/* ── Icons ── */
const ip = { width: 14, height: 14, viewBox: '0 0 14 14', fill: 'none', stroke: 'currentColor', strokeWidth: 1.3 };

function DashIcon()      { return <svg {...ip}><rect x="1" y="1" width="5" height="5" rx="1"/><rect x="8" y="1" width="5" height="5" rx="1"/><rect x="1" y="8" width="5" height="5" rx="1"/><rect x="8" y="8" width="5" height="5" rx="1"/></svg>; }
function GlobeIcon()     { return <svg {...ip}><circle cx="7" cy="7" r="5.5"/><path d="M7 1.5 Q9.5 7 7 12.5 Q4.5 7 7 1.5"/><path d="M1.5 7h11"/></svg>; }
function CaptureIcon()   { return <svg {...ip}><circle cx="7" cy="7" r="5.5"/><path d="M7 4v3.5l2 1.5"/></svg>; }
function NetworkIcon()   { return <svg {...ip}><circle cx="3" cy="7" r="1.5"/><circle cx="7" cy="3.5" r="1.5"/><circle cx="11" cy="7" r="1.5"/><circle cx="7" cy="10.5" r="1.5"/><path d="M4.5 7h1M8.5 7h1M7 5v1.5M7 8.5v1"/></svg>; }
function BellIcon()      { return <svg {...ip}><path d="M7 1.5a4 4 0 0 1 4 4v2.5l1 2H2l1-2V5.5a4 4 0 0 1 4-4z"/><path d="M5.5 10.5a1.5 1.5 0 0 0 3 0"/></svg>; }
function SourceIcon()    { return <svg {...ip}><rect x="2" y="2" width="10" height="10" rx="1"/><path d="M5 5h4M5 7.5h3M5 10h2"/></svg>; }
function TagIcon()       { return <svg {...ip}><path d="M2 2h4.5l5 5L8 10.5l-5-5V2z"/><circle cx="4.5" cy="4.5" r="0.8" fill="currentColor"/></svg>; }
function SearchIcon()    { return <svg {...ip}><circle cx="6" cy="6" r="3.5"/><path d="M8.5 8.5l3 3"/></svg>; }
function SearchSmIcon()  { return <svg {...ip}><circle cx="6" cy="6" r="3.5"/><path d="M8.5 8.5l3 3"/></svg>; }
function GraphIcon()     { return <svg {...ip}><circle cx="7" cy="7" r="1.5"/><circle cx="2.5" cy="3" r="1.2"/><circle cx="11.5" cy="3" r="1.2"/><circle cx="2.5" cy="11" r="1.2"/><path d="M3.7 3.8 5.5 5.5M10.3 3.8 8.5 5.5M3.7 10.2 5.5 8.5"/></svg>; }
function NLPIcon()       { return <svg {...ip}><rect x="2" y="4" width="10" height="6" rx="1"/><path d="M5 4V3M9 4V3M4 7h2M8 7h2"/></svg>; }
function ShieldIcon()    { return <svg {...ip}><path d="M7 1.5 L12 3.5 V7.5 C12 10 9.5 12 7 12.5 C4.5 12 2 10 2 7.5 V3.5 Z"/></svg>; }
function ReportIcon()    { return <svg {...ip}><rect x="3" y="1.5" width="8" height="11" rx="1"/><path d="M5 5h4M5 7.5h4M5 10h2"/></svg>; }
function SettingsIcon()  { return <svg {...ip}><circle cx="7" cy="7" r="2"/><path d="M7 1.5v1.2M7 11.3v1.2M1.5 7h1.2M11.3 7h1.2M3.3 3.3l.85.85M9.85 9.85l.85.85M3.3 10.7l.85-.85M9.85 4.15l.85-.85"/></svg>; }
function IDScanIcon()    { return <svg {...ip}><rect x="2" y="3" width="10" height="8" rx="1"/><path d="M5 6h1M8 6h1M5 8.5h4"/><path d="M4 3V2M10 3V2M4 11v1M10 11v1"/></svg>; }
function ResilienceIcon(){ return <svg {...ip}><path d="M7 2 L12 5 V9 C12 11.2 9.8 12.8 7 13 C4.2 12.8 2 11.2 2 9 V5 Z"/><path d="M5 7.5l1.5 1.5 3-3" strokeLinecap="round" strokeLinejoin="round"/></svg>; }

/* ── Styles ── */
const css = {
  sidebar: {
    width: 224, minWidth: 224,
    background: '#060F1C',
    borderRight: '1px solid rgba(0,194,255,0.12)',
    display: 'flex', flexDirection: 'column',
    height: '100vh', position: 'relative', overflow: 'hidden',
  },
  ambientGlow: {
    position: 'absolute', top: 0, left: 0, right: 0, height: 200, zIndex: 0,
    background: 'radial-gradient(ellipse at 50% -30%, rgba(0,194,255,0.08) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  brand: {
    padding: '16px 16px 13px',
    borderBottom: '1px solid rgba(0,180,255,0.07)',
    display: 'flex', alignItems: 'center', gap: 10,
    flexShrink: 0, position: 'relative', zIndex: 1,
  },
  brandHex: {
    width: 34, height: 34,
    border: '1px solid rgba(0,194,255,0.22)',
    borderRadius: 7,
    background: 'rgba(0,194,255,0.07)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 0 10px rgba(0,194,255,0.12)',
    flexShrink: 0,
  },
  brandName: {
    fontFamily: 'Syne, sans-serif',
    fontSize: 15, fontWeight: 700,
    letterSpacing: '0.1em', color: '#E6F1FF', lineHeight: 1,
  },
  brandVer: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 8, color: '#3A4E62', letterSpacing: '0.1em', marginTop: 2,
  },
  statusRow: {
    padding: '7px 16px',
    borderBottom: '1px solid rgba(0,180,255,0.06)',
    display: 'flex', alignItems: 'center', gap: 7,
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 9, color: '#3A4E62', letterSpacing: '0.1em',
    flexShrink: 0,
  },
  liveDot: {
    display: 'inline-block', width: 5, height: 5, borderRadius: '50%',
    background: '#00E676', boxShadow: '0 0 5px #00E676', flexShrink: 0,
  },
  nav: {
    flex: 1, padding: '10px 8px', overflowY: 'auto',
    position: 'relative', zIndex: 1,
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(0,194,255,0.1) transparent',
  },
  groupLabel: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 8.5, letterSpacing: '0.16em',
    color: '#2E3E50', padding: '6px 8px 3px',
    textTransform: 'uppercase',
  },
  sep: {
    height: 1,
    background: 'rgba(0,180,255,0.06)',
    margin: '6px 8px 8px',
  },
  footer: {
    borderTop: '1px solid rgba(0,180,255,0.07)',
    padding: '11px 14px',
    display: 'flex', alignItems: 'center', gap: 10,
    flexShrink: 0,
  },
  avatar: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'linear-gradient(135deg, #0049a8, #0093d0)',
    border: '1px solid rgba(0,194,255,0.22)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 9, fontWeight: 700, color: '#E6F1FF', flexShrink: 0,
    fontFamily: 'Syne, sans-serif',
  },
  userName: { fontSize: 11, fontWeight: 600, color: '#B8C7D9' },
  userRole: {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 7.5, color: '#3A4E62', letterSpacing: '0.1em',
  },
  logoutBtn: {
    marginLeft: 'auto',
    background: 'transparent', border: 'none',
    color: '#3A4E62', cursor: 'pointer',
    padding: 5, borderRadius: 5,
    transition: 'color 0.15s, background 0.15s',
    display: 'flex', alignItems: 'center',
  },
};