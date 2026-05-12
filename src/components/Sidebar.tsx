import React, { useState, useEffect, CSSProperties } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store";

/* ═══════════════════════════════════════════════════════════
   IBM Carbon Design System — Dark theme (Gray 100)
═══════════════════════════════════════════════════════════ */
const C = {
  gray100: "#161616", gray90: "#262626", gray80: "#393939",
  gray70: "#525252", gray60: "#6f6f6f", gray50: "#8d8d8d",
  gray40: "#a8a8a8", gray30: "#c6c6c6", gray20: "#e0e0e0",
  gray10: "#f4f4f4", white: "#ffffff",
  blue60: "#0f62fe", blue50: "#4589ff", blue40: "#78a9ff",
  cyan50: "#1192e8", cyan40: "#33b1ff", cyan30: "#82cfff",
  cyan20: "#bae6ff", cyan10: "#e5f6ff",
  teal40: "#3ddbd9", teal50: "#009d9a",
  red60: "#da1e28", red40: "#ff8389",
  green50: "#24a148", green40: "#42be65",
  yellow30: "#f1c21b", orange40: "#ff832b",
  purple40: "#be95ff", magenta40: "#ff7eb6",
  bg: "#0d1117", bgLayer: "#161b24",
  s02: "4px", s03: "8px", s04: "12px", s05: "16px",
  s06: "24px", s07: "32px", s08: "40px", s09: "48px",
};

/* ═══════════════════════════════════════════════════════════
   Route map — nav item id → React Router path
═══════════════════════════════════════════════════════════ */
const ROUTE_MAP: Record<string, string> = {
  dashboard:     "/",
  geo:           "/geo",
  ephemeral:     "/ephemeral",
  narr:          "/narr",
  investigation: "/investigations",
  nlp:           "/nlp",
  idscan:        "/idscan",
  credibility:   "/credibility",
  resilience:    "/resilience",
  search:        "/search",
  sources:       "/sources",
  keywords:      "/keywords",
  entities:      "/entities",
  alerts:        "/alerts",        // ← goes to AlertInbox page
  reports:       "/reports",
  settings:      "/settings",
};

/* Reverse map: path → nav id (for active highlighting) */
const PATH_TO_ID: Record<string, string> = Object.fromEntries(
  Object.entries(ROUTE_MAP).map(([id, path]) => [path, id])
);

/* ═══════════════════════════════════════════════════════════
   Types
═══════════════════════════════════════════════════════════ */
interface NavItem {
  id: string;
  label: string;
  icon: React.FC<{ color: string }>;
  badge?: string | number;
  badgeKind?: "danger" | "warning" | "info" | "success";
}

interface NavGroup {
  label?: string;
  items: NavItem[];
}

interface UserInfo {
  name: string;
  role: string;
  initials: string;
}

interface SidebarProps {
  user?: UserInfo;
}

/* ═══════════════════════════════════════════════════════════
   Navigation groups
═══════════════════════════════════════════════════════════ */
const NAV_GROUPS: NavGroup[] = [
  {
    items: [
      { id: "geo",       label: "Geo Intel",  icon: GlobeIcon },
      { id: "dashboard", label: "Dashboard",  icon: DashIcon  },
    ],
  },
  {
    label: "BEL Capability Modules",
    items: [
      { id: "ephemeral",     label: "Ephemeral Capture", icon: CaptureIcon    },
      { id: "narr",          label: "Coordinated Narr.", icon: NetworkIcon    },
      { id: "investigation", label: "Investigation",     icon: MagnifyIcon    },
      { id: "nlp",           label: "Multilingual NLP",  icon: NLPIcon        },
      { id: "idscan",        label: "ID Scan",           icon: IDScanIcon     },
      { id: "credibility",   label: "Credibility",       icon: ShieldIcon     },
      { id: "resilience",    label: "Resilience",        icon: ResilienceIcon },
    ],
  },
  {
    label: "Platform",
    items: [
      { id: "search",   label: "Search",       icon: SearchIcon                                    },
      { id: "sources",  label: "Sources",      icon: SourceIcon                                    },
      { id: "keywords", label: "Keywords",     icon: TagIcon                                       },
      { id: "entities", label: "Entity Graph", icon: GraphIcon                                     },
      { id: "alerts",   label: "Alerts",       icon: BellIcon },
      { id: "reports",  label: "Reports",      icon: ReportIcon                                    },
      { id: "settings", label: "Settings",     icon: GearIcon                                      },
    ],
  },
];

const BADGE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  danger:  { bg: "rgba(218,30,40,0.15)",  text: C.red40,    border: "rgba(218,30,40,0.3)"   },
  warning: { bg: "rgba(241,194,27,0.15)", text: C.yellow30, border: "rgba(241,194,27,0.3)"  },
  info:    { bg: "rgba(51,177,255,0.12)", text: C.cyan40,   border: "rgba(51,177,255,0.25)" },
  success: { bg: "rgba(66,190,101,0.15)", text: C.green40,  border: "rgba(66,190,101,0.3)"  },
};

/* ═══════════════════════════════════════════════════════════
   Sidebar Component
═══════════════════════════════════════════════════════════ */
const Sidebar: React.FC<SidebarProps> = ({ user }) => {
  const navigate  = useNavigate();
  const location  = useLocation();
  const logout    = useAuthStore((s) => s.logout);
  const storeUser = useAuthStore((s) => s.user);

  /* Derive active nav id from current URL path */
  const activePage = PATH_TO_ID[location.pathname] ?? "dashboard";

  /* Resolve display user: prop overrides store */
  const displayUser = user ?? {
    name:     storeUser?.role === "admin" ? "Administrator" : "Intelligence Analyst",
    role:     storeUser?.role ?? "analyst",
    initials: (storeUser?.username ?? "IA").slice(0, 2).toUpperCase(),
  };

  const [time, setTime] = useState<Date>(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString("en-GB", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });

  /* ── navigate or logout ── */
  const handleNav = (id: string) => {
    if (id === "__logout__") {
      logout();
      navigate("/login", { replace: true });
      return;
    }
    const path = ROUTE_MAP[id];
    if (path) navigate(path);
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        @keyframes cds-pulse  { 0%,100%{opacity:1} 50%{opacity:.35} }
        @keyframes cds-fade-in{ from{opacity:0;transform:translateX(-6px)} to{opacity:1;transform:translateX(0)} }
        *{box-sizing:border-box}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:rgba(51,177,255,.15);border-radius:2px}
      `}</style>

      <aside style={s.sidebar}>
        <div style={s.glowTop} />
        <div style={s.glowBottom} />

        {/* ── Header ── */}
        <div style={s.header}>
          <div style={s.logoMark}>
            <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
              <path d="M16 2L4 7v8c0 8.84 5.09 13.91 12 15 6.91-1.09 12-6.16 12-15V7L16 2z"
                stroke={C.cyan40} strokeWidth="1.4" fill="rgba(51,177,255,0.08)" />
              <path d="M13 16.59L10.41 14 9 15.41l4 4 8-8-1.41-1.41L13 16.59z" fill={C.cyan40} />
            </svg>
          </div>
          <div style={s.headerText}>
            <span style={s.productName}>
              <span style={{ fontWeight: 300, color: C.gray30 }}>ILA </span>
              <span style={{ fontWeight: 600, color: C.white }}>OSINT</span>
            </span>
            <span style={s.versionTag}>v0.1</span>
          </div>
        </div>

        {/* ── Status bar ── */}
        <div style={s.statusBar}>
          <span style={s.liveDot} />
          <span style={s.statusText}>SYSTEM LIVE</span>
          <span style={{ flex: 1 }} />
          <span style={s.clock}>{timeStr}</span>
        </div>

        {/* ── Nav ── */}
        <nav style={s.nav}>
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi}>
              {group.label && <div style={s.groupHeader}>{group.label}</div>}

              {group.items.map((item) => (
                <SidebarNavItem
                  key={item.id}
                  item={item}
                  active={activePage === item.id}
                  onClick={() => handleNav(item.id)}
                />
              ))}

              {gi < NAV_GROUPS.length - 1 && <div style={s.divider} />}
            </div>
          ))}
        </nav>

        {/* ── Footer ── */}
        <div style={s.footer}>
          <div style={s.avatar}>{displayUser.initials}</div>
          <div style={s.userInfo}>
            <span style={s.userName}>{displayUser.name}</span>
            <span style={s.userRole}>{displayUser.role}</span>
          </div>
          <button style={s.logoutBtn} title="Sign out" onClick={() => handleNav("__logout__")}>
            <LogoutIcon color={C.gray40} />
          </button>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;

/* ═══════════════════════════════════════════════════════════
   Nav Item
═══════════════════════════════════════════════════════════ */
interface NavItemProps { item: NavItem; active: boolean; onClick: () => void; }

const SidebarNavItem: React.FC<NavItemProps> = ({ item, active, onClick }) => {
  const [hovered, setHovered] = useState(false);
  const Icon  = item.icon;
  const badge = item.badge != null ? BADGE_COLORS[item.badgeKind ?? "info"] : null;

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={item.label}
      style={{
        display: "flex", alignItems: "center", width: "100%",
        minHeight: "32px", padding: "0 16px", gap: "12px",
        background: active ? "rgba(51,177,255,0.1)" : hovered ? "rgba(255,255,255,0.04)" : "transparent",
        border: "none",
        borderLeft: `2px solid ${active ? C.cyan40 : "transparent"}`,
        borderRadius: "0", cursor: "pointer", textAlign: "left",
        transition: "background 70ms cubic-bezier(0.2,0,0.38,0.9), border-color 70ms",
        marginBottom: "1px", outline: "none",
      }}
    >
      <span style={{ width:16, height:16, display:"flex", alignItems:"center",
        justifyContent:"center", flexShrink:0, transition:"color 70ms" }}>
        <Icon color={active ? C.cyan40 : hovered ? C.gray30 : C.gray60} />
      </span>

      <span style={{
        fontFamily: "'IBM Plex Sans', sans-serif", fontSize: "13px",
        lineHeight: "16px", letterSpacing: "0.16px",
        fontWeight: active ? 500 : 400,
        color: active ? C.cyan30 : hovered ? C.gray20 : C.gray50,
        flex: 1, transition: "color 70ms",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
      }}>
        {item.label}
      </span>

      {badge && item.badge != null && (
        <span style={{
          fontFamily: "'IBM Plex Mono', monospace", fontSize: "10px",
          fontWeight: 600, letterSpacing: "0.32px", padding: "1px 6px",
          background: badge.bg, color: badge.text,
          border: `1px solid ${badge.border}`, borderRadius: "0",
          lineHeight: "16px", flexShrink: 0,
        }}>
          {item.badge}
        </span>
      )}
    </button>
  );
};

/* ═══════════════════════════════════════════════════════════
   Styles
═══════════════════════════════════════════════════════════ */
const s: Record<string, CSSProperties> = {
  sidebar: {
    width: "240px", minWidth: "240px", height: "100vh",
    background: C.bg, borderRight: `1px solid rgba(51,177,255,0.1)`,
    display: "flex", flexDirection: "column",
    fontFamily: "'IBM Plex Sans', sans-serif",
    position: "relative", overflow: "hidden",
    animation: "cds-fade-in 0.3s ease both",
  },
  glowTop: {
    position: "absolute", top:0, left:0, right:0, height:"200px",
    background: "radial-gradient(ellipse at 50% -20%,rgba(51,177,255,0.07) 0%,transparent 70%)",
    pointerEvents: "none", zIndex: 0,
  },
  glowBottom: {
    position: "absolute", bottom:0, left:0, right:0, height:"120px",
    background: "radial-gradient(ellipse at 50% 120%,rgba(15,98,254,0.06) 0%,transparent 70%)",
    pointerEvents: "none", zIndex: 0,
  },
  header: {
    position:"relative", zIndex:2,
    display:"flex", alignItems:"center", height:"48px", padding:"0 16px", gap:"10px",
    borderBottom:`1px solid rgba(51,177,255,0.08)`, flexShrink:0,
  },
  logoMark: {
    display:"flex", alignItems:"center", justifyContent:"center",
    width:"32px", height:"32px",
    background:"rgba(51,177,255,0.07)", border:`1px solid rgba(51,177,255,0.2)`,
    flexShrink:0,
  },
  headerText: { display:"flex", alignItems:"center", gap:"8px" },
  productName: {
    fontFamily:"'IBM Plex Sans',sans-serif", fontSize:"14px",
    lineHeight:"18px", letterSpacing:"0.1em",
  },
  versionTag: {
    fontFamily:"'IBM Plex Mono',monospace", fontSize:"10px",
    letterSpacing:"0.08em", color:C.cyan40,
    background:"rgba(51,177,255,0.1)", border:`1px solid rgba(51,177,255,0.2)`,
    padding:"1px 5px", lineHeight:"16px",
  },
  statusBar: {
    position:"relative", zIndex:2,
    display:"flex", alignItems:"center", height:"28px",
    padding:"0 16px", gap:"6px",
    background:C.bgLayer, borderBottom:`1px solid rgba(51,177,255,0.06)`,
    flexShrink:0,
  },
  liveDot: {
    width:"6px", height:"6px", borderRadius:"50%", background:C.green40,
    display:"inline-block", flexShrink:0,
    animation:"cds-pulse 2s ease-in-out infinite",
  },
  statusText: {
    fontFamily:"'IBM Plex Mono',monospace", fontSize:"10px",
    letterSpacing:"0.32px", color:C.gray50,
  },
  clock: {
    fontFamily:"'IBM Plex Mono',monospace", fontSize:"10px",
    letterSpacing:"0.32px", color:C.gray60,
  },
  nav: {
    position:"relative", zIndex:2, flex:1,
    overflowY:"auto", overflowX:"hidden",
    paddingTop:"8px", paddingBottom:"8px",
  },
  groupHeader: {
    fontFamily:"'IBM Plex Sans',sans-serif", fontSize:"11px", fontWeight:600,
    letterSpacing:"0.32px", color:C.gray60,
    padding:"16px 16px 6px", textTransform:"uppercase" as const,
    userSelect:"none" as const,
  },
  divider: { height:"1px", background:`rgba(51,177,255,0.07)`, margin:"8px 0" },
  footer: {
    position:"relative", zIndex:2,
    display:"flex", alignItems:"center", gap:"10px",
    height:"48px", padding:"0 16px",
    borderTop:`1px solid rgba(51,177,255,0.1)`,
    background:C.bgLayer, flexShrink:0,
  },
  avatar: {
    width:"28px", height:"28px", borderRadius:"50%", background:C.blue60,
    display:"flex", alignItems:"center", justifyContent:"center",
    fontFamily:"'IBM Plex Sans',sans-serif", fontSize:"11px",
    fontWeight:600, color:C.white, letterSpacing:"0.04em", flexShrink:0,
  },
  userInfo: {
    flex:1, display:"flex", flexDirection:"column" as const,
    gap:"1px", minWidth:0,
  },
  userName: {
    fontFamily:"'IBM Plex Sans',sans-serif", fontSize:"12px", fontWeight:500,
    color:C.gray20, letterSpacing:"0.16px", lineHeight:"16px",
    whiteSpace:"nowrap" as const, overflow:"hidden", textOverflow:"ellipsis",
  },
  userRole: {
    fontFamily:"'IBM Plex Mono',monospace", fontSize:"10px",
    color:C.cyan40, letterSpacing:"0.32px", lineHeight:"14px",
  },
  logoutBtn: {
    width:"32px", height:"32px", display:"flex",
    alignItems:"center", justifyContent:"center",
    background:"transparent", border:"none", cursor:"pointer",
    padding:0, flexShrink:0, borderRadius:"0", transition:"background 70ms",
  },
};

/* ═══════════════════════════════════════════════════════════
   Icons
═══════════════════════════════════════════════════════════ */
const I = (props: React.SVGProps<SVGSVGElement>) => (
  <svg width="16" height="16" viewBox="0 0 32 32" fill="currentColor" {...props} />
);

function GlobeIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M16 2a14 14 0 100 28A14 14 0 0016 2zm0 2c1.76 0 3.6.95 5.18 3H10.82C12.4 4.95 14.24 4 16 4zm-8.5 5h17c.5 1.26.8 2.6.9 4H6.6c.1-1.4.4-2.74.9-4zM4 16c0-.68.06-1.35.15-2h23.7c.09.65.15 1.32.15 2s-.06 1.35-.15 2H4.15C4.06 17.35 4 16.68 4 16zm12 12c-1.76 0-3.6-.95-5.18-3h10.36C19.6 27.05 17.76 28 16 28zm8.5-5h-17a13.22 13.22 0 01-.9-4h18.8a13.22 13.22 0 01-.9 4z" /></I>;
}
function DashIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M12 20H4v-8h8zm2 0V12h14v8zm-2-10H4V4h8zm2 0V4h14v6z" /></I>;
}
function CaptureIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M11 4H4v7h7zm0 10H4v7h7zm10-10h-7v7h7zm0 10h-7v7h7z" /></I>;
}
function NetworkIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M27 22.14a4 4 0 00-3.37 1.86L11.5 17.64A4 4 0 0011.5 14.36L23.63 8a4 4 0 10-.63-2.14 4 4 0 00.37 1.64L11.24 13.86a4 4 0 100 4.28l12.13 6.36A4 4 0 1027 22.14zM27 6a2 2 0 11-2 2 2 2 0 012-2zM5 18a2 2 0 112-2 2 2 0 01-2 2zm22 8a2 2 0 112-2 2 2 0 01-2 2z" /></I>;
}
function MagnifyIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M28.83 26.83L22 20a9 9 0 10-1.41 1.41l6.83 6.83zM5 13a8 8 0 118 8 8 8 0 01-8-8z" /></I>;
}
function NLPIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M28 6H4a2 2 0 00-2 2v16a2 2 0 002 2h24a2 2 0 002-2V8a2 2 0 00-2-2zm0 18H4V8h24zM8 13h16v2H8zm0 5h10v2H8z" /></I>;
}
function IDScanIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M2 10V6a2 2 0 012-2h4V2H4a4 4 0 00-4 4v4zM2 22v4a2 2 0 002 2h4v-2H4v-4zm26-12V6a2 2 0 00-2-2h-4V2h4a4 4 0 014 4v4zm0 12v4a2 2 0 01-2 2h-4v-2h4v-4zM14 10h4a2 2 0 012 2v8a2 2 0 01-2 2h-4a2 2 0 01-2-2v-8a2 2 0 012-2zm0 2v8h4v-8z" /></I>;
}
function ShieldIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M16 2L4 7v8c0 8.84 5.09 13.91 12 15 6.91-1.09 12-6.16 12-15V7L16 2zm0 2.18L26 8.3V15c0 7.52-4.32 11.89-10 13.06C10.32 26.89 6 22.52 6 15V8.3z" /><path d="M13 16.59L10.41 14 9 15.41l4 4 8-8-1.41-1.41L13 16.59z" /></I>;
}
function ResilienceIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M16 4a12 12 0 1012 12A12 12 0 0016 4zm0 22a10 10 0 1110-10 10 10 0 01-10 10z" /><path d="M21.5 11l-7.5 7.5-3.5-3.5-1.5 1.5 5 5 9-9z" /></I>;
}
function SearchIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M28.83 26.83L22 20a9 9 0 10-1.41 1.41l6.83 6.83zM5 13a8 8 0 118 8 8 8 0 01-8-8z" /></I>;
}
function SourceIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M4 6h24v2H4zm0 6h24v2H4zm0 6h16v2H4z" /></I>;
}
function TagIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M17.41 2H8a2 2 0 00-2 2v9.41a2 2 0 00.59 1.42l13 13a2 2 0 002.82 0l9.41-9.41a2 2 0 000-2.82l-13-13A2 2 0 0017.41 2zM10 10a2 2 0 112-2 2 2 0 01-2 2z" /></I>;
}
function GraphIcon({ color }: { color: string }) {
  return <I style={{ color }}><circle cx="16" cy="8" r="4" /><circle cx="6" cy="24" r="4" /><circle cx="26" cy="24" r="4" /><path d="M14 11.5l-6 9M18 11.5l6 9M10 24h12" strokeWidth="2" stroke={color} fill="none" /></I>;
}
function BellIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M28.71 19.29L26 16.59V13A10 10 0 006 13v3.59l-2.71 2.7A1 1 0 004 21h6a6 6 0 0012 0h6a1 1 0 00.71-1.71zM16 25a4 4 0 01-4-4h8a4 4 0 01-4 4zM6.41 19L8 17.41V13a8 8 0 0116 0v4.41L25.59 19z" /></I>;
}
function ReportIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M24 2H8a2 2 0 00-2 2v24a2 2 0 002 2h16a2 2 0 002-2V4a2 2 0 00-2-2zm0 26H8V4h16zm-4-20H12v2h8zm0 5H12v2h8zm-5 5h-3v2h3z" /></I>;
}
function GearIcon({ color }: { color: string }) {
  return <I style={{ color }}><path d="M27 16.76V15.24l1.92-1.68A2 2 0 0029.3 11L27.1 7.17a2 2 0 00-2.44-.89l-2.39.96a10.76 10.76 0 00-1.31-.75l-.36-2.53A2 2 0 0018.62 2h-4.24a2 2 0 00-1.98 1.96l-.36 2.53a10.76 10.76 0 00-1.31.75l-2.39-.96a2 2 0 00-2.44.89L3.7 11a2 2 0 00.38 2.56L6 15.24v1.52l-1.92 1.68A2 2 0 003.7 21l2.2 3.83a2 2 0 002.44.89l2.39-.96c.43.26.87.51 1.31.75l.36 2.53A2 2 0 0014.38 30h4.24a2 2 0 001.98-1.96l.36-2.53c.44-.24.88-.49 1.31-.75l2.39.96a2 2 0 002.44-.89L29.3 21a2 2 0 00-.38-2.56zm-1.48 3.45l-2.7 4.7-3.13-1.25a8.52 8.52 0 01-2.2 1.28l-.47 3.32h-5.4l-.47-3.32a8.52 8.52 0 01-2.2-1.28l-3.13 1.25-2.7-4.7 2.51-2.21a8.66 8.66 0 01-.08-1 8.66 8.66 0 01.08-1l-2.51-2.21 2.7-4.7 3.13 1.25a8.52 8.52 0 012.2-1.28l.47-3.32h5.4l.47 3.32a8.52 8.52 0 012.2 1.28l3.13-1.25 2.7 4.7-2.51 2.21a8.66 8.66 0 01.08 1 8.66 8.66 0 01-.08 1zM16 10a6 6 0 106 6 6 6 0 00-6-6zm0 10a4 4 0 114-4 4 4 0 01-4 4z" /></I>;
}
function LogoutIcon({ color }: { color: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 32 32" fill={color}>
      <path d="M6 30h12a2 2 0 002-2v-3h-2v3H6V4h12v3h2V4a2 2 0 00-2-2H6a2 2 0 00-2 2v24a2 2 0 002 2z" />
      <path d="M20.59 20.59L24.17 17H10v-2h14.17l-3.58-3.59L22 10l6 6-6 6-1.41-1.41z" />
    </svg>
  );
}