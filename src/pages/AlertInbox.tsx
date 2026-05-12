import { useState, useEffect, useRef, CSSProperties, ReactNode } from 'react';

/* ─────────────────────────────────────────
   IBM CARBON DESIGN SYSTEM — GRAY 100 THEME
   Tokens: https://carbondesignsystem.com/guidelines/color/tokens
───────────────────────────────────────── */
const C = {
  /* Backgrounds & layers */
  background:        '#161616',
  layer01:           '#262626',
  layer02:           '#393939',
  layerHover01:      '#2e2e2e',
  layerActive01:     '#525252',

  /* Borders */
  borderSubtle00:    '#393939',
  borderSubtle01:    '#525252',
  borderStrong01:    '#6f6f6f',
  borderInteractive: '#4589ff',

  /* Text */
  textPrimary:     '#f4f4f4',
  textSecondary:   '#c6c6c6',
  textHelper:      '#8d8d8d',
  textPlaceholder: '#6f6f6f',
  textOnColor:     '#ffffff',
  textDisabled:    '#525252',

  /* Icon */
  iconPrimary:   '#f4f4f4',
  iconSecondary: '#c6c6c6',

  /* Support (semantic) */
  supportError:   '#fa4d56',
  supportWarning: '#f1c21b',
  supportSuccess: '#42be65',
  supportInfo:    '#4589ff',

  /* Notification backgrounds */
  notifErrorBg:   '#2d0709',
  notifWarningBg: '#302400',
  notifSuccessBg: '#071908',
  notifInfoBg:    '#001d6c',

  /* Interactive / link */
  interactive: '#4589ff',
  focus:       '#4589ff',
  linkPrimary: '#78a9ff',

  /* Carbon Tag color pairs (bg / text) */
  tagRed:      { bg: '#a2191f', text: '#ffd7d9' },
  tagOrange:   { bg: '#8a3800', text: '#ffd9be' },
  tagYellow:   { bg: '#684e00', text: '#fce300' },
  tagGreen:    { bg: '#0e6027', text: '#a7f0ba' },
  tagBlue:     { bg: '#002d9c', text: '#a6c8ff' },
  tagPurple:   { bg: '#5a1ba9', text: '#d4bbff' },
  tagCoolGray: { bg: '#4d5358', text: '#dde1e6' },
};

/* Carbon Type Scale — IBM Plex Sans / IBM Plex Mono */
const T = {
  label01:    { fontSize: 11, lineHeight: '16px', letterSpacing: '0.32px', fontWeight: 400 },
  label02:    { fontSize: 12, lineHeight: '16px', letterSpacing: '0.32px', fontWeight: 400 },
  body01:     { fontSize: 14, lineHeight: '20px', letterSpacing: '0.16px', fontWeight: 400 },
  code01:     { fontSize: 12, lineHeight: '16px', letterSpacing: '0.32px', fontFamily: "'IBM Plex Mono', monospace" },
  code02:     { fontSize: 14, lineHeight: '20px', letterSpacing: '0.32px', fontFamily: "'IBM Plex Mono', monospace" },
  heading01:  { fontSize: 14, lineHeight: '18px', letterSpacing: '0.16px', fontWeight: 600 },
  heading02:  { fontSize: 16, lineHeight: '22px', letterSpacing: '0px',    fontWeight: 600 },
  heading03:  { fontSize: 20, lineHeight: '28px', letterSpacing: '0px',    fontWeight: 400 },
  heading04:  { fontSize: 28, lineHeight: '36px', letterSpacing: '0px',    fontWeight: 400 },
};

/* ─────────────────────────────────────────
   MOCK DATA
───────────────────────────────────────── */
const MOCK_ALERTS = [
  { id:'ALT-7821', entity_name:'aadhaar-update-portal.in', entity_type:'domain', alert_type:'Phishing Domain Detected', risk_score:94, status:'new', source:'OSINT-Feed', source_tier:1, summary:'New phishing domain detected: aadhaar-update-portal.in (lookalike score: 0.92). Domain registered 6 hours ago with privacy-protected WHOIS.', primary_id:'DOM-9921-IN', aliases:['update-aadhaar.in','aadhar-portal.net'], flags:['phishing','domain_cluster','velocity_anomaly'], timestamp:Date.now()-1000*60*8, severity:'critical', type:'Entity' },
  { id:'ALT-7820', entity_name:'UPI transfer.fast@paytm', entity_type:'account', alert_type:'Financial Fraud Pattern', risk_score:88, status:'new', source:'FinInt-API', source_tier:2, summary:'Financial fraud pattern: UPI transfer.fast@paytm linked to 28 mule accounts across 4 banks. Transaction velocity 340% above baseline.', primary_id:'ACC-4471-FIN', aliases:['@paytm_fast','upi.transfer22'], flags:['hawala','velocity_anomaly','network_centrality'], timestamp:Date.now()-1000*60*33, severity:'critical', type:'Fraud' },
  { id:'ALT-7819', entity_name:'Bomb Threat — Kolkata Metro', entity_type:'event', alert_type:'Threat Escalation', risk_score:97, status:'under_review', source:'SocMed-Monitor', source_tier:1, summary:'Bomb threat mentions in Kolkata exceed alert threshold. 47 coordinated posts across 3 platforms within 12 minutes.', primary_id:'EVT-0033-KOL', aliases:[], flags:['coordinated_behavior','keyword_match','velocity_anomaly'], timestamp:Date.now()-1000*60*55, severity:'critical', type:'Terrorism' },
  { id:'ALT-7818', entity_name:'@NarendraModi_Fan99', entity_type:'account', alert_type:'Inauthentic Coordinated Behaviour', risk_score:71, status:'new', source:'Twitter-API', source_tier:2, summary:'Account shows signs of coordinated inauthentic behaviour. Part of a 214-node botnet amplifying political disinformation.', primary_id:'TW-8812-IN', aliases:['@NaMo_fan99','@Supporter_Modi9'], flags:['coordinated_behavior','inauthentic_content','sim_cluster'], timestamp:Date.now()-1000*60*90, severity:'high', type:'Threat' },
  { id:'ALT-7817', entity_name:'Investment Scheme — Srinagar', entity_type:'event', alert_type:'Threat Escalation', risk_score:82, status:'new', source:'SocMed-Monitor', source_tier:1, summary:'Investment scheme mentions in Srinagar exceed alert threshold. Likely Ponzi structure with 1,200+ victims identified.', primary_id:'EVT-0034-SRN', aliases:[], flags:['keyword_match','network_centrality','pattern_match'], timestamp:Date.now()-1000*60*108, severity:'critical', type:'Fraud' },
  { id:'ALT-7816', entity_name:'RBI Digital Fraud Narrative', entity_type:'narrative', alert_type:'Coordinated Narrative Spread', risk_score:65, status:'confirmed', source:'OSINT-Feed', source_tier:1, summary:'RBI is mulling measures to tackle rising digital fraud. Coordinated amplification detected across Telegram channels.', primary_id:'NAR-2201-FIN', aliases:[], flags:['coordinated_behavior','negative_sentiment','pattern_match'], timestamp:Date.now()-1000*60*142, severity:'high', type:'Fraud' },
  { id:'ALT-7815', entity_name:'Operation Sindoor — Anniversary', entity_type:'event', alert_type:'Narrative Amplification', risk_score:58, status:'dismissed', source:'NewsAPI', source_tier:3, summary:'Spike in cross-border messaging around Operation Sindoor anniversary. Glorification patterns detected.', primary_id:'EVT-0031-DEL', aliases:[], flags:['keyword_match','coordinated_behavior'], timestamp:Date.now()-1000*60*180, severity:'medium', type:'Terrorism' },
  { id:'ALT-7814', entity_name:'Air India Multi-Modal Hub', entity_type:'narrative', alert_type:'Sensitive Infrastructure Mention', risk_score:44, status:'new', source:'NewsAPI', source_tier:3, summary:'Airport integrated multi-modal connectivity hub drawing attention from adversarial actors. Keyword match confirmed.', primary_id:'NAR-2199-INF', aliases:[], flags:['keyword_match','negative_sentiment'], timestamp:Date.now()-1000*60*210, severity:'info', type:'Threat' },
];

/* ─────────────────────────────────────────
   SEVERITY / STATUS CONFIG
───────────────────────────────────────── */
const SEV = {
  critical: { tag: C.tagRed,      label: 'Critical', color: C.supportError,   notifKind: 'error' },
  high:     { tag: C.tagOrange,   label: 'High',     color: C.supportWarning, notifKind: 'warning' },
  medium:   { tag: C.tagBlue,     label: 'Medium',   color: C.supportInfo,    notifKind: 'info' },
  info:     { tag: C.tagCoolGray, label: 'Info',     color: C.textHelper,     notifKind: 'info' },
};
const STAT = {
  new:          { tag: C.tagRed,      label: 'New' },
  under_review: { tag: C.tagYellow,   label: 'In review' },
  confirmed:    { tag: C.tagGreen,    label: 'Confirmed' },
  dismissed:    { tag: C.tagCoolGray, label: 'Dismissed' },
};
const FLAG_LABELS = {
  velocity_anomaly:'Velocity anomaly', pattern_match:'Pattern match', negative_sentiment:'Negative sentiment',
  coordinated_behavior:'Coordinated', sim_cluster:'SIM cluster', phishing:'Phishing',
  domain_cluster:'Domain cluster', hawala:'Hawala', keyword_match:'Keyword match',
  network_centrality:'Network hub', inauthentic_content:'Inauthentic', crypto_layering:'Crypto layering',
};
const TYPE_OPTIONS     = ['All types','Threat','Fraud','Terrorism','Entity'];
const SOURCE_OPTIONS   = ['All sources','OSINT-Feed','FinInt-API','SocMed-Monitor','Twitter-API','NewsAPI'];
const SEVERITY_OPTIONS = ['all','critical','high','medium','info'];
const PAGE_LIMIT       = 20;
const DEFAULT_FILTERS: AlertFilters = { severity:'all', type:'All types', source:'All sources', dateFrom:'', dateTo:'' };

interface AlertFilters {
  severity: string;
  type: string;
  source: string;
  dateFrom: string;
  dateTo: string;
}

interface FetchAlertsParams {
  query?: string;
  page?: number;
  limit?: number;
  filters?: Partial<AlertFilters>;
}

interface TagProps {
  pair: { bg: string; text: string };
  small?: boolean;
  children: ReactNode;
  onRemove?: () => void;
}

interface BtnProps {
  kind?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'tertiary';
  size?: 'sm' | 'md' | 'lg';
  onClick?: (e: any) => void;
  disabled?: boolean;
  style?: CSSProperties;
  children: ReactNode;
}

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  width?: number;
  icon?: ReactNode;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  width?: number;
}

interface DateInputProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

/* ─────────────────────────────────────────
   HELPERS
───────────────────────────────────────── */
function formatTime(ts) {
  const d = Date.now() - ts;
  if (d < 60000)    return `${Math.floor(d/1000)}s ago`;
  if (d < 3600000)  return `${Math.floor(d/60000)}m ago`;
  if (d < 86400000) return `${Math.floor(d/3600000)}h ago`;
  return `${Math.floor(d/86400000)}d ago`;
}

async function fetchAlerts({ query='', page=1, limit=PAGE_LIMIT, filters=DEFAULT_FILTERS }: FetchAlertsParams = {}) {
  const params = new URLSearchParams({ page: String(page), limit: String(limit),
    ...(query && { search: query }),
    ...(filters.severity && filters.severity!=='all'          && { severity: filters.severity }),
    ...(filters.type     && filters.type    !=='All types'    && { type: filters.type }),
    ...(filters.source   && filters.source  !=='All sources'  && { source: filters.source }),
    ...(filters.dateFrom && { date_from: filters.dateFrom }),
    ...(filters.dateTo   && { date_to: filters.dateTo }),
  } as Record<string, string>);
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/alerts?${params}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    const results = data.data ?? data.results ?? [];
    return { results, hasMore: results.length === limit };
  } catch {
    let r = [...MOCK_ALERTS];
    if (query) { const q=query.toLowerCase(); r=r.filter(a=>a.summary.toLowerCase().includes(q)||a.entity_name.toLowerCase().includes(q)||a.id.toLowerCase().includes(q)); }
    if (filters.severity && filters.severity!=='all')       r=r.filter(a=>a.severity===filters.severity);
    if (filters.type     && filters.type    !=='All types') r=r.filter(a=>a.type===filters.type);
    if (filters.source   && filters.source  !=='All sources') r=r.filter(a=>a.source===filters.source);
    if (filters.dateFrom) r=r.filter(a=>a.timestamp>=new Date(filters.dateFrom).getTime());
    if (filters.dateTo)   r=r.filter(a=>a.timestamp<=new Date(filters.dateTo).getTime()+86399999);
    const start=(page-1)*limit;
    return { results:r.slice(start,start+limit), hasMore:start+limit<r.length };
  }
}

/* ─────────────────────────────────────────
   ATOMIC CARBON COMPONENTS
───────────────────────────────────────── */

/* Tag — square, no border-radius (Carbon spec) */
function Tag({ pair, small, children, onRemove }: TagProps) {
  const { bg, text } = pair || C.tagCoolGray;
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:4, background:bg, color:text,
      padding: small ? '0 6px' : '0 8px', height: small ? 18 : 24, borderRadius:0, ...T.label01, whiteSpace:'nowrap' }}>
      {children}
      {onRemove && (
        <button onClick={onRemove} aria-label="Remove"
          style={{ background:'none',border:'none',cursor:'pointer',color:text,padding:0,lineHeight:1,fontSize:13,display:'flex',alignItems:'center' }}>
          ×
        </button>
      )}
    </span>
  );
}

/* Button — border-radius 0, height 40 (md), 32 (sm), 48 (lg) */
function Btn({ kind='primary', size='md', onClick, disabled, style:ext, children }: BtnProps) {
  const [hov,setHov]=useState(false);
  const K={
    primary:   {bg:'#0f62fe',bgH:'#0353e9',color:C.textOnColor,border:'none'},
    secondary: {bg:C.layer02,bgH:'#4c4c4c',color:C.textPrimary,border:'none'},
    ghost:     {bg:'transparent',bgH:C.layerHover01,color:C.linkPrimary,border:'none'},
    danger:    {bg:C.supportError,bgH:'#ba1b23',color:C.textOnColor,border:'none'},
    tertiary:  {bg:'transparent',bgH:'rgba(255,255,255,0.06)',color:C.textPrimary,border:`1px solid ${C.borderStrong01}`},
  }[kind];
  const h={sm:32,md:40,lg:48}[size];
  return (
    <button onClick={onClick} disabled={disabled} onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      style={{ height:h, padding:'0 15px', background:hov?K.bgH:K.bg, color:K.color, border:K.border,
        borderRadius:0, cursor:disabled?'not-allowed':'pointer', opacity:disabled?.5:1,
        ...T.body01, display:'inline-flex', alignItems:'center', gap:8, transition:'background 70ms',
        whiteSpace:'nowrap', ...ext }}>
      {children}
    </button>
  );
}

/* Text input — Carbon style: bottom border only, no radius */
function TextInput({ value, onChange, placeholder, width=256, icon }: TextInputProps) {
  const [foc,setFoc]=useState(false);
  return (
    <div style={{ width, position:'relative' }}>
      {icon && <span style={{ position:'absolute',left:12,top:'50%',transform:'translateY(-50%)',color:C.iconSecondary,fontSize:16,pointerEvents:'none' }}>{icon}</span>}
      <input value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}
        onFocus={()=>setFoc(true)} onBlur={()=>setFoc(false)}
        style={{ width:'100%', height:40, background:C.layer01, border:'none',
          borderBottom:`2px solid ${foc?C.focus:C.borderStrong01}`,
          color:C.textPrimary, padding:icon?'0 12px 0 40px':'0 12px',
          outline:'none', boxSizing:'border-box', ...T.body01, borderRadius:0 }} />
    </div>
  );
}

/* Select — bottom border only */
function Select({ value, onChange, options, width=164 }) {
  return (
    <div style={{ width, position:'relative' }}>
      <select value={value} onChange={e=>onChange(e.target.value)}
        style={{ width:'100%', height:40, background:C.layer01, border:'none',
          borderBottom:`2px solid ${C.borderStrong01}`, color:C.textPrimary,
          padding:'0 32px 0 12px', appearance:'none', outline:'none',
          ...T.body01, borderRadius:0, cursor:'pointer' }}>
        {options.map(o=><option key={o} value={o} style={{background:C.layer02}}>{o}</option>)}
      </select>
      <span style={{ position:'absolute',right:10,top:'50%',transform:'translateY(-50%)',color:C.iconSecondary,pointerEvents:'none',fontSize:10 }}>▾</span>
    </div>
  );
}

/* Date input */
function DateInput({ value, onChange, label }) {
  return (
    <div>
      {label && <div style={{ ...T.label01, color:C.textHelper, marginBottom:4 }}>{label}</div>}
      <input type="date" value={value} onChange={e=>onChange(e.target.value)}
        style={{ width:'100%', height:40, background:C.layer01, border:'none',
          borderBottom:`2px solid ${C.borderStrong01}`, color:value?C.textPrimary:C.textPlaceholder,
          padding:'0 12px', outline:'none', boxSizing:'border-box', ...T.body01, borderRadius:0, colorScheme:'dark' }} />
    </div>
  );
}

/* Carbon Loading Spinner (SVG) */
function Spinner({ size=20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{animation:'cds-spin 0.7s linear infinite'}} aria-label="Loading">
      <circle cx="50" cy="50" r="44" fill="none" stroke={C.borderSubtle01} strokeWidth="10"/>
      <circle cx="50" cy="50" r="44" fill="none" stroke={C.interactive} strokeWidth="10"
        strokeDasharray="138 138" strokeDashoffset="103" strokeLinecap="butt" transform="rotate(-90 50 50)"/>
    </svg>
  );
}

/* Carbon Inline Notification */
function InlineNotif({ kind='error', title }) {
  const K={
    error:  {bg:C.notifErrorBg,  bar:C.supportError,  icon:'⊗'},
    warning:{bg:C.notifWarningBg,bar:C.supportWarning,icon:'⚠'},
    success:{bg:C.notifSuccessBg,bar:C.supportSuccess,icon:'✓'},
    info:   {bg:C.notifInfoBg,   bar:C.supportInfo,   icon:'ℹ'},
  }[kind];
  return (
    <div style={{ display:'flex',alignItems:'center',gap:10, background:K.bg,
      borderLeft:`3px solid ${K.bar}`, padding:'10px 16px', ...T.body01 }}>
      <span style={{color:K.bar,fontSize:15,flexShrink:0}}>{K.icon}</span>
      <span style={{color:C.textPrimary,fontWeight:600}}>{title}</span>
    </div>
  );
}

/* ─────────────────────────────────────────
   DATA TABLE ROW
───────────────────────────────────────── */
function AlertRow({ alert, selected, onClick }) {
  const [hov,setHov]=useState(false);
  const sev  = SEV[alert.severity]  || SEV.info;
  const stat = STAT[alert.status]   || STAT.new;
  const scoreColor = alert.risk_score>=85?C.supportError:alert.risk_score>=65?C.supportWarning:C.supportInfo;

  return (
    <tr onClick={()=>onClick(alert)} onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      style={{ background:selected?C.layerActive01:hov?C.layerHover01:'transparent',
        borderLeft:`3px solid ${selected?sev.color:'transparent'}`,
        cursor:'pointer', transition:'background 70ms' }}>

      <td style={{padding:'11px 16px',whiteSpace:'nowrap'}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          {alert.status==='new' && (
            <span style={{width:6,height:6,borderRadius:'50%',background:sev.color,display:'inline-block',
              animation:'cds-blink 1.4s infinite',flexShrink:0}} />
          )}
          <Tag pair={sev.tag} small>{sev.label}</Tag>
        </div>
      </td>

      <td style={{padding:'11px 16px',maxWidth:0}}>
        <div style={{...T.body01,color:C.textPrimary,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{alert.summary}</div>
        <div style={{...T.code01,color:C.textHelper,marginTop:2}}>{alert.id} · {alert.entity_name}</div>
      </td>

      <td style={{padding:'11px 16px',whiteSpace:'nowrap'}}>
        <span style={{...T.label01,color:C.textSecondary}}>{alert.type}</span>
      </td>

      <td style={{padding:'11px 16px',whiteSpace:'nowrap'}}>
        <Tag pair={stat.tag} small>{stat.label}</Tag>
      </td>

      <td style={{padding:'11px 16px',textAlign:'center'}}>
        <span style={{...T.code02,color:scoreColor,fontWeight:600}}>{alert.risk_score}</span>
      </td>

      <td style={{padding:'11px 16px',whiteSpace:'nowrap'}}>
        <span style={{...T.label01,color:C.textHelper}}>{formatTime(alert.timestamp)}</span>
      </td>

      <td style={{padding:'11px 16px',textAlign:'right'}}>
        <Btn kind="ghost" size="sm" onClick={e=>e.stopPropagation()}>ACK</Btn>
      </td>
    </tr>
  );
}

/* ─────────────────────────────────────────
   TASK 4 — FILTER PANEL
   Carbon: right-side "flyout" panel
   Sections: Alert type · Risk level · Source · Date range
───────────────────────────────────────── */
function FilterPanel({ filters, onChange, onClear, resultCount }) {
  const [open, setOpen] = useState(false);

  const activeCount = [
    filters.severity !== 'all',
    filters.type     !== 'All types',
    filters.source   !== 'All sources',
    !!filters.dateFrom,
    !!filters.dateTo,
  ].filter(Boolean).length;

  const Divider = () => <div style={{height:1,background:C.borderSubtle00,margin:'16px 0'}}/>;
  const SectionLabel = ({children}) => (
    <div style={{...T.label01,color:C.textHelper,letterSpacing:'0.32px',textTransform:'uppercase',marginBottom:10}}>
      {children}
    </div>
  );

  /* Carbon Checkbox */
  const CbBox = ({ checked, onToggle, label }) => (
    <label style={{display:'flex',alignItems:'center',gap:10,cursor:'pointer',padding:'5px 0'}}>
      <div onClick={onToggle} style={{
        width:16,height:16,flexShrink:0,borderRadius:0,cursor:'pointer',
        border:`2px solid ${checked?C.interactive:C.borderStrong01}`,
        background:checked?C.interactive:'transparent',
        display:'flex',alignItems:'center',justifyContent:'center',
        transition:'background 70ms, border-color 70ms',
      }}>
        {checked && <span style={{color:'#fff',fontSize:10,fontWeight:700,lineHeight:1}}>✓</span>}
      </div>
      <span style={{...T.body01,color:C.textPrimary}} onClick={onToggle}>{label}</span>
    </label>
  );

  return (
    <>
      {/* Toolbar trigger button */}
      <Btn kind={activeCount>0?'primary':'tertiary'} size="md" onClick={()=>setOpen(o=>!o)}>
        {/* Carbon Filter icon */}
        <svg width="16" height="16" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
          <path d="M18 28H14a2 2 0 01-2-2v-7.59L4.59 11A2 2 0 014 9.59V6a2 2 0 012-2h20a2 2 0 012 2v3.59a2 2 0 01-.59 1.41L20 18.41V26a2 2 0 01-2 2zM6 6v3.59l8 8V26h4v-8.41l8-8V6z"/>
        </svg>
        Filters
        {activeCount>0 && (
          <span style={{background:'#fff',color:'#0f62fe',borderRadius:'50%',width:18,height:18,
            display:'inline-flex',alignItems:'center',justifyContent:'center',...T.label01,fontWeight:600}}>
            {activeCount}
          </span>
        )}
      </Btn>

      {/* Backdrop */}
      {open && <div onClick={()=>setOpen(false)} style={{position:'fixed',inset:0,zIndex:200}}/>}

      {/* Carbon right flyout panel */}
      <div style={{
        position:'fixed', top:0, right:0, width:320, height:'100vh',
        background:C.layer01, borderLeft:`1px solid ${C.borderSubtle01}`,
        zIndex:300, display:'flex', flexDirection:'column',
        transform:open?'translateX(0)':'translateX(100%)',
        transition:'transform 240ms cubic-bezier(0.4,0,0.2,1)',
        boxSizing:'border-box',
      }}>
        {/* Panel header */}
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',
          padding:'16px',borderBottom:`1px solid ${C.borderSubtle00}`,flexShrink:0}}>
          <div>
            <div style={{...T.heading02,color:C.textPrimary}}>Filters</div>
            <div style={{...T.label01,color:C.textHelper,marginTop:3}}>
              {resultCount} result{resultCount!==1?'s':''} match
            </div>
          </div>
          <button onClick={()=>setOpen(false)} aria-label="Close"
            style={{background:'none',border:'none',cursor:'pointer',color:C.iconSecondary,fontSize:20,
              padding:4,display:'flex',alignItems:'center'}}>
            ×
          </button>
        </div>

        {/* Panel body — scrollable */}
        <div style={{flex:1,overflowY:'auto',padding:'20px 16px'}}>

          {/* Alert type */}
          <SectionLabel>Alert type</SectionLabel>
          <div style={{display:'flex',flexWrap:'wrap',gap:4,marginBottom:4}}>
            {TYPE_OPTIONS.map(t=>(
              <button key={t} onClick={()=>onChange({type:t})} style={{
                height:32,padding:'0 12px',
                background:filters.type===t?C.interactive:C.layer02,
                color:filters.type===t?C.textOnColor:C.textSecondary,
                border:'none',borderRadius:0,...T.label02,cursor:'pointer',
                transition:'background 70ms',
              }}>{t}</button>
            ))}
          </div>

          <Divider/>

          {/* Risk level */}
          <SectionLabel>Risk level</SectionLabel>
          <div style={{display:'flex',gap:4,flexWrap:'wrap',marginBottom:4}}>
            {SEVERITY_OPTIONS.map(s=>{
              const cfg=s==='all'?{tag:C.tagCoolGray,label:'All'}:SEV[s];
              const active=filters.severity===s;
              return (
                <button key={s} onClick={()=>onChange({severity:s})} style={{
                  height:30,padding:'0 11px',
                  background:active?cfg.tag.bg:C.layer02,
                  color:active?cfg.tag.text:C.textSecondary,
                  border:active?`1px solid ${cfg.tag.text}40`:`1px solid transparent`,
                  borderRadius:0,...T.label01,cursor:'pointer',transition:'background 70ms',
                }}>{cfg.label||s}</button>
              );
            })}
          </div>

          <Divider/>

          {/* Source — checkboxes */}
          <SectionLabel>Source</SectionLabel>
          {SOURCE_OPTIONS.map(src=>(
            <CbBox key={src}
              checked={filters.source===src}
              onToggle={()=>onChange({source:filters.source===src?'All sources':src})}
              label={src}
            />
          ))}

          <Divider/>

          {/* Date range */}
          <SectionLabel>Date range</SectionLabel>
          <div style={{display:'flex',flexDirection:'column',gap:12}}>
            <DateInput label="Start date" value={filters.dateFrom} onChange={v=>onChange({dateFrom:v})}/>
            <DateInput label="End date"   value={filters.dateTo}   onChange={v=>onChange({dateTo:v})}/>
          </div>

          {/* Active filter chips */}
          {activeCount>0 && (
            <>
              <Divider/>
              <SectionLabel>Active filters</SectionLabel>
              <div style={{display:'flex',flexWrap:'wrap',gap:6}}>
                {filters.severity!=='all'        && <Tag pair={C.tagCoolGray} onRemove={()=>onChange({severity:'all'})}>Risk: {filters.severity}</Tag>}
                {filters.type    !=='All types'  && <Tag pair={C.tagCoolGray} onRemove={()=>onChange({type:'All types'})}>Type: {filters.type}</Tag>}
                {filters.source  !=='All sources'&& <Tag pair={C.tagCoolGray} onRemove={()=>onChange({source:'All sources'})}>{filters.source}</Tag>}
                {filters.dateFrom                && <Tag pair={C.tagCoolGray} onRemove={()=>onChange({dateFrom:''})}>From: {filters.dateFrom}</Tag>}
                {filters.dateTo                  && <Tag pair={C.tagCoolGray} onRemove={()=>onChange({dateTo:''})}>To: {filters.dateTo}</Tag>}
              </div>
            </>
          )}
        </div>

        {/* Panel footer — Carbon button group, flush to edges */}
        <div style={{flexShrink:0,borderTop:`1px solid ${C.borderSubtle00}`,display:'flex'}}>
          <Btn kind="secondary" size="lg" onClick={onClear}
            style={{flex:1,justifyContent:'center',borderRadius:0,borderRight:`1px solid ${C.borderSubtle00}`}}>
            Clear all
          </Btn>
          <Btn kind="primary" size="lg" onClick={()=>setOpen(false)}
            style={{flex:1,justifyContent:'center',borderRadius:0}}>
            Apply
          </Btn>
        </div>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────
   ALERT DETAIL — Carbon Structured List
───────────────────────────────────────── */
function AlertDetail({ alert, onStatusChange }) {
  if (!alert) return (
    <div style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:10}}>
      <svg width="40" height="40" viewBox="0 0 32 32" fill={C.borderStrong01} aria-hidden="true">
        <path d="M16 2a14 14 0 1014 14A14 14 0 0016 2zm0 26a12 12 0 110-24 12 12 0 010 24zm0-22a1.5 1.5 0 101.5 1.5A1.5 1.5 0 0016 6zm1 5h-2v12h2z"/>
      </svg>
      <div style={{...T.heading01,color:C.textSecondary}}>No alert selected</div>
      <div style={{...T.body01,color:C.textHelper}}>Select a row to view details</div>
    </div>
  );

  const sev    = SEV[alert.severity] || SEV.info;
  const stat   = STAT[alert.status]  || STAT.new;
  const score  = alert.risk_score;
  const scoreC = score>=85?C.supportError:score>=65?C.supportWarning:C.supportInfo;

  const STATUS_ACTIONS = {
    new:          [{label:'Start review',  next:'under_review'}],
    under_review: [{label:'Confirm',       next:'confirmed'},{label:'Dismiss',next:'dismissed'}],
    confirmed:    [{label:'Reopen',        next:'under_review'}],
    dismissed:    [{label:'Reopen',        next:'new'}],
  };

  /* Structured list row */
  const SRow = ({label,value,mono}: { label:string; value:string; mono?: boolean }) => (
    <div style={{display:'grid',gridTemplateColumns:'120px 1fr',padding:'9px 16px',borderBottom:`1px solid ${C.borderSubtle00}`}}>
      <span style={{...T.label01,color:C.textHelper}}>{label}</span>
      <span style={{...(mono?T.code01:T.body01),color:C.textPrimary,wordBreak:'break-all'}}>{value}</span>
    </div>
  );

  return (
    <div style={{flex:1,overflowY:'auto'}}>
      {/* Tile header */}
      <div style={{padding:'16px',background:C.layer01,borderLeft:`4px solid ${sev.color}`,borderBottom:`1px solid ${C.borderSubtle01}`}}>
        <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:12}}>
          <div style={{flex:1,minWidth:0}}>
            <div style={{...T.heading02,color:C.textPrimary,marginBottom:4}}>{alert.entity_name}</div>
            <div style={{...T.code01,color:C.textHelper}}>{alert.id} · {alert.entity_type}</div>
          </div>
          {/* Carbon expressive number */}
          <div style={{textAlign:'center',flexShrink:0}}>
            <div style={{...T.heading04,color:scoreC,lineHeight:1}}>{score}</div>
            <div style={{...T.label01,color:C.textHelper}}>Risk score</div>
          </div>
        </div>
        <div style={{display:'flex',gap:6,marginTop:12,flexWrap:'wrap'}}>
          <Tag pair={sev.tag}>{sev.label}</Tag>
          <Tag pair={stat.tag}>{stat.label}</Tag>
          <Tag pair={C.tagCoolGray}>{alert.source}</Tag>
        </div>
      </div>

      {/* Alert type notification */}
      <InlineNotif kind={sev.notifKind} title={alert.alert_type}/>

      {/* Summary */}
      <div style={{padding:'12px 16px',borderBottom:`1px solid ${C.borderSubtle00}`}}>
        <div style={{...T.label01,color:C.textHelper,textTransform:'uppercase',marginBottom:6}}>Summary</div>
        <p style={{...T.body01,color:C.textSecondary,margin:0,lineHeight:'20px'}}>{alert.summary}</p>
      </div>

      {/* Structured list */}
      <div style={{borderBottom:`1px solid ${C.borderSubtle01}`}}>
        <div style={{...T.label01,color:C.textHelper,textTransform:'uppercase',padding:'10px 16px 4px'}}>Identifiers</div>
        <SRow label="Primary ID"  value={alert.primary_id} mono/>
        {alert.aliases.map((a,i)=><SRow key={i} label={`Alias ${i+1}`} value={a} mono/>)}
        <SRow label="Entity type" value={alert.entity_type}/>
        <SRow label="Source tier" value={`Tier ${alert.source_tier}`}/>
        <SRow label="Timestamp"   value={new Date(alert.timestamp).toLocaleString('en-IN',{hour12:false})}/>
      </div>

      {/* Intelligence flags */}
      <div style={{padding:'12px 16px',borderBottom:`1px solid ${C.borderSubtle00}`}}>
        <div style={{...T.label01,color:C.textHelper,textTransform:'uppercase',marginBottom:8}}>Intelligence flags</div>
        <div style={{display:'flex',flexWrap:'wrap',gap:6}}>
          {alert.flags.map(f=>(
            <Tag key={f} pair={C.tagYellow}>{FLAG_LABELS[f]||f}</Tag>
          ))}
        </div>
      </div>

      {/* Status + action buttons — Carbon button group */}
      <div style={{padding:'12px 16px'}}>
        <div style={{...T.label01,color:C.textHelper,textTransform:'uppercase',marginBottom:8}}>
          Status — <span style={{color:stat.tag.text}}>{stat.label}</span>
        </div>
        {/* Carbon button group: no gaps between siblings */}
        <div style={{display:'inline-flex'}}>
          {(STATUS_ACTIONS[alert.status]||[]).map(a=>(
            <Btn key={a.next} kind="primary" size="md" onClick={()=>onStatusChange(alert.id,a.next)}>
              {a.label}
            </Btn>
          ))}
          <Btn kind="tertiary" size="md">View graph</Btn>
          <Btn kind="ghost" size="md">Export</Btn>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────
   MAIN PAGE
───────────────────────────────────────── */
export default function AlertsPage() {
  /* ── Pagination & data state ── */
  const [alerts, setAlerts]               = useState([]);
  const [page, setPage]                   = useState(1);
  const [hasMore, setHasMore]             = useState(true);
  const [isLoading, setIsLoading]         = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  /* ── Search — debounced 350 ms ── */
  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery]             = useState('');
  const debounceRef                   = useRef(null);

  /* ── Filters (Task 4) ── */
  const [filters, setFilters] = useState<AlertFilters>(DEFAULT_FILTERS);

  /* ── UI ── */
  const [selected, setSelected]   = useState(null);
  const [liveCount, setLiveCount] = useState(289);

  /* ── Refs ── */
  const loaderRef   = useRef(null);
  const fetchingRef = useRef(false);

  /* Live counter */
  useEffect(()=>{
    const t=setInterval(()=>setLiveCount(c=>c+Math.floor(Math.random()*2)),8000);
    return ()=>clearInterval(t);
  },[]);

  /* Debounced search handler */
  function handleSearch(v) {
    setSearchInput(v);
    clearTimeout(debounceRef.current);
    debounceRef.current=setTimeout(()=>{
      setAlerts([]); setPage(1); setHasMore(true); setQuery(v);
    }, 350);
  }

  /* Filter change — always resets pagination */
  function handleFilterChange(patch) {
    setFilters(prev=>{ const n={...prev,...patch}; setAlerts([]); setPage(1); setHasMore(true); return n; });
  }
  function handleClearFilters() {
    setAlerts([]); setPage(1); setHasMore(true); setFilters(DEFAULT_FILTERS);
  }

  /* ─────────────────────────────────────
     TASK 3 — Core fetch effect
     Triggers on: page change (scroll) OR
                  query change (search)  OR
                  filter change.
     page===1 → replace list (new search/filter)
     page > 1 → append    (infinite scroll)
  ───────────────────────────────────── */
  useEffect(()=>{
    if (fetchingRef.current) return;
    const first = page===1;
    if (first) setIsLoading(true); else setIsLoadingMore(true);
    fetchingRef.current = true;

    fetchAlerts({ query, page, limit:PAGE_LIMIT, filters })
      .then(({results, hasMore:more})=>{
        setAlerts(prev=>{
          if (first) return results;
          const ids=new Set(prev.map(a=>a.id));
          return [...prev, ...results.filter(a=>!ids.has(a.id))];
        });
        setHasMore(more);
      })
      .catch(()=>{})
      .finally(()=>{
        setIsLoading(false); setIsLoadingMore(false); fetchingRef.current=false;
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[page, query, filters]);

  /* ─────────────────────────────────────
     TASK 3 — IntersectionObserver
     Watches sentinel <div ref={loaderRef}>.
     When it enters viewport → setPage(p+1)
     which fires the fetch effect above.
  ───────────────────────────────────── */
  useEffect(()=>{
    const el=loaderRef.current;
    if (!el) return;
    const obs=new IntersectionObserver(
      ([entry])=>{
        if (entry.isIntersecting && hasMore && !isLoadingMore && !fetchingRef.current)
          setPage(p=>p+1);
      },
      { threshold:0.1 }
    );
    obs.observe(el);
    return ()=>obs.disconnect();
  },[hasMore, isLoadingMore]);

  /* Status update (detail panel) */
  function handleStatusChange(id, next) {
    setAlerts(prev=>prev.map(a=>a.id===id?{...a,status:next}:a));
    setSelected(prev=>prev?.id===id?{...prev,status:next}:prev);
  }

  /* Counts */
  const counts = {
    total:    liveCount,
    new:      alerts.filter(a=>a.status==='new').length,
    critical: alerts.filter(a=>a.severity==='critical').length,
    high:     alerts.filter(a=>a.severity==='high').length,
  };
  const activeFilterCount = Object.entries(filters)
    .filter(([,v])=>v&&v!=='all'&&v!=='All types'&&v!=='All sources').length;

  /* Table column definitions */
  const COLS = [
    {label:'SEVERITY', w:120},
    {label:'SUMMARY',  w:null},
    {label:'TYPE',     w:100},
    {label:'STATUS',   w:110},
    {label:'RISK',     w:70},
    {label:'TIME',     w:110},
    {label:'',         w:80},
  ];

  return (
    <div style={{
      display:'flex', flexDirection:'column',
      height:'100vh', background:C.background, overflow:'hidden',
      fontFamily:"'IBM Plex Sans',Arial,sans-serif", color:C.textPrimary,
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap');
        *{box-sizing:border-box;}
        @keyframes cds-blink{0%,100%{opacity:1}50%{opacity:0.15}}
        @keyframes cds-spin{to{transform:rotate(360deg)}}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:${C.borderStrong01}}
        input[type="date"]::-webkit-calendar-picker-indicator{filter:invert(0.5);cursor:pointer}
        input::placeholder{color:${C.textPlaceholder}}
        select option{background:${C.layer02}}
      `}</style>

      {/* ══ CARBON PAGE HEADER ══ */}
      <div style={{background:C.layer01,borderBottom:`1px solid ${C.borderSubtle01}`,flexShrink:0}}>

        {/* Breadcrumb */}
        <div style={{display:'flex',alignItems:'center',gap:6,padding:'8px 16px',...T.label01,color:C.textHelper}}>
          <span>ILA</span>
          <span>›</span>
          <span style={{color:C.textPrimary}}>Alert management</span>
        </div>

        {/* Title + summary numbers */}
        <div style={{display:'flex',alignItems:'flex-end',justifyContent:'space-between',padding:'0 16px 16px'}}>
          <div>
            <h1 style={{...T.heading04,color:C.textPrimary,margin:0}}>Alert management</h1>
            <div style={{display:'flex',alignItems:'center',gap:6,marginTop:6,...T.label01,color:C.supportSuccess}}>
              <span style={{width:6,height:6,borderRadius:'50%',background:C.supportSuccess,
                animation:'cds-blink 1.4s infinite',display:'inline-block'}}/>
              System live
            </div>
          </div>

          {/* Carbon summary numbers — right-aligned */}
          <div style={{display:'flex'}}>
            {[
              {label:'Total alerts', value:counts.total,    color:C.textPrimary},
              {label:'New',          value:counts.new,      color:C.supportError},
              {label:'Critical',     value:counts.critical, color:C.supportError},
              {label:'High',         value:counts.high,     color:C.supportWarning},
            ].map(({label,value,color},i)=>(
              <div key={label} style={{
                padding:'6px 24px', textAlign:'right',
                borderLeft: i>0?`1px solid ${C.borderSubtle00}`:'none',
              }}>
                <div style={{...T.heading03,color,lineHeight:1}}>{value}</div>
                <div style={{...T.label01,color:C.textHelper,marginTop:4}}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ══ CARBON TABLE TOOLBAR ══ */}
      <div style={{
        background:C.layer01, borderBottom:`1px solid ${C.borderSubtle01}`,
        padding:'0 16px', display:'flex', alignItems:'center', gap:8, height:56, flexShrink:0,
      }}>
        {/* Content switcher — severity quick filter */}
        <div style={{display:'flex',border:`1px solid ${C.borderSubtle01}`}}>
          {SEVERITY_OPTIONS.map(s=>{
            const active=filters.severity===s;
            return (
              <button key={s} onClick={()=>handleFilterChange({severity:s})} style={{
                height:40, padding:'0 14px',
                background:active?C.layer02:'transparent',
                color:active?C.textPrimary:C.textSecondary,
                border:'none', borderRight:`1px solid ${C.borderSubtle01}`,
                outline:active?`2px solid ${C.interactive}`:'none',
                outlineOffset:-2, ...T.label02, cursor:'pointer',
                transition:'background 70ms', textTransform:'capitalize',
              }}>{s==='all'?'All':SEV[s]?.label||s}</button>
            );
          })}
        </div>

        {/* Type dropdown */}
        <Select value={filters.type} onChange={v=>handleFilterChange({type:v})} options={TYPE_OPTIONS} width={152}/>

        {/* Active filter count indicator */}
        {activeFilterCount>0 && (
          <div style={{display:'flex',alignItems:'center',gap:6,...T.label01,color:C.textHelper}}>
            <span style={{width:6,height:6,borderRadius:'50%',background:C.interactive,display:'inline-block'}}/>
            {activeFilterCount} filter{activeFilterCount>1?'s':''} active
          </div>
        )}

        <div style={{flex:1}}/>

        {/* Carbon search */}
        <TextInput value={searchInput} onChange={handleSearch} placeholder="Search alerts…" width={280}
          icon={
            <svg width="16" height="16" viewBox="0 0 32 32" fill={C.iconSecondary} aria-hidden="true">
              <path d="M29 27.586l-7.552-7.552a11 11 0 10-1.414 1.414L27.586 29zM4 13a9 9 0 119 9 9.01 9.01 0 01-9-9z"/>
            </svg>
          }
        />

        {/* Task 4 filter panel */}
        <FilterPanel filters={filters} onChange={handleFilterChange} onClear={handleClearFilters} resultCount={alerts.length}/>
      </div>

      {/* ══ BODY ══ */}
      <div style={{flex:1,display:'flex',overflow:'hidden'}}>

        {/* ── CARBON DATA TABLE ── */}
        <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden',minWidth:0}}>

          {/* Sticky column headers */}
          <table style={{width:'100%',borderCollapse:'collapse',flexShrink:0,tableLayout:'fixed'}}>
            <colgroup>
              {COLS.map((c,i)=><col key={i} style={c.w?{width:c.w}:{}}/>)}
            </colgroup>
            <thead>
              <tr style={{background:C.layer02,borderBottom:`1px solid ${C.borderStrong01}`}}>
                {COLS.map(c=>(
                  <th key={c.label} style={{
                    padding:'10px 16px',...T.label01,color:C.textHelper,
                    textAlign:c.label===''?'right':'left',fontWeight:600,
                    letterSpacing:'0.32px',whiteSpace:'nowrap',userSelect:'none',
                  }}>{c.label}</th>
                ))}
              </tr>
            </thead>
          </table>

          {/* Scrollable table body */}
          <div style={{flex:1,overflowY:'auto'}}>
            <table style={{width:'100%',borderCollapse:'collapse',tableLayout:'fixed'}}>
              <colgroup>
                {COLS.map((c,i)=><col key={i} style={c.w?{width:c.w}:{}}/>)}
              </colgroup>
              <tbody>

                {/* First-load state */}
                {isLoading && alerts.length===0 && (
                  <tr><td colSpan={7} style={{padding:'48px',textAlign:'center'}}>
                    <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:14}}>
                      <Spinner size={32}/>
                      <span style={{...T.body01,color:C.textHelper}}>Loading alerts…</span>
                    </div>
                  </td></tr>
                )}

                {/* Empty state */}
                {!isLoading && alerts.length===0 && (
                  <tr><td colSpan={7} style={{padding:'64px',textAlign:'center'}}>
                    <div style={{...T.heading01,color:C.textSecondary,marginBottom:6}}>No alerts match</div>
                    <div style={{...T.body01,color:C.textHelper,marginBottom:14}}>Try adjusting or clearing your filters</div>
                    <Btn kind="ghost" size="md" onClick={handleClearFilters}>Clear all filters</Btn>
                  </td></tr>
                )}

                {/* Alert rows */}
                {alerts.map(alert=>(
                  <AlertRow key={alert.id} alert={alert} selected={selected?.id===alert.id} onClick={setSelected}/>
                ))}

                {/* ─────────────────────────────────────
                    TASK 3 — INFINITE SCROLL SENTINEL
                    This invisible <div> sits at the very
                    bottom of the rendered list.
                    IntersectionObserver watches it:
                      → enters viewport
                      → setPage(prev + 1)
                      → useEffect re-runs, fetches next page
                      → results are APPENDED to alerts[]
                ───────────────────────────────────── */}
                <tr><td colSpan={7} style={{padding:0}}>
                  <div ref={loaderRef} style={{height:1}}/>
                </td></tr>

                {/* Load-more indicator */}
                {isLoadingMore && (
                  <tr><td colSpan={7} style={{padding:'14px',textAlign:'center'}}>
                    <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:10}}>
                      <Spinner size={18}/>
                      <span style={{...T.label01,color:C.textHelper}}>Loading more…</span>
                    </div>
                  </td></tr>
                )}

                {/* End-of-results */}
                {!hasMore && alerts.length>0 && (
                  <tr><td colSpan={7}>
                    <div style={{padding:'12px 16px',textAlign:'center',...T.label01,color:C.textHelper,borderTop:`1px solid ${C.borderSubtle00}`}}>
                      All {alerts.length} results loaded
                    </div>
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Carbon table footer / pagination bar */}
          <div style={{
            height:40,padding:'0 16px',borderTop:`1px solid ${C.borderSubtle01}`,
            display:'flex',alignItems:'center',gap:16,background:C.layer01,flexShrink:0,
          }}>
            <span style={{...T.label01,color:C.textHelper}}>
              {alerts.length} item{alerts.length!==1?'s':''}
              {activeFilterCount>0?` · ${activeFilterCount} filter${activeFilterCount>1?'s':''} applied`:''}
              {isLoadingMore?` · Fetching page ${page}…`:''}
            </span>
            <span style={{marginLeft:'auto',...T.label01,color:C.textHelper}}>
              Last sync: {new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false})}
            </span>
          </div>
        </div>

        {/* ── CARBON RIGHT PANEL — Alert detail ── */}
        <div style={{
          width:360,minWidth:360,flexShrink:0,
          display:'flex',flexDirection:'column',
          background:C.layer01,borderLeft:`1px solid ${C.borderSubtle01}`,overflow:'hidden',
        }}>
          {/* Panel header */}
          <div style={{height:40,padding:'0 16px',borderBottom:`1px solid ${C.borderSubtle01}`,
            display:'flex',alignItems:'center',gap:8,flexShrink:0}}>
            <span style={{...T.heading01,color:C.textSecondary}}>Alert detail</span>
            {selected && <Tag pair={C.tagYellow} small>{selected.id}</Tag>}
          </div>
          <AlertDetail alert={selected} onStatusChange={handleStatusChange}/>
        </div>
      </div>
    </div>
  );
}